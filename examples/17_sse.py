"""
Example 17 — Server-Sent Events (SSE): the protocol under streaming.
=====================================================================

Every streaming Claude response — in the Claude.ai UI, in examples/08_streaming.py,
in every production assistant — travels over a protocol called Server-Sent
Events (SSE). The Anthropic SDK parses it for you, but knowing the raw format
pays off: it's exactly what you'll produce when you build a backend that
forwards AI tokens to a browser.

The SSE wire format
-------------------
SSE is an ordinary HTTP response that stays open and drips data until the
server says it's done. The server sets:

    Content-Type: text/event-stream

Then sends events as text lines, each event terminated by a blank line.
Claude's stream is richer than most: it uses both the `event:` field (the
event type) and the `data:` field (the JSON payload):

    event: message_start
    data: {"type":"message_start","message":{"id":"msg_...","model":"claude-haiku-4-5",...}}

    event: content_block_start
    data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

    event: ping
    data: {"type":"ping"}

    event: content_block_delta
    data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

    event: content_block_stop
    data: {"type":"content_block_stop","index":0}

    event: message_delta
    data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":42}}

    event: message_stop
    data: {"type":"message_stop"}

Rules:
  - Each event has an `event:` line (the type) and a `data:` line (JSON payload).
  - A blank line terminates the current event.
  - The `content_block_delta` events carry the actual text tokens.
  - Token usage arrives in `message_delta`, not a final chunk like OpenAI.

This richer event taxonomy lets you react differently to each phase — ideal
when your server needs to track thinking blocks, tool calls, and text separately.

This example has three parts:

  Part 1 — Raw events: iterate the low-level event stream and print each event
           exactly as it would look on the wire, including the `event:` type line.

  Part 2 — Token timing: measure time-to-first-token and generation throughput
           to understand the rhythm of incremental delivery.

  Part 3 — Partial accumulation: show how a server buffers tokens in memory
           to track progress and recover from interruptions.

The capstone that puts all of this into practice is hands_on/streaming_server.py
— a FastAPI server that streams tokens over SSE to a real browser.

Run it:

    python examples/17_sse.py
"""

import json
import os
import sys
import time

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY (copy .env.example to .env) and try again.")

client = anthropic.Anthropic()

PROMPT = "Give three one-sentence reasons why streaming matters for AI UIs."

# ---------------------------------------------------------------------------
# Parts 1 & 2: use the low-level raw event stream to see every SSE event
# type, not just text deltas.
# ---------------------------------------------------------------------------

print("=== raw SSE events (as they appear on the wire) ===\n")

# client.messages.create(stream=True) returns a Stream[RawMessageStreamEvent],
# which gives us every event — message_start, pings, deltas, and message_stop.
# (client.messages.stream() is the high-level helper that skips non-text events.)
raw_stream = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=512,
    messages=[{"role": "user", "content": PROMPT}],
    stream=True,
)

start = time.perf_counter()
first_token_time: float | None = None
last_token_time: float | None = None
token_count = 0
partial: list[str] = []
output_tokens = 0

with raw_stream as stream:
    for event in stream:
        now = time.perf_counter()

        # Reconstruct the two lines that arrived on the wire:
        #   event: <type>
        #   data: <json>
        payload = json.dumps(event.model_dump(exclude_none=True))
        print(f"event: {event.type}")
        print(f"data: {payload[:100]}{'…' if len(payload) > 100 else ''}")
        print()  # blank line terminates the SSE event

        # Only content_block_delta events with text_delta carry actual text.
        if (event.type == "content_block_delta"
                and event.delta.type == "text_delta"):
            piece = event.delta.text
            if piece:
                if first_token_time is None:
                    first_token_time = now
                    print(f"  ↳ first token in {now - start:.3f}s\n")
                last_token_time = now
                token_count += 1
                partial.append(piece)

        # Usage arrives in the message_delta event (not in a final "chunk").
        if event.type == "message_delta" and hasattr(event, "usage"):
            output_tokens = event.usage.output_tokens

# ---------------------------------------------------------------------------
# Part 3: assembled response and stats.
# ---------------------------------------------------------------------------

total_elapsed = time.perf_counter() - start

print("=== assembled response ===\n")
print("".join(partial))

print("\n--- stats ---")
print(f"Total time:          {total_elapsed:.2f}s")
if first_token_time is not None:
    print(f"Time to first token: {first_token_time - start:.3f}s")
if first_token_time and last_token_time and token_count > 1:
    gen_span = last_token_time - first_token_time
    tps = (token_count - 1) / gen_span if gen_span > 0 else 0
    print(f"Generation span:     {gen_span:.2f}s ({tps:.0f} tokens/s)")
print(f"Chunks with text:    {token_count}")
if output_tokens:
    print(f"Output tokens:       {output_tokens}")

# ---------------------------------------------------------------------------
# What you do next: building a server.
# ---------------------------------------------------------------------------

print("""
Key takeaway
------------
In a streaming server, each text `piece` becomes one SSE event you yield
to the browser:

    yield f"data: {json.dumps({'type': 'token', 'text': piece})}\\n\\n"

Your server only needs to forward the text; the client doesn't need to know
about message_start, pings, or message_stop — those are internal plumbing.
See hands_on/streaming_server.py for the full production-ready implementation.
""")
