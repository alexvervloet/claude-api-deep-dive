"""
Example 13 — multi-turn conversations (the API has no memory).
==============================================================

Here's the single most common surprise for newcomers:

  >> The API is STATELESS. It remembers nothing between requests. If you want
  >> Claude to "remember" what was said earlier, *you* have to send the whole
  >> conversation back every single time.

There's no session, no conversation ID, no server-side history. Each call to
`client.messages.create` is judged entirely on the `messages` list you hand it
right then. The illusion of a chatbot that remembers is built by you, the
caller, by appending each new turn to a growing list:

    [user] -> [user, assistant] -> [user, assistant, user, assistant] -> ...

Two Claude specifics to keep in mind (both from Example 02):
  - The system prompt is the top-level `system=` parameter, NOT an entry in the
    list. It stays constant; only the user/assistant turns accumulate.
  - `response.content` is a list of blocks, so we pull the text out before
    appending the assistant's turn back into the history.

Run it (type a few messages, then `quit`):

    secrun python examples/13_conversation.py

Try this to feel the statelessness: tell it your name, then ask "what's my
name?". It works — because the earlier turns are still in the list. Now look at
`trim_history()` below: drop the early turns and Claude genuinely forgets,
because for the model the conversation *is* whatever list you send.
"""

import os
import sys

import anthropic
from anthropic.types import MessageParam
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

SYSTEM = "You are a concise, friendly assistant."

# Unlike OpenAI, the system prompt is NOT in this list — it's passed separately.
# So `messages` holds only user/assistant turns. This list IS the memory.
messages: list[MessageParam] = []


def trim_history(history: list[MessageParam], max_turns: int = 10) -> list[MessageParam]:
    """Keep only the most recent `max_turns` messages.

    Every turn you keep is re-sent (and re-billed) on the next request, so real
    apps cap the history. Drop the oldest turns and Claude forgets them — proof
    that "memory" is just the list you choose to send. (The first message must
    always be a `user` turn, so we trim in user/assistant pairs.)
    """
    if len(history) <= max_turns:
        return history
    trimmed = history[-max_turns:]
    if trimmed and trimmed[0]["role"] != "user":
        trimmed = trimmed[1:]
    return trimmed


print("Chat with Claude. Type 'quit' to exit.\n")

while True:
    try:
        user_input = input("you> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break

    if user_input.lower() in {"quit", "exit"}:
        break
    if not user_input:
        continue

    # 1. Append the user's turn to the running history.
    messages.append({"role": "user", "content": user_input})

    # 2. Send the ENTIRE history every time — that's what gives Claude context.
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        system=SYSTEM,
        messages=messages,
    )

    # 3. Flatten the content blocks to text, then append the assistant's turn so
    #    the next request includes it.
    reply = "".join(block.text for block in response.content if block.type == "text")
    messages.append({"role": "assistant", "content": reply})
    messages = trim_history(messages)

    print(f"claude> {reply}\n")
