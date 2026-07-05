#!/usr/bin/env python3
"""
streaming_server.py — FastAPI streaming server capstone.
=========================================================

This is the capstone project for the SSE section: a production-style FastAPI
server that streams Claude responses to a browser using Server-Sent Events.
It shows the three challenges unique to streaming web services:

  1. Token-by-token forwarding — each AI token is wrapped in a JSON SSE event
     and pushed to the browser as it arrives, not buffered until the end.

  2. Disconnect detection — if the browser closes the tab mid-stream, we detect
     it and abort the AI request immediately (stops burning tokens).

  3. Error recovery — transient API errors (rate limits, connection blips)
     trigger automatic retries with exponential backoff before the stream
     starts. Mid-stream errors yield a clean error event so the browser can
     show a message rather than hanging indefinitely.

Run the server
--------------
    # One-time install (if not already in requirements.txt):
    pip install fastapi "uvicorn[standard]"

    # Start (auto-reloads on file saves):
    uvicorn hands_on.streaming_server:app --reload

Then open http://localhost:8000 in a browser. The HTML client in
hands_on/static/index.html is served automatically.

SSE event format
----------------
Each event the server sends is a JSON object on a `data:` line:

    data: {"type": "token",   "text": "Hello"}

    data: {"type": "token",   "text": " world"}

    data: {"type": "done",    "tokens": 42, "chunks": 7, "elapsed": 1.23}

    data: {"type": "error",   "message": "...", "partial": "...so far..."}

Architecture
------------
  POST /stream  body: {"prompt": "..."}
    → StreamingResponse(text/event-stream)
    → retries the API call up to 3× on transient errors
    → yields token events token-by-token
    → detects client disconnect and aborts early
    → yields done or error event at the end

  GET /
    → serves hands_on/static/index.html

See examples/17_sse.py to understand the underlying SSE protocol, including
Claude's richer event types (message_start, content_block_delta, etc.).
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add repo root to path so `utils.*` is importable from any working directory.
sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from fastapi import FastAPI, Request  # type: ignore[import-untyped]
from fastapi.responses import FileResponse, StreamingResponse  # type: ignore[import-untyped]
from pydantic import BaseModel

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("streaming_server")

# Async client — essential for FastAPI so the event loop isn't blocked while
# waiting for the API. Each request gets its own concurrent slot.
async_client = AsyncAnthropic()

app = FastAPI(title="Streaming AI Server")

STATIC_DIR = Path(__file__).parent / "static"


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------


class StreamRequest(BaseModel):
    prompt: str
    model: str = "claude-haiku-4-5"
    max_tokens: int = 1024


# ---------------------------------------------------------------------------
# SSE event helpers
# ---------------------------------------------------------------------------


def _token_event(text: str) -> str:
    return f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"


def _done_event(tokens: int, chunks: int, elapsed: float) -> str:
    return f"data: {json.dumps({'type': 'done', 'tokens': tokens, 'chunks': chunks, 'elapsed': round(elapsed, 2)})}\n\n"


def _error_event(message: str, partial: str = "") -> str:
    payload: dict = {"type": "error", "message": message}
    if partial:
        payload["partial"] = partial
    return f"data: {json.dumps(payload)}\n\n"


# ---------------------------------------------------------------------------
# Core streaming generator
# ---------------------------------------------------------------------------


async def _stream_tokens(request: Request, body: StreamRequest):
    """
    Async generator that calls the Claude API and yields SSE events.

    Three concerns handled here:

    1. Retry before streaming starts — transient errors (rate limit, network)
       are retried with exponential backoff. Once tokens begin flowing we
       don't retry (partial output would confuse the client).

    2. Disconnect detection — `request.is_disconnected()` is polled each
       iteration as a fallback, but in practice Starlette's StreamingResponse
       notices the closed socket first and cancels this generator outright
       (caught below as `asyncio.CancelledError`). Either path aborts the
       Claude call instead of letting it run to completion unread.

    3. Partial response — we accumulate tokens into `partial` so that if an
       error occurs mid-stream, the error event includes what was received.

    Claude note: we use client.messages.stream() (the high-level helper) which
    exposes `stream.text_stream` — a clean async iterator of text pieces. This
    hides the low-level event types (message_start, pings, etc.) that you can
    see in examples/17_sse.py.
    """
    partial: list[str] = []
    start = time.perf_counter()

    # --- Phase 1: open the stream with retries ---
    # We check for connection/rate-limit errors before any tokens flow.
    # After the first token, we don't retry — partial output would be confusing.
    last_exc: Exception | None = None
    stream_context = None
    stream = None

    for attempt in range(3):
        try:
            # Enter the context manager (opens the HTTP connection).
            stream_context = async_client.messages.stream(
                model=body.model,
                max_tokens=body.max_tokens,
                messages=[{"role": "user", "content": body.prompt}],
            )
            # __aenter__ actually sends the request; errors surface here.
            stream = await stream_context.__aenter__()
            break
        except (anthropic.RateLimitError, anthropic.APIConnectionError) as exc:
            last_exc = exc
            if attempt < 2:
                await asyncio.sleep(1.0 * (2**attempt))
        except anthropic.AuthenticationError as exc:
            yield _error_event(f"Authentication failed: {exc}")
            return
        except anthropic.BadRequestError as exc:
            yield _error_event(f"Bad request: {exc}")
            return

    if stream_context is None:
        yield _error_event(f"Could not reach the API after 3 attempts: {last_exc}")
        return

    assert stream is not None

    # --- Phase 2: stream tokens to the client ---
    try:
        async for text in stream.text_stream:
            # Check for client disconnect before each yield.
            if await request.is_disconnected():
                logger.info(
                    "client disconnected after %d chunks — aborting Claude call",
                    len(partial),
                )
                await stream_context.__aexit__(None, None, None)
                return  # generator closes → StreamingResponse cleans up

            partial.append(text)
            yield _token_event(text)

    except asyncio.CancelledError:
        # The usual disconnect path: StreamingResponse notices the closed
        # socket and cancels this generator before the is_disconnected()
        # check above gets a chance to run.
        logger.info(
            "client disconnected after %d chunks — aborting Claude call",
            len(partial),
        )
        raise
    except (anthropic.RateLimitError, anthropic.APIConnectionError) as exc:
        yield _error_event(str(exc), partial="".join(partial))
        return
    except anthropic.APIError as exc:
        yield _error_event(str(exc), partial="".join(partial))
        return
    finally:
        # Always close the context manager to release the HTTP connection.
        try:
            await stream_context.__aexit__(None, None, None)
        except Exception:
            pass

    # --- Phase 3: final stats event ---
    elapsed = time.perf_counter() - start
    # len(partial) counts SSE text chunks, not LLM tokens — a single chunk can
    # contain several tokens. get_final_message() gives the real output token
    # count from the API's usage stats.
    final_message = await stream.get_final_message()
    yield _done_event(
        tokens=final_message.usage.output_tokens, chunks=len(partial), elapsed=elapsed
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
async def serve_ui():
    """Serve the browser UI from hands_on/static/index.html."""
    html_path = STATIC_DIR / "index.html"
    if not html_path.exists():
        return {"error": "index.html not found in hands_on/static/"}
    return FileResponse(html_path)


@app.post("/stream")
async def stream_endpoint(request: Request, body: StreamRequest):
    """
    Stream an AI response as SSE.

    The client should read the response body as a stream (fetch + ReadableStream)
    and parse each `data: <json>\\n\\n` event. See hands_on/static/index.html
    for a working browser example.
    """
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # tells Nginx not to buffer this response
    }
    return StreamingResponse(
        _stream_tokens(request, body),
        media_type="text/event-stream",
        headers=headers,
    )
