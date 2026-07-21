#!/usr/bin/env python3
"""
ask.py: Ask a question about a code snippet.

This is the main hands-on tool of the repo. You point it at a file and ask a
question about it; it builds a request to a Claude model, shows you the token
count and an estimated cost, calls the model, and prints the answer plus the
*actual* usage and cost.

It also doubles as a guided tour of the request parameters, every one of which is
exposed as a command-line flag with a short explanation in --help.

Examples
--------
  # Simplest form: explain a file
  secrun python hands_on/ask.py snippets/buggy.py "What does this code do?"

  # Find a bug, with a more capable model
  secrun python hands_on/ask.py snippets/buggy.py "Is there a bug here?" --model claude-sonnet-4-6

  # See the size and cost *before* paying for an answer.
  # (This still makes the FREE token-counting call, so it needs your key, but it
  #  never pays for generation.)
  secrun python hands_on/ask.py snippets/buggy.py "Explain this" --dry-run

  # Turn creativity down to 0 for deterministic, focused answers
  secrun python hands_on/ask.py snippets/buggy.py "Rewrite this cleanly" --temperature 0

  # Cap the answer length and stop at a marker
  secrun python hands_on/ask.py snippets/buggy.py "List 3 issues" --max-tokens 200 --stop "4."
"""

import argparse
import os
import sys

# Make the repo root importable so `utils.*` is resolvable when running from
# any directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from utils.pricing import estimate_cost, format_cost
from utils.tokens import count_message_tokens

# The newest models have removed the classic sampling knobs (temperature, top_p,
# top_k): sending them returns an error. They steer behavior through prompting +
# effort/thinking instead (see examples/11_thinking.py). We detect these so the
# tool quietly drops --temperature / --top-p for them instead of crashing.
SAMPLING_REMOVED = {"claude-opus-4-8", "claude-opus-4-7", "claude-fable-5"}


# A default system prompt. The system prompt sets the assistant's behavior and
# persona for the whole request: and on Claude it's a top-level parameter, not a
# message. See examples/02_roles.py.
DEFAULT_SYSTEM_PROMPT = (
    "You are a precise, friendly senior software engineer helping someone "
    "understand code. Be concrete, point to specific lines, and keep answers "
    "tight. If you spot a bug, explain why it's a bug before suggesting a fix."
)


def build_messages(code: str, question: str) -> list[dict]:
    """Assemble the `messages` list.

    A request is a *list of messages*, each with a `role` and `content`. The
    system prompt is NOT in this list; it rides on the top-level `system=`
    parameter (see main()). Here we send a single `user` message: the code,
    clearly fenced so the model knows where it starts and ends, then the question.

    The model replies with an `assistant` message, the part you don't
    write; the API generates it.
    """
    user_content = (
        f"Here is a code snippet:\n\n```\n{code}\n```\n\n"
        f"Question: {question}"
    )
    return [{"role": "user", "content": user_content}]


