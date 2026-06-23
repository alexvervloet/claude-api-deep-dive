#!/usr/bin/env python3
"""
extract.py — Turn free-form text into validated structured data.
================================================================

The second hands-on tool of the repo, and a companion to `ask.py`. Where `ask.py`
gets you *prose* about a file, `extract.py` gets you *data*: point it at messy
free-form text (meeting notes, an email, a support ticket) and it pulls out a
clean, typed, validated structure you could drop straight into a database.

It ties together three things from the examples:
  - Structured outputs + Pydantic validation (examples 09 & 15): Claude is
    constrained to a schema and the reply comes back as a validated object.
  - Rich output (example 16): the result is shown as a Markdown summary and a
    real table, not a wall of JSON.
  - Token/cost awareness (tokens.py, pricing.py): same --dry-run discipline as
    ask.py — see the price before you spend. (On Claude, counting tokens is a
    free API call, so even --dry-run needs your key.)

Examples
--------
  # Extract action items from the sample meeting notes
  python extract.py snippets/meeting_notes.txt

  # See tokens + estimated cost without paying for generation
  python extract.py snippets/meeting_notes.txt --dry-run

  # Use a more capable model for messier text
  python extract.py snippets/meeting_notes.txt --model claude-sonnet-4-6

  # Get the raw validated JSON instead of the pretty tables
  python extract.py snippets/meeting_notes.txt --json
"""

import argparse
import os
import sys
from enum import Enum

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from pricing import estimate_cost, format_cost
from tokens import count_message_tokens


# --- The shape we want out of the text -----------------------------------------
# These Pydantic models ARE the contract. The SDK turns them into the output
# format Claude must follow, and validates the reply back into these types. Field
# descriptions are sent along as guidance, so they double as extraction hints.
class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ActionItem(BaseModel):
    task: str = Field(description="The concrete thing that needs doing.")
    owner: str = Field(description="Who is responsible; 'unassigned' if unclear.")
    due: str | None = Field(
        default=None,
        description="When it's due if stated (e.g. 'Friday', 'end of month'); else null.",
    )
    priority: Priority = Field(description="Inferred urgency from the text.")


class Extraction(BaseModel):
    summary: str = Field(description="A one-sentence summary of the text.")
    action_items: list[ActionItem]


SYSTEM_PROMPT = (
    "You extract structured action items from free-form notes. Capture every task "
    "that someone needs to do. Infer the owner and priority from context; if an "
    "owner truly isn't implied, use 'unassigned'. Only include a due date if the "
    "text actually mentions one."
)


def build_messages(text: str) -> list[dict]:
    """A single user message with the raw text; the system prompt rides separately."""
    return [
        {"role": "user", "content": f"Extract action items from these notes:\n\n{text}"},
    ]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract validated structured data from a free-form text file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", help="Path to the free-form text to extract from.")
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5",
        help="Model to use (default: claude-haiku-4-5, the cheap, fast workhorse).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1024,
        help="Cap on generated tokens (REQUIRED by Claude; default 1024).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the validated data as raw JSON instead of formatted tables.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show token/cost estimates but DON'T generate. The counting call is "
             "free, so this spends no money.",
    )
    return parser.parse_args(argv)


def render(console: Console, data: Extraction) -> None:
    """Show the extraction as a Markdown summary + a table of action items."""
    console.print(Markdown(f"**Summary:** {data.summary}"))

    if not data.action_items:
        console.print("\n[italic]No action items found.[/italic]")
        return

    table = Table(title="Action items", title_style="bold")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Task", style="white")
    table.add_column("Owner", style="cyan")
    table.add_column("Due", style="yellow")
    table.add_column("Priority", justify="center")

    # Color the priority so high-urgency rows jump out.
    colors = {Priority.high: "red", Priority.medium: "yellow", Priority.low: "green"}
    for i, item in enumerate(data.action_items, 1):
        color = colors[item.priority]
        table.add_row(
            str(i),
            item.task,
            item.owner,
            item.due or "—",
            f"[{color}]{item.priority.value}[/{color}]",
        )

    console.print(table)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    console = Console()

    # 1. Read the text file.
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"Could not read {args.file!r}: {e}", file=sys.stderr)
        return 1

    # 2. We need the client even for --dry-run, because counting tokens is a (free)
    #    API call on Claude.
    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        print(
            "\nANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your "
            "key. (Even --dry-run needs it for the free token-counting call.)",
            file=sys.stderr,
        )
        return 1

    import anthropic
    client = anthropic.Anthropic()

    # 3. Count input tokens and estimate cost BEFORE generating anything.
    messages = build_messages(text)
    input_tokens = count_message_tokens(
        client, messages, model=args.model, system=SYSTEM_PROMPT
    )

    print(f"Model:         {args.model}")
    print(f"Input tokens:  {input_tokens:,} (counted via the free count_tokens API)")
    try:
        est = estimate_cost(args.model, input_tokens, args.max_tokens)
        print(f"Est. cost:     {format_cost(est)} "
              f"(assuming the full {args.max_tokens:,} output tokens)")
    except KeyError as e:
        print(f"Est. cost:     unknown — {e}")

    if args.dry_run:
        print("\n[--dry-run] Stopping before generation. No money spent.")
        return 0

    print("\nCalling the API...\n")
    # output_format=Extraction → Claude is constrained to our schema and the reply
    # is parsed + validated back into an Extraction instance for us.
    response = client.messages.parse(
        model=args.model,
        max_tokens=args.max_tokens,
        system=SYSTEM_PROMPT,
        messages=messages,
        output_format=Extraction,
    )

    # The validated object rides on the text block's `.parsed_output`.
    data = next(b.parsed_output for b in response.content if b.type == "text")
    assert data is not None

    # 4. Output — either raw JSON or the formatted view.
    if args.json:
        print(data.model_dump_json(indent=2))
    else:
        render(console, data)

    # 5. Report authoritative usage and real cost.
    usage = response.usage
    total = usage.input_tokens + usage.output_tokens
    print(f"\nTokens used:   {usage.input_tokens:,} in + "
          f"{usage.output_tokens:,} out = {total:,} total")
    try:
        actual = estimate_cost(args.model, usage.input_tokens, usage.output_tokens)
        print(f"Actual cost:   {format_cost(actual)}")
    except KeyError:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
