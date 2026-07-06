"""
Example 02 — system, user, and assistant.
==========================================

A chat is a transcript of messages. On Claude there are exactly two roles you put
in the `messages` list:

  - user      : What the human says. The first message must be a `user` message.
  - assistant : What the model said. You include PRIOR assistant messages to give
                the model memory of the conversation — the API itself is
                stateless, so *you* resend the history every time.

And then there's the **system prompt** — the standing instructions, persona, and
tone. Here's a key Claude difference worth burning in:

  >> The system prompt is NOT a message in the list. It's a separate top-level
  >> `system=` parameter on the request.

Set it once and it steers everything that follows.

Run it:

    secrun python examples/02_roles.py

Try editing the system prompt (e.g. "You are a grumpy pirate") and watch the tone
of the answer change without touching the question at all. That's the power of
the system prompt.
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

# Note the assistant message in the middle: we're *simulating* a prior turn so
# the model continues the thread coherently. This is how you build multi-turn
# chat — keep appending messages to the list.
response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=256,
    system="You are a terse math tutor. One line only.",  # <- top-level, not a message
    messages=[
        {"role": "user", "content": "What is 12 * 12?"},
        {"role": "assistant", "content": "144."},
        {"role": "user", "content": "And that, doubled?"},
    ],
)

for block in response.content:
    if block.type == "text":
        print(block.text)
