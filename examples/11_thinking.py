"""
Example 11 — extended thinking & effort.
========================================

This is the most distinctly *Claude* capability. On hard problems you can let the
model **think before it answers** — work through intermediate reasoning in
dedicated `thinking` blocks — and you control how much effort it spends.

Two parameters:

  - thinking={"type": "adaptive"}
      Turns on adaptive thinking: the model decides *when* and *how much* to think,
      per request. (Add "display": "summarized" to get a readable summary of that
      reasoning back; by default the thinking happens but isn't shown.)

  - output_config={"effort": "low" | "medium" | "high" | "max"}
      How much overall effort to spend. Lower effort = faster, cheaper, terser;
      higher effort = more thorough. This is the knob that's *replacing*
      temperature/top_p on the newest models (see example 03): you no longer fiddle
      with sampling, you dial effort and let the model reason.

The response `content` now interleaves block types: `thinking` blocks (the
reasoning) and `text` blocks (the answer). We handle each by `.type`, the same
list-of-blocks shape you met in example 01.

Note: thinking requires a recent reasoning model — we use claude-sonnet-4-6 here,
not the Haiku workhorse from the earlier examples. Thinking tokens are billed as
output tokens, so a thoughtful answer costs more — that's the tradeoff.

Run it:

    secrun python examples/11_thinking.py
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

puzzle = (
    "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the "
    "ball. How much does the ball cost? Show your reasoning."
)

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    thinking={"type": "adaptive", "display": "summarized"},
    output_config={"effort": "high"},
    messages=[{"role": "user", "content": puzzle}],
)

for block in response.content:
    if block.type == "thinking":
        print("--- thinking (summary) ---")
        print(block.thinking)
        print()
    elif block.type == "text":
        print("--- answer ---")
        print(block.text)

print("\n--- usage ---")
print(response.usage)
print("(output_tokens includes the thinking — that's what you pay for the extra care.)")
