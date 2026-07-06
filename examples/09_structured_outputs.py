"""
Example 09 — structured outputs (guaranteed JSON).
==================================================

Often you don't want prose — you want *data* your program can use directly. Claude
can guarantee the reply matches an exact JSON Schema you define. No more fragile
"please reply in JSON" prompting and hoping.

You ask for this with the `output_config` parameter:

    output_config={"format": {"type": "json_schema", "schema": <your schema>}}

The model is then constrained to emit JSON conforming to that schema — the right
keys, the right types, every time. The content still arrives as a text block
containing a JSON *string*, which you parse with `json.loads()`.

  >> Ergonomic shortcut: `client.messages.parse(..., output_format=MyPydanticModel)`
     takes a Pydantic model, sends the schema for you, AND returns a validated
     object on `response.parsed_output` — no manual json.loads. We use the raw
     schema below so you can see exactly what's going over the wire.

Run it:

    secrun python examples/09_structured_outputs.py
"""

import json
import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

# Describe EXACTLY the structure we want back. `additionalProperties: False` and
# listing every field in `required` are needed for the schema to be accepted.
schema = {
    "type": "object",
    "properties": {
        "language": {"type": "string"},
        "summary": {"type": "string"},
        "bugs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "line_hint": {"type": "string"},
                    "problem": {"type": "string"},
                },
                "required": ["line_hint", "problem"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["language", "summary", "bugs"],
    "additionalProperties": False,
}

code = """
def average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total // len(numbers)
"""

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    system="You are a code reviewer.",
    messages=[
        {"role": "user", "content": f"Review this code:\n```\n{code}\n```"},
    ],
    output_config={
        "format": {"type": "json_schema", "schema": schema},
    },
)

# The format guarantee means the first text block is valid JSON matching our
# schema — safe to parse and use as a dict.
text = next(b.text for b in response.content if b.type == "text")
data = json.loads(text)

print(f"Language: {data['language']}")
print(f"Summary:  {data['summary']}")
print("Bugs:")
for bug in data["bugs"]:
    print(f"  - ({bug['line_hint']}) {bug['problem']}")
