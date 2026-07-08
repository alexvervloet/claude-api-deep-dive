# Exercises — make the learning stick

Reading code teaches you less than *predicting* what it will do and then checking.
This file turns each section of the [README](README.md) into a few quick
active-recall prompts: a thing to predict, a thing to change, and a question to
answer from memory. None take more than a couple of minutes.

How to use it: work the section in the README first, then come back here. For each
exercise, **commit to an answer before you run or reveal** — the prediction is
where the learning happens, even (especially) when you're wrong. Answers are
hidden behind ▸ toggles.

> Most of these cost a fraction of a cent. The ones marked **(free API call)**
> only count tokens, which Claude never bills for — so they're free but still need
> your key.

---

## Section 2 — Your first request

**Predict.** Before running `examples/01_basic_chat.py`: is `response.content` a
string you can `print()` directly, or something else? What does the loop
`for block in response.content` tell you?

<details><summary>▸ Answer</summary>

It's a **list of content blocks**, not a string. Each block has a `.type`; for a
plain answer you read the `text` blocks. That same list is how Claude later hands
you `thinking` and `tool_use` blocks too — which is why it's worth meeting on day
one.
</details>

**Do.** Remove the `max_tokens=256` argument from the call and rerun. What happens,
and what does that teach you about Claude specifically?

<details><summary>▸ Answer</summary>

It errors — `max_tokens` is **required** on every Claude request. Other APIs let
you omit it; Claude does not. It's the cap on how much the model may generate.
</details>

---

## Section 3 — The system prompt, and roles

**Recall.** On Claude, where does the system prompt go — is it a message in the
`messages` list, like `user` and `assistant`?

<details><summary>▸ Answer</summary>

No. The system prompt is a separate top-level `system=` parameter, *not* a message.
Only `user` and `assistant` are roles inside the `messages` list, and the first
message must be `user`.
</details>

**Do.** Open `examples/02_roles.py` and set the system prompt to
`"You answer only in haiku."` Rerun. Then try moving that instruction into the
`user` message instead. Which placement steers more reliably?

---

## Section 4 — The knobs

**Predict, then run.** You run `examples/03_temperature.py` twice at
`temperature=0`. How similar will the answers be? Now twice at `temperature=1.0`
(Claude's *maximum* — note the range is 0–1, not 0–2)?

<details><summary>▸ Answer</summary>

At `0` they'll be nearly identical (focused, near-deterministic — though never a
100% guarantee). At `1.0` they'll vary. Note Claude's temperature range tops out
at 1.0, unlike some other APIs that go to 2.0.
</details>

**Do.** In `examples/04_max_tokens.py`, set `max_tokens` to something tiny like
`10` and ask for a paragraph. Inspect `stop_reason`. What value do you get, and
what does it mean?

<details><summary>▸ Answer</summary>

`"max_tokens"` — the model was cut off by your cap, not because it was done. A
natural finish shows `"end_turn"`. Watching `stop_reason` is how you detect
truncated answers in real code.
</details>

**Recall.** On the newest models (Opus 4.8, Fable 5), what happens if you send a
`temperature` or `top_p` parameter, and what replaced those knobs?

<details><summary>▸ Answer</summary>

The request **errors** — those sampling knobs have been removed on the newest
models. They steer through prompting plus **effort** and **thinking** controls
instead (see Section 8 / `examples/11_thinking.py`). The knobs still work on the
workhorse models and are worth understanding — just know the frontier is moving
past them.
</details>

---

## Section 5 — Tokens **(free API call)**

**Recall.** Why can't you count Claude tokens offline the way you can with some
other APIs?

<details><summary>▸ Answer</summary>

Anthropic ships no public/offline tokenizer. You count by asking the API
(`client.messages.count_tokens(...)`). The good news: it's **free** (unbilled,
uses no output budget) and **exact**. The trade-off: it needs your key and a
network round-trip, and you get back a *count*, not the individual token pieces.
</details>

