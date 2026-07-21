"""
Example 20: prompt caching: stop re-paying for a repeated prefix.

Many real apps send the *same* long prefix on every request: a big system prompt,
a tool catalog, a document you're asking many questions about. Re-processing those
identical input tokens every time is wasteful, so Claude lets you **cache** them.

You mark a block with `cache_control={"type": "ephemeral"}`. The first request
*writes* that prefix to the cache (at ~1.25× the input price); later requests with
a byte-for-byte identical prefix *read* it from cache at **~0.1×** the price, and
faster. Caching is a **prefix match**: any change anywhere before the breakpoint
invalidates everything after it, so put the *stable* content first (system prompt,
tools, a document) and the *variable* content (the user's question) last.

This script sends two questions that share a long, identical, cached system
prefix, then reads `usage.cache_creation_input_tokens` (the write) and
`usage.cache_read_input_tokens` (the hit) so you can watch the cache pay off.

One catch worth knowing: there's a **minimum** cacheable prefix (≈2048 tokens on
Sonnet, ≈4096 on Opus/Haiku). Shorter prefixes silently won't cache, so the demo
prefix below is deliberately large.

Run it:

    secrun python examples/20_prompt_caching.py
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

# A long, STABLE prefix (must clear the model's minimum to cache: see docstring).
# We fake one by repeating a policy block; in a real app this is your big system
# prompt, a tool catalog, or a document you're answering questions about.
STABLE_PREFIX = (
    "You are Acme Corp's support assistant. Follow these policies exactly.\n"
    + "\n".join(
        f"Policy {i}: Be concise, accurate, and cite the policy number when relevant. "
        f"Never share internal pricing. Escalate any refund over $500 to a human agent. "
        f"Always confirm the customer's account email before making account changes."
        for i in range(1, 200)
    )
)


def ask(question: str):
    """Same cached system prefix every time; only the question changes."""
    resp = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=60,
        # The system block is marked cacheable. It's constant across calls, so the
        # second call reads it from cache instead of reprocessing it.
        system=[
            {"type": "text", "text": STABLE_PREFIX, "cache_control": {"type": "ephemeral"}}
        ],
        messages=[{"role": "user", "content": question}],  # variable -> not cached
    )
    u = resp.usage
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return text, u.input_tokens, u.cache_creation_input_tokens, u.cache_read_input_tokens


print(f"Stable system prefix is ~{len(STABLE_PREFIX) // 4} tokens.\n")

# First call: WRITES the prefix to cache (cache_creation > 0, cache_read == 0).
_, inp1, write1, read1 = ask("How do I reset my password?")
print(f"Call 1: input={inp1}, cache_write={write1}, cache_read={read1}")

# Second call: same prefix -> READS it from cache (cache_read > 0) at ~0.1x price.
_, inp2, write2, read2 = ask("What's your refund policy?")
print(f"Call 2: input={inp2}, cache_write={write2}, cache_read={read2}  <-- the cache paid off")

print("\nThe second call served the long prefix from cache (cache_read > 0) at ~1/10th")
print("the price, and processed faster, just by keeping the constant part up front and")
print("marking it cache_control. (If cache_read is 0, the prefix was under the minimum,")
print("or something made it differ between calls; caching needs a byte-identical prefix.)")
