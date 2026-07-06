"""
Example 05 — top_p (nucleus sampling).
======================================

`top_p` is the other randomness knob. Instead of scaling probabilities like
temperature does, it *restricts the candidate pool*:

  top_p = 0.1  -> consider only the smallest set of tokens whose probabilities
                  add up to 10%. Very focused — picks from the obvious choices.
  top_p = 1.0  -> consider everything (no restriction). This is the default.

Mental model: temperature changes *how boldly* the model chooses among options;
top_p changes *how many options it's even allowed to consider*.

Important: Anthropic recommends tuning EITHER temperature OR top_p, not both at
once, because they interact in confusing ways. Pick one knob and learn it.

(And, as in example 03: `top_p` is one of the sampling knobs the newest models —
Claude Opus 4.8, Claude Fable 5 — have removed. It still works on Claude Haiku
4.5, which we use here.)

Run it:

    secrun python examples/05_top_p.py
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

prompt = "Name an unusual but real animal."

for p in (0.1, 1.0):
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=64,
        messages=[{"role": "user", "content": prompt}],
        top_p=p,
        # We leave temperature at its default and only vary top_p here.
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    print(f"top_p={p:<4} -> {text}")
