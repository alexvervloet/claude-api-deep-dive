"""
Example 16 — formatting output: Markdown, tables, and code blocks.
==================================================================

So far we've `print()`ed raw strings. But Claude loves to answer in **Markdown** —
headings, **bold**, bullet lists, and fenced ```code``` blocks — and dumping that
raw to a terminal shows the literal `**asterisks**` and backticks. Ugly.

The `rich` library renders all of that beautifully in the terminal:
  - `Markdown(...)`  turns a Markdown string into styled text.
  - `Syntax(...)`    syntax-highlights a code block for a given language.
  - `Table(...)`     draws real bordered tables from your data.

This pairs naturally with what you've learned: ask Claude for Markdown and render
it (live, even, while streaming), or take *structured* data (example 15) and lay
it out as a table. Nothing here is Claude-specific — it's how you make any model's
output pleasant to read.

This example needs `rich` (in requirements.txt):

    pip install rich

Run it:

    python examples/16_rich_output.py
"""

import os
import sys

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY (copy .env.example to .env) and try again.")

client = anthropic.Anthropic()
console = Console()  # rich's entry point; console.print() understands rich objects

# --- 1. Render a Markdown answer from the model ---------------------------------
# Ask explicitly for Markdown, then hand the string to rich.Markdown so headings,
# bold, and lists render as formatting instead of literal symbols.
response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=512,
    messages=[
        {
            "role": "user",
            "content": (
                "In Markdown, give 3 tips for writing good commit messages. "
                "Use a heading and a bulleted list with some **bold**."
            ),
        }
    ],
)
# response.content is a list of blocks — stitch the text blocks together.
answer = "".join(b.text for b in response.content if b.type == "text")

console.rule("[bold]1. Markdown answer")
console.print(Markdown(answer))

# --- 2. Syntax-highlight a code block -------------------------------------------
# When the answer IS code, Syntax highlights it for the given language.
#
# The snippet below is hard-coded so this section can demonstrate Syntax() in
# isolation, without a network call. In real use you won't call Syntax() on a
# hard-coded string — the code comes from Claude's response, in one of two ways:
#
#   1. Markdown(answer) already handles it. If the response contains fenced
#      code blocks (```python ... ```), rich's Markdown renderer detects the
#      language tag and syntax-highlights the block automatically — see
#      section 1 above. No extraction needed; this covers most chat-style use.
#   2. Extract it yourself when you need the code apart from the surrounding
#      prose — to save it to a file, execute it, or highlight it standalone:
#
#          import re
#          for lang, code in re.findall(r"```(\w+)?\n(.*?)```", answer, re.DOTALL):
#              console.print(Syntax(code, lang or "text", theme="monokai"))
#
#      findall() returns one (language, code) tuple per fenced block, since a
#      single answer can contain several.
snippet = '''def greet(name: str) -> str:
    """Return a friendly greeting."""
    return f"Hello, {name}!"
'''

console.rule("[bold]2. Code block")
console.print(Syntax(snippet, "python", theme="monokai", line_numbers=True))

# --- 3. Lay structured data out as a table --------------------------------------
# Tables shine for the structured data from example 15. Here we hard-code a few
# rows; in a real app these would come from a validated model.
console.rule("[bold]3. Table")
table = Table(title="Model line-up")
table.add_column("Model", style="cyan", no_wrap=True)
table.add_column("Good for", style="white")
table.add_column("Relative cost", justify="right", style="green")

table.add_row("claude-haiku-4-5", "Everyday tasks, high volume", "$")
table.add_row("claude-sonnet-4-6", "Harder reasoning, coding", "$$")
table.add_row("claude-opus-4-8", "The deepest reasoning", "$$$")

console.print(table)
