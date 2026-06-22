"""
Cost estimation for Claude models.
==================================

Anthropic bills you per *token*, and charges a different rate for tokens you send
(input tokens) versus tokens the model generates back (output tokens). Output
tokens are several times more expensive than input tokens, which is why a chatty
model — or one that "thinks" a lot, see examples/11_thinking.py — can cost more
than you expect.

Prices are quoted per 1,000,000 tokens. We store them that way below and divide
when we estimate.

⚠️  PRICES CHANGE. The numbers below are a snapshot and may be out of date by the
    time you read this. Always confirm against the official pricing page:
        https://platform.claude.com/docs/en/about-claude/pricing
    Treat this module as a *teaching tool*, not a billing source of truth.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    """Price in US dollars per 1,000,000 tokens."""
    input_per_1m: float
    output_per_1m: float


# A small, representative slice of the catalog, spanning the price spectrum from
# the fast/cheap workhorse (Haiku) to the most capable model (Fable). Add more as
# you explore. (input $/1M, output $/1M)
PRICING: dict[str, ModelPrice] = {
    "claude-haiku-4-5":  ModelPrice(input_per_1m=1.00, output_per_1m=5.00),
    "claude-sonnet-4-6": ModelPrice(input_per_1m=3.00, output_per_1m=15.00),
    "claude-opus-4-8":   ModelPrice(input_per_1m=5.00, output_per_1m=25.00),
    "claude-fable-5":    ModelPrice(input_per_1m=10.00, output_per_1m=50.00),
}

# Voyage AI embedding models (see examples/12_embeddings.py). Voyage is a SEPARATE
# provider — Anthropic's recommended embeddings service — with its own API key.
# Embeddings have no "output" to generate, so you only pay for the tokens you send
# in; we keep them in their own table with a single price per 1M tokens.
VOYAGE_EMBEDDING_PRICING: dict[str, float] = {
    "voyage-3.5-lite": 0.02,
    "voyage-3.5":      0.06,
    "voyage-3-large":  0.18,
    "voyage-code-3":   0.18,
}


# A note on prompt caching (a Claude feature worth knowing for cost): if you send
# the same large prefix on many requests, you can cache it. Cached *reads* cost
# ~0.1x the input price and cache *writes* cost ~1.25x — so repeated context gets
# up to ~90% cheaper. We don't model that here to keep the math simple, but it's
# the single biggest cost lever for context-heavy apps. See the README's
# "Where to go next".


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return the estimated cost in USD for a request/response.

    Raises KeyError with a helpful message if we don't know the model's price.
    """
    if model not in PRICING:
        known = ", ".join(sorted(PRICING))
        raise KeyError(
            f"No pricing on file for {model!r}. "
            f"Known models: {known}. "
            f"Add it to PRICING in pricing.py (check the pricing page first)."
        )
    price = PRICING[model]
    input_cost = input_tokens / 1_000_000 * price.input_per_1m
    output_cost = output_tokens / 1_000_000 * price.output_per_1m
    return input_cost + output_cost


def estimate_embedding_cost(model: str, input_tokens: int) -> float:
    """Return the estimated cost in USD for embedding `input_tokens` tokens.

    Embeddings have no output tokens, so cost depends only on the input. Prices
    are for Voyage AI (a separate provider); confirm at www.voyageai.com/pricing.
    """
    if model not in VOYAGE_EMBEDDING_PRICING:
        known = ", ".join(sorted(VOYAGE_EMBEDDING_PRICING))
        raise KeyError(
            f"No embedding pricing on file for {model!r}. "
            f"Known models: {known}. "
            f"Add it to VOYAGE_EMBEDDING_PRICING in pricing.py (check the pricing page first)."
        )
    return input_tokens / 1_000_000 * VOYAGE_EMBEDDING_PRICING[model]


def format_cost(usd: float) -> str:
    """Pretty-print a cost. Tiny amounts get more decimal places so they don't
    just show up as ``$0.00`` and look free (they aren't!)."""
    if usd < 0.01:
        return f"${usd:.6f}"
    return f"${usd:.4f}"


if __name__ == "__main__":
    # Run `python pricing.py` for a quick demo / sanity check. No API call.
    demo_model = "claude-haiku-4-5"
    cost = estimate_cost(demo_model, input_tokens=1_000, output_tokens=500)
    print(f"{demo_model}: 1,000 in + 500 out  ->  {format_cost(cost)}")

    # The same request on the most capable model costs ~10x as much:
    big = estimate_cost("claude-opus-4-8", input_tokens=1_000, output_tokens=500)
    print(f"claude-opus-4-8: 1,000 in + 500 out  ->  {format_cost(big)}")

    # Embeddings (Voyage AI) are billed on input tokens only:
    embed_cost = estimate_embedding_cost("voyage-3.5", input_tokens=1_000)
    print(f"voyage-3.5: 1,000 in  ->  {format_cost(embed_cost)}")