**Do.** Run `secrun python utils/tokens.py`, then edit the `sample` string to add your
system prompt's worth of text. Watch the count climb. Why does the system prompt
count toward your *input* tokens even though it isn't in the `messages` list?

<details><summary>▸ Answer</summary>

Because everything you send the model — system prompt, messages, and any tool
definitions — is input the model has to read, and you're billed for all of it.
`count_message_tokens()` takes a `system=` argument precisely so the number
matches what you'll actually pay.
</details>

---

## Section 6 — Cost **(offline math)**

**Predict.** A request is 2,000 input tokens and 500 output tokens. Using the
prices in `utils/pricing.py`, will it cost more on `claude-haiku-4-5` or
`claude-opus-4-8`? Roughly how many times more?

<details><summary>▸ Answer</summary>

Far more on Opus. Do the arithmetic with `estimate_cost()` to see the exact
multiple — and notice that **output** tokens dominate, since output is priced ~5x
higher than input on every model. Choosing the right model for a task is real
money saved. (The counting in Section 5 is an API call; this cost *math* is pure
local computation — no network, no key.)
</details>

**Recall.** `utils/pricing.py` mentions prompt caching. If you send the same large
prefix on 100 requests, roughly how much cheaper can the cached portion get?

<details><summary>▸ Answer</summary>

Up to ~90%. Cache *reads* cost ~0.1x the input price (writes cost ~1.25x), so
repeated context gets dramatically cheaper. It's the single biggest cost lever for
context-heavy apps — see the README's "Where to go next."
</details>

---

## Section 7 — Capstone: `ask.py`

**Predict, then run.** `ask.py --dry-run` is described as spending no money — yet
it still needs your API key. Why?

<details><summary>▸ Answer</summary>

Because on Claude, counting tokens is itself an API call (a free, unbilled one).
`--dry-run` skips the paid *generation* step but still makes the free counting
call to show you the size and cost estimate — so it needs the key but costs
nothing.
</details>

**Do.** Run `ask.py snippets/buggy.py "Is there a bug here?" --model claude-opus-4-8
--temperature 0`. Watch the note it prints about the temperature flag. Why does it
drop the flag instead of crashing?

<details><summary>▸ Answer</summary>

Opus 4.8 has removed the sampling knobs, so sending `temperature` would error. The
tool knows this (see its `SAMPLING_REMOVED` set) and quietly drops the flag for
those models — a small example of writing code that's robust to the API's frontier
moving.
</details>

**Stretch.** Point `ask.py` at one of your own files and compare the dry-run
estimate to the actual cost printed after a real run. Where do they diverge, and
why?

---

## Section 8 — Beyond the basics

**Recall.** In tool use (`examples/10_tool_use.py`), Claude decides to call your
tool. Does the API run the tool for you?

<details><summary>▸ Answer</summary>

No. Claude only emits a `tool_use` block with the tool *name and arguments*. **You**
run it and feed the result back as a `tool_result` block in a follow-up message.
Claude never executes your code — it just requests the call.
</details>

**Predict, then run.** In `examples/11_thinking.py`, the response interleaves
`thinking` blocks and `text` blocks. Are the thinking tokens billed, and as input
or output?

<details><summary>▸ Answer</summary>

They're billed as **output** tokens — a thoughtful answer literally costs more,
because reasoning is generation. That's the tradeoff: more care for more money. The
example prints `usage` so you can see it.
</details>

**Recall.** Embeddings (`examples/12_embeddings.py`) don't use your Anthropic key.
What do they use, and why?

<details><summary>▸ Answer</summary>

Voyage AI — a *separate* provider that Anthropic recommends for embeddings, with
its own SDK (`voyageai`) and key (`VOYAGE_API_KEY`). Anthropic has no first-party
embeddings endpoint. The realistic shape of a Claude app: Claude reasons, Voyage
embeds.
</details>

**Predict.** Can `examples/12_embeddings.py` rank a sentence highly even if it
shares *no words* with the query?

<details><summary>▸ Answer</summary>

Yes — that's the whole point. Embeddings capture *meaning*, not word overlap, so
"the feline napped" can rank near "a cat is sleeping." This is what powers semantic
search and RAG.
</details>

