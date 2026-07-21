"""
Example 10: tool use.

The model can't run code, browse, or query your database. But it *can* tell you
"I'd like you to call this tool with these arguments", and then you run it and
hand the result back. This is "tool use," and it's how an assistant gets the
ability to actually *do* things.

The dance has four steps:

  1. You describe your tools (name, what they do, their inputs as a schema) and
     send them alongside the user's message.
  2. The model replies with `stop_reason == "tool_use"` and a `tool_use` content
     block: which tool, and what input (already parsed into a dict for you).
  3. YOU execute the real function with that input.
  4. You send the result back as a `tool_result` block and the model writes the
     final natural-language answer using it.

The model never runs your code. It only *asks*. You stay in control of what
actually executes.

A couple of Claude specifics to notice below:
  - A tool is `{name, description, input_schema}` at the top level; there's no
    "function" wrapper around it.
  - You append the model's whole `response.content` back as the assistant turn
    (it contains the tool_use block), then a `user` turn carrying the
    `tool_result`, matched to the request by `tool_use_id`.

Run it:

    secrun python examples/10_tool_use.py
"""

import os
import sys
from typing import cast

import anthropic
from anthropic.types import MessageParam, ToolParam
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()


# --- The actual function the model is allowed to ask us to run. ---
# In real life this might hit a weather API; here we fake it so the example is
# self-contained.
def get_current_weather(city: str) -> str:
    fake_db = {"Paris": "18°C, light rain", "Tokyo": "27°C, sunny"}
    return fake_db.get(city, "unknown")


# --- Step 1: describe the tool to the model. ---
tools: list[ToolParam] = [
    {
        "name": "get_current_weather",
        "description": "Get the current weather for a city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. Paris"},
            },
            "required": ["city"],
        },
    }
]

messages: list[MessageParam] = [
    {"role": "user", "content": "What's the weather like in Tokyo?"}
]

# First call: the model decides it needs the tool.
first = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=512,
    tools=tools,
    messages=messages,
)
print(f"[stop_reason: {first.stop_reason}]")

# --- Step 2 & 3: the model asked for a tool; we run it. ---
# Append the model's full response (including the tool_use block) as the
# assistant turn: the API requires the tool_result to follow it.
messages.append({"role": "assistant", "content": first.content})

tool_results = []
for block in first.content:
    if block.type == "tool_use":
        print(f"[model requested: {block.name}({block.input})]")
        # block.input is typed as `object` (it's parsed JSON); we know our schema.
        tool_input = cast("dict[str, str]", block.input)
        result = get_current_weather(**tool_input)
        # --- Step 4: return the result, tagged with the call's id. ---
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result,
        })

messages.append({"role": "user", "content": tool_results})

# Second call: the model now has the data and writes the final answer.
second = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=512,
    tools=tools,
    messages=messages,
)
print("\n" + next((b.text for b in second.content if b.type == "text"), ""))