def extract_text(content: list) -> str:
    """Join the text from a response's content blocks.

    Remember `response.content` is a *list of blocks*, not a string, so we pull
    out the `text` blocks and stitch them together.
    """
    return "".join(b.text for b in content if b.type == "text")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ask a Claude model a question about a code file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", help="Path to the code snippet to ask about.")
    parser.add_argument("question", help="Your question about the code.")

    parser.add_argument(
        "--model",
        default="claude-haiku-4-5",
        help="Model to use (default: claude-haiku-4-5, the cheap, fast workhorse).",
    )
    parser.add_argument(
        "--system",
        default=DEFAULT_SYSTEM_PROMPT,
        help="Override the system prompt (the assistant's standing instructions).",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1024,
        help=(
            "Hard cap on how many tokens the model may *generate* (REQUIRED by "
            "Claude; default 1024). Limits the output, not the input. If the "
            "answer is cut off, stop_reason will be 'max_tokens'. Raise this."
        ),
    )

    # ---- The classic sampling "knobs". Each shapes the response. ----
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help=(
            "Randomness, 0.0–1.0 (Claude's range; default 1.0). 0 = focused and "
            "near-deterministic; higher = more varied. For factual code "
            "questions, low is usually better. Ignored by the newest models."
        ),
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=None,
        help=(
            "Nucleus sampling, 0.0–1.0. The model samples only from the most "
            "likely tokens whose probabilities sum to top_p. An alternative to "
            "temperature. Tune one, not both. Ignored by the newest models."
        ),
    )
    parser.add_argument(
        "--stop",
        action="append",
        default=None,
        metavar="SEQUENCE",
        help=(
            "A string that, if generated, makes the model stop immediately (the "
            "stop text itself is not included). Repeat the flag for several."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count tokens and show the cost estimate, but DON'T generate an "
             "answer. The counting call is free, so this spends no money.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    # 1. Read the code file.
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            code = f.read()
    except OSError as e:
        print(f"Could not read {args.file!r}: {e}", file=sys.stderr)
        return 1

    # 2. We need the client even for --dry-run, because counting tokens is an API
    #    call on Claude (a free one: it isn't billed and uses no output budget).
    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        print(
            "\nANTHROPIC_API_KEY is not set. Store it in your keychain and run under `secrun` "
            "(see SECRETS.md). Even --dry-run needs it for the free token-counting call.",
            file=sys.stderr,
        )
        return 1

    import anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

    # 3. Build the request and count input tokens BEFORE generating anything.
    messages = build_messages(code, args.question)
    input_tokens = count_message_tokens(
        client, messages, model=args.model, system=args.system
    )

    print(f"Model:         {args.model}")
    print(f"Input tokens:  {input_tokens:,} (counted via the free count_tokens API)")
    try:
        # We don't know the output size yet, so estimate against the max_tokens
        # cap to give a worst-case ballpark.
        est = estimate_cost(args.model, input_tokens, args.max_tokens)
        print(f"Est. cost:     {format_cost(est)} "
              f"(assuming the full {args.max_tokens:,} output tokens)")
    except KeyError as e:
        print(f"Est. cost:     unknown ({e})")

    if args.dry_run:
        print("\n[--dry-run] Stopping before generation. No money spent.")
        return 0

    # 4. Assemble the request. max_tokens and system always go; the sampling
    #    knobs go only if set AND the model accepts them.
    request: dict = {
        "model": args.model,
        "max_tokens": args.max_tokens,
        "system": args.system,
        "messages": messages,
    }
    if args.model in SAMPLING_REMOVED and (
        args.temperature is not None or args.top_p is not None
    ):
        print(f"\n(note: {args.model} ignores temperature/top_p, so dropping them.)")
    else:
        if args.temperature is not None:
            request["temperature"] = args.temperature
        if args.top_p is not None:
            request["top_p"] = args.top_p
    if args.stop is not None:
        request["stop_sequences"] = args.stop

    print("\nCalling the API...\n")
    response = client.messages.create(**request)

    # 5. Print the answer (stitched from the text content blocks).
    print("=" * 70)
    print(extract_text(response.content))
    print("=" * 70)

    # `stop_reason` tells you WHY the model stopped:
    #   "end_turn"      -> it finished naturally
    #   "max_tokens"    -> it hit your --max-tokens cap (answer is truncated!)
    #   "stop_sequence" -> it hit one of your --stop strings
    print(f"\nstop_reason:   {response.stop_reason}")

    # 6. Report the AUTHORITATIVE usage from the response, and the real cost.
    usage = response.usage
    total = usage.input_tokens + usage.output_tokens
    print(f"Tokens used:   {usage.input_tokens:,} in + "
          f"{usage.output_tokens:,} out = {total:,} total")
    try:
        actual = estimate_cost(args.model, usage.input_tokens, usage.output_tokens)
        print(f"Actual cost:   {format_cost(actual)}")
    except KeyError:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
