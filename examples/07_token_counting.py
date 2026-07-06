"""
Example 07 — counting tokens and estimating cost.
=================================================

This is where you plan and budget a request *before* paying for an answer.

Two pieces, with an important distinction between them:
  - Counting tokens is a **free API call** to `client.messages.count_tokens`.
    Free, but not offline — Claude has no local tokenizer (no `tiktoken`), so it
    needs your key and a network round-trip. It is not billed and uses none of
    your output budget.
  - Estimating cost is **pure local math** (utils/pricing.py) — multiply the token
    count by the model's price. No network, no key.

Run it (needs your key for the free counting call):

    secrun python examples/07_token_counting.py

It shows three things:
  1. How many tokens a sentence is.
  2. How a full request is counted — including the system prompt, which counts!
  3. How that token count maps to dollars across models.
"""

import os
import sys

# Make the repo-root modules (utils/pricing.py, utils/tokens.py) importable no
# matter what directory you run this from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from dotenv import load_dotenv

from utils.pricing import PRICING, estimate_cost, format_cost
from utils.tokens import count_message_tokens, count_tokens

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

# 1. A single string.
sentence = "Tokens are not the same as words!"
print(f"{sentence!r}")
print(f"  -> {count_tokens(client, sentence)} tokens\n")

# 2. A realistic request, system prompt included. Notice we pass `system`
#    separately — and it still counts toward your input tokens.
system = "You are a helpful assistant."
messages = [
    {"role": "user", "content": "Summarize the plot of Hamlet in two sentences."},
]
input_tokens = count_message_tokens(client, messages, system=system)
print(f"Request input tokens (system + messages): {input_tokens}\n")

# 3. Cost across models, assuming a 150-token answer. This part is offline math.
assumed_output = 150
print(f"Estimated cost for {input_tokens} in + {assumed_output} out:")
for model in PRICING:
    cost = estimate_cost(model, input_tokens, assumed_output)
    print(f"  {model:<18} {format_cost(cost)}")

print(
    "\nNotice how much cheaper claude-haiku-4-5 is than claude-opus-4-8 for the "
    "same request — choosing the right model matters as much as writing a good "
    "prompt."
)
