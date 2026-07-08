"""
Example 19 — the Message Batches API: half price, for work that isn't urgent.
=============================================================================

Every example so far made *synchronous* calls: you ask, you wait, you get an
answer. But a lot of real work isn't interactive — classify 10,000 reviews,
summarize a backlog of tickets, score a dataset. For that, the **Message Batches
API** is the right tool: you submit many requests at once, Anthropic processes
them (usually within an hour, max 24h), and you pay **50% less** on all tokens.

The lifecycle (it mirrors a job queue):

  1. Build a list of requests — each a `Request(custom_id, params)`.
  2. Create the batch   (messages.batches.create) — this starts processing.
  3. Poll until done    (messages.batches.retrieve) — processing_status -> "ended".
  4. Stream results     (messages.batches.results) — keyed by your custom_ids.

Two things to internalize:
  - You wrap each request's parameters in `MessageCreateParamsNonStreaming` — the
    same arguments you'd pass to `messages.create`, just packaged.
  - **Results come back in any order.** Always match them to inputs by
    `custom_id`, never by position.

Because a batch can take a while, this script does NOT block forever — it prints
the batch id and shows you how to check on it. Re-run with the id to poll & fetch.

Run it:

    secrun python examples/19_batch_api.py            # create a batch
    secrun python examples/19_batch_api.py <batch_id> # check status / fetch results

    secrun python examples/19_batch_api.py msgbatch_013HFWXDBXqAdrbDUDbjvTNT
"""

import os
import sys

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

# Three independent jobs. In real life this might be thousands of items.
PROMPTS = {
    "review-1": "Classify sentiment as positive/negative/neutral: 'Battery lasts forever, love it.'",
    "review-2": "Classify sentiment as positive/negative/neutral: 'Arrived broken and support ignored me.'",
    "review-3": "Classify sentiment as positive/negative/neutral: 'It's a phone. It works.'",
}


def create_batch() -> str:
    # --- Build the requests. Each carries a custom_id (to match the answer back)
    # and `params` = exactly what you'd pass to messages.create, wrapped. ---
    requests = [
        Request(
            custom_id=cid,
            params=MessageCreateParamsNonStreaming(
                model="claude-haiku-4-5",
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}],
            ),
        )
        for cid, prompt in PROMPTS.items()
    ]

    batch = client.messages.batches.create(requests=requests)
    print(f"[created batch: {batch.id}  status={batch.processing_status}]")
    print(
        "\nThe batch is now processing (50% cheaper than live calls). Check on it with:"
    )
    print(f"    secrun python examples/19_batch_api.py {batch.id}")
    return batch.id


def check_batch(batch_id: str) -> None:
    batch = client.messages.batches.retrieve(batch_id)
    counts = batch.request_counts
    print(
        f"status: {batch.processing_status}   "
        f"(succeeded={counts.succeeded}, errored={counts.errored}, processing={counts.processing})"
    )

    if batch.processing_status != "ended":
        print(
            "Not finished yet — batches run within 24h (usually <1h). Re-run this to check again."
        )
        return

    # --- Stream results. They arrive in ANY order, so key by custom_id. ---
    print("\nResults:")
    for result in client.messages.batches.results(batch_id):
        if result.result.type == "succeeded":
            text = next(
                (b.text for b in result.result.message.content if b.type == "text"), ""
            )
            print(f"  {result.custom_id}: {text.strip()}")
        else:
            print(f"  {result.custom_id}: [{result.result.type}]")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_batch(sys.argv[1])
    else:
        create_batch()
