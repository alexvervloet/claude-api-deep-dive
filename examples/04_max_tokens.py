"""
Example 04 — max_tokens (and stop_reason).
==========================================

`max_tokens` caps how many tokens the model is allowed to GENERATE. It does NOT
limit your input, and it does NOT make the model "summarize to fit" — it simply
cuts the model off when the budget runs out, mid-sentence if necessary.

On Claude `max_tokens` is **required** on every request (you've been setting it
all along). Think of it as a seatbelt you can't unbuckle.

Why the value matters:
  - Cost control: output tokens are the expensive ones.
  - Latency: shorter answers come back faster.
  - Safety: stop a runaway answer from ballooning.

The companion to watch is `stop_reason` — Claude's name for "why did it stop?":
  - "end_turn"       : the model finished on its own.
  - "max_tokens"     : it hit your max_tokens cap — the answer is truncated.
  - "stop_sequence"  : it hit one of your stop strings (see example 06).
  - "tool_use"       : it wants to call a tool (see example 10).

Run it:

    secrun python examples/04_max_tokens.py
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

prompt = "Explain how the internet works."

# A tiny cap gets truncated ("max_tokens"); a roomy one finishes ("end_turn").
for cap in (16, 256):
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=cap,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    print(f"--- max_tokens={cap} (stop_reason={response.stop_reason}) ---")
    print(text)
    print()
