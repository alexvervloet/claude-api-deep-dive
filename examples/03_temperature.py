"""
Example 03: temperature.

`temperature` controls randomness. On Claude the range is **0.0 to 1.0** (not 0–2
like some APIs), and the default is 1.0.

  - 0.0  : The model almost always picks its single most likely next token.
           Answers are focused, repeatable, and a bit "safe". Best for facts,
           code, extraction, anything where you want consistency.
  - 0.5  : A balance of focus and variety.
  - 1.0  : Most varied. More surprising word choices. Good for brainstorming.

Run it:

    secrun python examples/03_temperature.py

We ask the same creative question at three temperatures. Notice how 0.0 tends to
repeat itself across runs while 1.0 reinvents the answer each time.

>> Heads up, the modern Claude direction:
   The sampling knobs `temperature`, `top_p`, and `top_k` are being retired, in
   two separate steps that are easy to confuse.

   1. The *models* dropped them. On Claude Opus 4.7 and everything after it,
      including Sonnet 5, Opus 5, and Fable 5/5.1, sending any of them returns a
      400. Those models steer behavior through prompting plus the `effort` and
      thinking controls instead (see examples/11_thinking.py).
   2. The *SDK* dropped them. `anthropic` 1.0 removed them from the Messages
      method signatures, so `temperature=0.2` is no longer a keyword argument
      you can pass at all, on any model. Where a model still accepts the
      parameter, you send it through the escape hatch: `extra_body={...}`, as
      below.

   So the knobs in examples 03 and 05 still work, on the fast workhorse models like
   Claude Haiku 4.5, which is what we use here, and they now need the escape
   hatch to get there. They're worth understanding. Just know you're looking at
   a parameter with one foot out the door, and that `extra_body` is the shape
   the SDK gives you for exactly that: a parameter the server might take and the
   client no longer promises anything about.
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see ../docs/SECRETS.md) and try again.")

client = anthropic.Anthropic()

prompt = "Give a five-word slogan for a coffee shop on the moon."

for temp in (0.0, 0.5, 1.0):
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=64,
        messages=[{"role": "user", "content": prompt}],
        # Not a keyword argument any more: see the heads-up at the top.
        extra_body={"temperature": temp},
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    print(f"temperature={temp:<4} -> {text}")
