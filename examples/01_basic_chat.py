"""
Example 01: Your first message.

The whole API in a few lines. You send a list of messages; you get back a
message. Run it:

    secrun python examples/01_basic_chat.py

What to notice:
  - `client = anthropic.Anthropic()` reads your key from the ANTHROPIC_API_KEY
    environment variable. We load it from .env first.
  - `messages` is a list. Even a one-off question is a list with one entry.
  - `max_tokens` is **required** on Claude. It's the cap on how much the model
    may generate. (Other APIs let you omit it; Claude does not.)
  - The reply lives in `response.content`, which is a *list of content blocks* 
    NOT a single string. Each block has a `.type`. For plain answers you want the
    `text` blocks. (Later you'll see other block types: `thinking`, `tool_use`.)
  - `response.usage` reports exactly how many tokens you were billed for, split
    into `input_tokens` and `output_tokens`.
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=256,
    messages=[
        {"role": "user", "content": "In one sentence, what is an API?"},
    ],
)

# response.content is a list. Walk it and print the text blocks.
for block in response.content:
    if block.type == "text":
        print(block.text)

print("\n--- usage ---")
print(response.usage)
