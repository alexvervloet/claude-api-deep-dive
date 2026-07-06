"""
Example 06 — stop sequences.
============================

`stop_sequences` is a list of strings that tell the model: "the moment you're
about to produce one of these, stop generating." The stop text itself is NOT
included in the output.

(Note the name: on Claude the parameter is `stop_sequences` — always a list —
and when one fires, `stop_reason` comes back as `"stop_sequence"`.)

Uses:
  - Cut a list off after N items (stop at "4.").
  - End a structured response at a delimiter.
  - Prevent the model from running past a known boundary (e.g. "\n\n").

Run it:

    secrun python examples/06_stop_sequences.py

The first call lets the model count freely; the second stops it the instant it
tries to write "4.", so you only get items 1–3.
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

prompt = "Count from 1 to 10, one number per line, like '1.', '2.', ..."

print("--- without stop ---")
r1 = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=128,
    messages=[{"role": "user", "content": prompt}],
)
print(next((b.text for b in r1.content if b.type == "text"), ""))

print("\n--- with stop_sequences=['4.'] ---")
r2 = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=128,
    messages=[{"role": "user", "content": prompt}],
    stop_sequences=["4."],
)
print(next((b.text for b in r2.content if b.type == "text"), ""))
print(f"(stop_reason={r2.stop_reason})")
