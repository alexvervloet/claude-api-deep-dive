"""
Example 03 — temperature.
=========================

`temperature` controls randomness. On Claude the range is **0.0 to 1.0** (not 0–2
like some APIs), and the default is 1.0.

  - 0.0  : The model almost always picks its single most likely next token.
           Answers are focused, repeatable, and a bit "safe". Best for facts,
           code, extraction — anything where you want consistency.
  - 0.5  : A balance of focus and variety.
  - 1.0  : Most varied. More surprising word choices. Good for brainstorming.

Run it:

    secrun python examples/03_temperature.py

We ask the same creative question at three temperatures. Notice how 0.0 tends to
repeat itself across runs while 1.0 reinvents the answer each time.

>> Heads up — the modern Claude direction:
   On the newest models (Claude Opus 4.8, Claude Fable 5) the sampling knobs
   `temperature`, `top_p`, and `top_k` have been *removed* — sending them returns
   an error. Those models steer behavior through prompting plus the `effort` and
   thinking controls instead (see examples/11_thinking.py). The knobs in
   examples 03–06 still work on the fast workhorse models like Claude Haiku 4.5,
   which is what we use here, and they're worth understanding — but know that the
   frontier is moving past them.
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

prompt = "Give a five-word slogan for a coffee shop on the moon."

for temp in (0.0, 0.5, 1.0):
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=64,
        messages=[{"role": "user", "content": prompt}],
        temperature=temp,
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    print(f"temperature={temp:<4} -> {text}")
