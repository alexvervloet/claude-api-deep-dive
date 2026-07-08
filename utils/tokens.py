"""
Token counting with Claude's count_tokens endpoint.
====================================================

Models don't see characters or words — they see *tokens*. A token is a chunk of
text (often a word fragment). Roughly, 1 token ≈ 4 characters of English, or
about ¾ of a word, but it varies.

Here is the first real difference from some other APIs: **Anthropic does not ship
a local, offline tokenizer.** There's no `tiktoken` equivalent you can `pip
install` and run on your laptop. Instead, you ask the API to count for you, via
`client.messages.count_tokens(...)`.

The good news:
  - It is **free** — counting tokens is not billed, and it doesn't consume any of
    your output budget.
  - It is **exact** — it's the same tokenizer the model uses, so the number lines
    up with what you'll be billed for on the input side.

The trade-offs vs. an offline tokenizer:
  - It needs your API key and a network round-trip (still free, just not offline).
  - You get back a *count*, not the individual token pieces — Anthropic's
    tokenizer internals aren't exposed, so you can't print "here's how the
    sentence was split" the way you can with a public tokenizer.

Why count tokens at all?
  1. Cost: you pay per token (see pricing.py).
  2. Limits: every model has a maximum *context window* (input + output). If you
     overflow it, the request fails.
  3. Intuition: watching the count change as you edit a prompt teaches you a lot
     about how the model reads your text.

Two functions live here:
  - count_tokens(client, text):          tokens in a raw string.
  - count_message_tokens(client, msgs):  tokens in a full message list, optionally
                                         including a system prompt and tools — all
                                         of which count toward your input tokens.
"""

import anthropic

# The default model to count against. Token counts are *model-specific*: pass the
# same model you'll actually call, because different model families tokenize text
# slightly differently.
DEFAULT_MODEL = "claude-haiku-4-5"


def count_tokens(
    client: anthropic.Anthropic, text: str, model: str = DEFAULT_MODEL
) -> int:
    """Count tokens in a plain string (wrapped as a single user message)."""
    resp = client.messages.count_tokens(
        model=model,
        messages=[{"role": "user", "content": text}],
    )
    return resp.input_tokens


def count_message_tokens(
    client: anthropic.Anthropic,
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    output_format: type | None = None,
) -> int:
    """Count input tokens for a full message list.

    Unlike a bare string, a real request also carries a system prompt and
    (sometimes) tool definitions or a structured `output_format` — and **all of
    it counts** toward your input tokens. Pass `system`/`output_format` here so
    the number matches what you'll be billed for: a Pydantic `output_format` is
    turned into a JSON-schema tool definition under the hood, which can easily
    outweigh the rest of the prompt.

    The API adds the same small per-message bookkeeping the model uses, so this
    is the authoritative input-token count, not an estimate.
    """
    kwargs: dict = {"model": model, "messages": messages}
    if system is not None:
        kwargs["system"] = system
    if output_format is not None:
        kwargs["output_format"] = output_format
    return client.messages.count_tokens(**kwargs).input_tokens


if __name__ == "__main__":
    # Run `secrun python utils/tokens.py` to see token counting in action.
    # This makes a (free) API call, so it needs your key in the environment (via secrun).
    import os
    import sys

    from dotenv import load_dotenv

    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

    client = anthropic.Anthropic()

    sample = "The quick brown fox jumps over the lazy dog."
    print(f"Text:   {sample!r}")
    print(f"Tokens: {count_tokens(client, sample)}")
    print(
        "\n(Counting is a free API call. Anthropic's tokenizer isn't public, so we "
        "get the count — not the individual pieces.)"
    )
