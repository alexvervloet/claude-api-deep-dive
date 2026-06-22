"""
Example 12 — embeddings & semantic similarity (via Voyage AI).
==============================================================

So far every example used a *chat* model that produces text. Embeddings are
different: an embeddings model turns a piece of text into a list of numbers (a
"vector") that captures its *meaning*. Texts with similar meaning end up with
similar vectors — even if they share no words.

This is the engine behind semantic search, recommendations, clustering, and
"retrieval-augmented generation" (RAG), where you find the most relevant
documents to stuff into a Claude prompt.

>> Important: this one is a DIFFERENT PROVIDER.
   Anthropic does not offer a first-party embeddings endpoint — it recommends
   Voyage AI. Voyage is a separate service with its own Python SDK (`voyageai`)
   and its own API key (`VOYAGE_API_KEY`), distinct from your Anthropic key.
   That's the realistic picture: in a Claude app, Claude does the reasoning and
   Voyage does the embeddings.

A nice Voyage feature worth knowing: `input_type`. You embed your search *query*
with `input_type="query"` and your *documents* with `input_type="document"`.
Voyage optimizes each side for retrieval, which improves the match quality. We
use both below.

How we measure "similar": **cosine similarity** — the cosine of the angle between
two vectors. It ranges from -1 (opposite) to 1 (identical direction). Closer to 1
means more similar in meaning. We compute it by hand, no math libraries needed.

Run it (needs VOYAGE_API_KEY in .env):

    python examples/12_embeddings.py
"""

import math
import os
import sys

# Make the repo-root modules (pricing.py) importable no matter where you run from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import voyageai
from dotenv import load_dotenv

from pricing import estimate_embedding_cost, format_cost

load_dotenv()
if not os.getenv("VOYAGE_API_KEY"):
    sys.exit(
        "Set VOYAGE_API_KEY in .env (get one at https://www.voyageai.com/). "
        "This example uses Voyage AI, not Anthropic — see the docstring."
    )

# The Voyage client reads VOYAGE_API_KEY from the environment automatically.
vo = voyageai.Client()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)


query = "How do I reset my password?"
candidates = [
    "Steps to recover a forgotten login credential.",  # same meaning, no shared words
    "Our office is open from 9am to 5pm.",              # unrelated
    "Click 'Forgot password' to receive a reset link.", # clearly relevant
]

model = "voyage-3.5"

# Embed the query and the documents separately, telling Voyage which is which.
query_result = vo.embed([query], model=model, input_type="query")
doc_result = vo.embed(candidates, model=model, input_type="document")

query_vec = query_result.embeddings[0]
candidate_vecs = doc_result.embeddings

print(f"Query: {query!r}\n")
print("Ranked by semantic similarity:")
scored = sorted(
    zip(candidates, candidate_vecs),
    key=lambda pair: cosine_similarity(query_vec, pair[1]),
    reverse=True,
)
for text, vec in scored:
    print(f"  {cosine_similarity(query_vec, vec):.3f}  {text}")

print(f"\n(Each vector has {len(query_vec)} dimensions.)")

# Embeddings are cheap, but not free. Each result reports the tokens billed.
tokens = query_result.total_tokens + doc_result.total_tokens
print(f"Billed {tokens} input tokens -> "
      f"{format_cost(estimate_embedding_cost(model, tokens))}")
