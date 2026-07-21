"""
Example 08: streaming responses.

By default, `client.messages.create` waits until the *entire* answer is ready,
then hands it back in one piece. With streaming, the API instead sends the answer
back in small pieces as the model generates them, exactly like you see text
appear word-by-word in the Claude app.

Why stream?
  - Perceived speed: the user sees the first words almost immediately instead of
    staring at a blank screen.
  - Long answers: with large `max_tokens`, a non-streaming request can hit an
    HTTP timeout. Streaming avoids that, so it's the recommended default for any
    long or open-ended generation.

The Claude SDK gives you a clean helper for this: `client.messages.stream(...)`
as a context manager:
  - `stream.text_stream` yields just the text pieces as they arrive.
  - `stream.get_final_message()` reassembles the whole thing afterward, so you
    still get the full message object and `usage` without juggling raw events.

Run it:

    secrun python examples/08_streaming.py
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

with client.messages.stream(
    model="claude-haiku-4-5",
    max_tokens=256,
    messages=[{"role": "user", "content": "Write a haiku about streaming data."}],
) as stream:
    for text in stream.text_stream:
        # end="" + flush so the text appears live instead of line-buffered.
        print(text, end="", flush=True)

    # After the loop, grab the assembled message for usage, stop_reason, etc.
    final = stream.get_final_message()

print("\n\n--- usage ---")
print(final.usage)