**Do.** Run `examples/08_streaming.py` and `examples/01_basic_chat.py` back to
back. Total time is similar, so what did streaming actually buy you?

<details><summary>▸ Answer</summary>

Time-to-*first-token*. The user starts reading immediately instead of waiting for
the whole answer. Same total time, far better perceived responsiveness — which is
why chat UIs stream. (Streaming is also the recommended way to do long generations,
since it dodges request timeouts.)
</details>

**Recall (vision, `18_vision.py`).** A text request sends a string for `content`.
What does an image request send, and what are the two `source` types?

<details><summary>▸ Answer</summary>

A **list of blocks** — a `text` block and an `image` block — in one user message.
The image `source` is either `{"type": "url", ...}` (Claude fetches it) or
`{"type": "base64", "media_type": ..., "data": ...}` (you inline the bytes). The
image is billed as input tokens, scaled by its pixel size.
</details>

**Recall (batch, `19_batch_api.py`).** What do you trade for the Batch API's 50%
discount, and why must you match results by `custom_id` rather than position?

<details><summary>▸ Answer</summary>

You trade **immediacy** — results land within 24h (usually <1h) instead of
instantly. Results come back in **any order**, so the only reliable way to tie an
answer to its request is the `custom_id` you set on each `Request`.
</details>

**Predict (caching, `20_prompt_caching.py`).** On the second call, `cache_read_input_tokens`
jumps from 0 to a big number. Why — and what would make it stay 0?

<details><summary>▸ Answer</summary>

The first call **wrote** the long system prefix to the cache; the second call's
prefix is byte-for-byte identical, so it's **read** from cache (~0.1× price). It
stays 0 if the prefix changes between calls (a silent invalidator) or is under the
model's minimum cacheable size (≈4096 tokens on Haiku) — caching is a prefix match.
</details>

**Do (async, `21_async_concurrency.py`).** It runs 6 prompts sequentially, then
4-at-a-time. Why is the concurrent run faster, and what is the `Semaphore` for?

<details><summary>▸ Answer</summary>

Each request is mostly **idle network waiting**, so overlapping them finishes in
about the time of the slowest call. The `Semaphore` caps how many run at once, so
you get the speedup without blowing past your account's **rate limit**.
</details>

---

## Capstones 9, 10 & 11

**Do (`extract.py`).** Run it on `snippets/meeting_notes.txt`, then add a line like
`"Nobody owns the budget review."` and rerun. How did the validated extraction
handle an action item with no clear owner?

**Do (`streaming_server.py`).** Start the server, open the browser, ask for a long
answer, and watch the `event:` / `data:` pairs in the Network tab's `/stream`
request. Then close the tab mid-answer and check the server logs. What did the
server do the instant you disconnected, and why does it save money?

<details><summary>▸ Answer</summary>

It detected the client disconnect and stopped the Claude call immediately — no
further tokens generated, nothing billed for output you'd never see. Detecting
disconnects is a real production cost lever, not just tidiness.
</details>

**Predict, then run (`rag.py`).** Run `secrun python hands_on/rag.py`, then run it again
with `--no-rag`. Will the answer change? Which one can you trust, and why?

<details><summary>▸ Answer</summary>

With retrieval, the model answers from the fact pasted into the prompt ("30
days"). With `--no-rag` there's no source — "Nimbus Notes" is made up — so it
guesses or admits it doesn't know. That's the whole idea: a model can only answer
from what's in its context window, and RAG decides what to put there.
</details>

**Do (`rag.py`).** Add a new fact to `KNOWLEDGE_BASE` (say,
`"Nimbus Notes can import notebooks from Evernote and Notion."`) and ask a
question only that fact can answer. Use `--show-prompt` to confirm it actually got
retrieved into the context. If it didn't, what would you try — reword the
question, or raise `-k`?

---

### Where to take it next

Invent your own. The best exercise is a question *you* genuinely don't know the
answer to — change one thing, predict the effect, run it, and reconcile the
difference. That loop is the whole skill.
