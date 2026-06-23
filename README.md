# Claude API — A Guided Deep Dive

A hands-on playground for learning the Claude (Anthropic) API **from zero**.
You'll build a real CLI tool that answers questions about your code, and along
the way you'll understand every moving part: messages and content blocks, the
system prompt, the sampling knobs (temperature, top_p, max_tokens, stop), token
counting, cost, and the things that make Claude *Claude* — tool use and extended
thinking.

This repo is meant to be *walked through*, not just read. Each section ends with
something to run. Do the running — that's where the learning is.

---

## 0. The one big idea

The Claude API is, at its core, astonishingly simple:

> **You send a list of messages. You get back a message.**

That's it. Everything else — the system prompt, the knobs, the token math — is
detail on top of that single request/response. Hold onto that idea and nothing
below will feel complicated.

One small twist worth knowing up front: the message you get back isn't a plain
string, it's a **list of content blocks** (each tagged with a `.type`). For a
normal answer you read the `text` blocks. That same list is how Claude later
hands you its *reasoning* and its *tool requests* too — so it's worth meeting
early.

---

## 1. Setup (5 minutes)

```bash
# 1. Create an isolated Python environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API key
cp .env.example .env
#    ...then open .env and paste your key from
#    https://console.anthropic.com/settings/keys
```

> 💡 **You'll need a key for everything here, but the token-counting parts are
> free.** Unlike some APIs, Claude has no offline tokenizer — counting tokens is
> a (free, unbilled) API call. So Sections 5–6 need a key, but they never cost
> you anything. More on that below.

> 🔑 **One optional extra key.** The embeddings example (Section 8) uses
> [Voyage AI](https://www.voyageai.com/) — Anthropic's recommended embeddings
> provider — which has its own `VOYAGE_API_KEY`. Everything else uses only your
> `ANTHROPIC_API_KEY`. Both go in `.env`; the Voyage one is optional.

---

## 2. Your first request

```bash
python examples/01_basic_chat.py
```

Open [examples/01_basic_chat.py](examples/01_basic_chat.py) and read it — it's
tiny. The shape of every call you'll ever make is right there:

```python
response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=256,
    messages=[{"role": "user", "content": "In one sentence, what is an API?"}],
)
for block in response.content:
    if block.type == "text":
        print(block.text)
```

Four things to internalize:

| Thing | What it is |
|-------|-----------|
| `model` | Which model answers. `claude-haiku-4-5` is the cheap, fast default. |
| `max_tokens` | **Required.** The cap on how much the model may generate. |
| `messages` | A **list** of messages — your half of the conversation. |
| `response.content` | A **list of blocks**, not a string. Read the `text` ones. |
| `response.usage` | Exactly how many input/output tokens you were billed for. |

---

## 3. The system prompt, and roles

A conversation is a transcript, and every message has a **role**. On Claude there
are two roles inside the list:

- **`user`** — what the human says. The first message must be a `user` message.
- **`assistant`** — what the model said. You re-send past assistant messages to
  give the model **memory** — the API itself is stateless, so the conversation
  only exists in the list you send each time.

The third piece, the **system prompt** — the standing instructions, persona, and
tone — is *not* a message. It's a separate top-level `system=` parameter. Set it
once, and it steers everything. *This is your most powerful lever.*

```bash
python examples/02_roles.py
```

**Experiment:** open [examples/02_roles.py](examples/02_roles.py), change the
system prompt to `"You are a grumpy pirate."`, and rerun. Same question, totally
different voice.

---

## 4. The knobs that shape a response

These parameters control *how* the model answers. Each has its own runnable
example.

### temperature — how bold the word choices are
`0.0` = focused & repeatable · `1.0` = most varied (and Claude's default). Claude's
range is **0.0–1.0** (not 0–2). For code and facts, go low.
```bash
python examples/03_temperature.py
```

### max_tokens — a hard cap on the answer's length
Caps **output** tokens (not input), and on Claude it's **required** on every
request. The model is cut off when the budget runs out — possibly mid-sentence.
Watch `stop_reason`: `"max_tokens"` means it was truncated; `"end_turn"` means it
finished naturally.
```bash
python examples/04_max_tokens.py
```

### top_p — how many options the model may consider
"Nucleus sampling." `0.1` = only the most obvious tokens; `1.0` = everything
(default). **Tune temperature OR top_p, not both** — they interact confusingly.
```bash
python examples/05_top_p.py
```

### stop_sequences — make generation halt at a marker
A list of strings; generation ends the moment one would appear. The stop text
itself isn't included. Great for cutting lists or hitting a delimiter.
```bash
python examples/06_stop_sequences.py
```

**Quick reference:**

| Knob | Range | Raise it to... | Default |
|------|-------|----------------|---------|
| `temperature` | 0.0–1.0 | get more variety | 1.0 |
| `top_p` | 0.0–1.0 | widen the pool of candidate words | 1.0 |
| `max_tokens` | ≥1 | allow a longer answer | *(required — no default)* |
| `stop_sequences` | list of strings | end at a specific marker | none |

> 🔭 **Where the frontier is going.** On Anthropic's newest models (Claude Opus
> 4.8, Claude Fable 5) the sampling knobs `temperature`, `top_p`, and `top_k`
> have been **removed** — sending them errors. Those models steer through
> prompting plus **effort** and **thinking** controls instead (Section 8). The
> knobs above still work on the workhorse models and are genuinely worth
> understanding — just know the cutting edge is moving past them.

---

## 5. Tokens — what you actually pay for

Models don't read characters or words. They read **tokens** — chunks of text,
often word-fragments. Rough rule: 1 token ≈ 4 English characters ≈ ¾ of a word.
But "rough" isn't good enough for budgeting, so we count exactly.

Here's a real Claude difference: **there's no offline tokenizer.** You count
tokens by asking the API, via `client.messages.count_tokens(...)`. The good news
is it's **free** (not billed, uses none of your output budget) and **exact**. The
trade-off is it needs your key and a network call — and you get back a *count*,
not the individual token pieces (Anthropic's tokenizer isn't public).

```bash
python utils/tokens.py          # count a sentence's tokens (free API call)
```

Why counting matters:
1. **Cost** — you're billed per token (next section).
2. **Limits** — every model has a max context window (input + output). Overflow
   it and the request fails.
3. **Intuition** — watching the count change as you edit a prompt teaches you how
   the model "sees" your text.

See [utils/tokens.py](utils/tokens.py) for `count_tokens()` (a raw string) and
`count_message_tokens()` (a full request — including the system prompt, which
counts toward your input tokens too).

---

## 6. Cost estimation

Anthropic charges **separately for input and output tokens**, and output is
several times more expensive. [utils/pricing.py](utils/pricing.py) holds a small price table
and an `estimate_cost()` helper. (Counting is an API call; the cost *math* is
pure local computation — no network, no key.)

```bash
python examples/07_token_counting.py   # tokens -> dollars, across models
```

Sample output shows the same request costing wildly different amounts per model —
which is why **choosing the right model is part of prompt engineering.**

> ⚠️ Prices change. The table in `utils/pricing.py` is a snapshot — always confirm at
> <https://platform.claude.com/docs/en/about-claude/pricing>.

---

## 7. The first capstone: `ask.py`

Everything above comes together in one tool: ask a question about a code file,
see the token count and estimated cost *before* you spend, get the answer, and
see the *actual* usage and cost after.

```bash
# See the size and cost first — the counting call is free, so no money spent:
python hands_on/ask.py snippets/buggy.py "Is there a bug here?" --dry-run

# For real:
python hands_on/ask.py snippets/buggy.py "Is there a bug here?"

# Now turn the knobs you just learned:
python hands_on/ask.py snippets/buggy.py "Rewrite this cleanly" --temperature 0
python hands_on/ask.py snippets/buggy.py "List the issues" --max-tokens 200 --stop "4."
python hands_on/ask.py snippets/buggy.py "Explain this" --model claude-sonnet-4-6
```

Run `python hands_on/ask.py --help` to see every knob explained inline. Read the source in
[hands_on/ask.py](hands_on/ask.py) — it's commented as a tutorial, especially `build_messages()`
(how the request is assembled, with the system prompt kept separate) and the
usage/cost reporting at the end.

**Suggested exercise:** point `hands_on/ask.py` at your *own* code, try the same question
at `--temperature 0` vs `--temperature 1`, and watch both the answers and the
cost change.

---

## 8. Beyond the basics

With the core down, here are the most useful next capabilities — each is a
runnable example in the same numbered style. Every one is still just a variation
on "send messages, get a message."

### Streaming — get the answer as it's typed
`client.messages.stream(...)` delivers the response in small pieces as it's
generated, so the user sees text appear immediately. It's also the recommended
way to do long generations (it dodges request timeouts).
```bash
python examples/08_streaming.py
```

### Structured outputs — make the model return real JSON
Constrain the reply to match an exact JSON Schema you define
(`output_config={"format": ...}`). The end of fragile "please reply in JSON"
prompting. (`client.messages.parse()` with a Pydantic model is the ergonomic
version.)
```bash
python examples/09_structured_outputs.py
```

### Tool use — let the model use your code
You describe tools; the model decides when to call one and with what arguments;
*you* run it and feed the result back. This is how a model gets to actually *do*
things (query a DB, hit an API).
```bash
python examples/10_tool_use.py
```

### Extended thinking & effort — let the model reason first
Claude's signature capability: on hard problems, let it think in dedicated
`thinking` blocks before answering, and dial how much **effort** it spends. This
is the modern replacement for the temperature/top_p knobs on the newest models.
```bash
python examples/11_thinking.py
```

### Embeddings — turn text into vectors for search & similarity (via Voyage AI)
Embeddings convert text into numbers that capture *meaning*, so you can rank text
by similarity — the foundation of semantic search and RAG. **Anthropic has no
first-party embeddings endpoint and recommends [Voyage AI](https://www.voyageai.com/)**,
a separate provider with its own SDK (`voyageai`) and key (`VOYAGE_API_KEY`). The
realistic picture of a Claude app: Claude reasons, Voyage embeds. The example
ranks sentences against a query — including one that shares *no words* with it.
```bash
python examples/12_embeddings.py
```

### Multi-turn conversations — the API has no memory
Each request is stateless: Claude remembers nothing. A chatbot that "remembers"
is just *you* re-sending the whole `messages` list every turn, appending each new
user and assistant message (the `system` prompt stays separate). The example is a
tiny REPL that grows that list.
```bash
python examples/13_conversation.py
```

### Error handling & retries — surviving the real world
The network blips, you hit a rate limit, the service is briefly overloaded (529).
The SDK already retries transient failures (429/5xx/connection) with backoff; your
job is to tune `timeout`/`max_retries` and catch the *typed* exceptions so "fix
your request" errors are handled differently from "try again later" ones.
```bash
python examples/14_error_handling.py
```

### Pydantic validation — typed, validated responses
Instead of a hand-written JSON Schema + `json.loads` into an untyped dict, define
your shape as a **Pydantic model** and pass it as `output_format`. The SDK sends
the schema, constrains Claude, and hands back a *validated instance* on
`.parsed_output` — typed attributes, enforced constraints, editor autocomplete.
```bash
python examples/15_pydantic_validation.py
```

### Formatting output — Markdown, tables & code blocks
Claude answers in Markdown; dumped raw to a terminal it's a mess of literal
`**asterisks**`. The `rich` library renders Markdown, syntax-highlighted code, and
real tables in the terminal — the difference between output you skim and output
you squint at.
```bash
python examples/16_rich_output.py
```

### Server-Sent Events (SSE) — the protocol under streaming
Every streaming Claude response travels over SSE: a plain HTTP response that
stays open and drips `event: <type>` / `data: <json>` pairs until the server is
done. Claude's event stream is richer than most — it includes `message_start`,
`content_block_delta`, `message_delta`, and more. This example shows all of them
at the raw level, plus per-token timing and partial response accumulation.
```bash
python examples/17_sse.py
```

---

## 9. The second capstone: `extract.py`

Where `ask.py` returns *prose*, `extract.py` returns *data*. Point it at messy
free-form text and it pulls out a clean, typed, **validated** structure — then
shows it as a Markdown summary and a real table. It's where examples 15
(Pydantic) and 16 (rich) earn their keep on a realistic task.

```bash
# See tokens + cost first — the counting call is free:
python hands_on/extract.py snippets/meeting_notes.txt --dry-run

# Extract action items (owner, due date, inferred priority) into a table:
python hands_on/extract.py snippets/meeting_notes.txt

# Want the raw validated JSON instead? (e.g. to pipe into another tool)
python hands_on/extract.py snippets/meeting_notes.txt --json
```

Read the source in [hands_on/extract.py](hands_on/extract.py): the `Extraction` / `ActionItem`
Pydantic models *are* the schema Claude must follow, and `render()` is the rich
table. **Suggested exercise:** point it at your own meeting notes or an email, or
change the models to extract something else entirely (contacts, invoice line
items) — the prompt barely changes.

---

## 10. The third capstone: `streaming_server.py`

Where `ask.py` and `extract.py` are CLI tools, `streaming_server.py` is a web
service. It's a FastAPI backend that streams Claude responses to a browser over
SSE, showing three production concerns: token-by-token forwarding, client
disconnect detection, and error recovery with retries.

```bash
# Start the server (auto-reloads on file saves):
uvicorn hands_on.streaming_server:app --reload

# Then open: http://localhost:8000
```

Open the browser's **Network tab** and click the `/stream` request to see the raw
`text/event-stream` response. Close the tab mid-stream to watch the server log
"client disconnected" and stop the Claude call. Read the source in
[hands_on/streaming_server.py](hands_on/streaming_server.py) — the three-phase
generator (`_stream_tokens`) is the core pattern every production streaming
endpoint follows.

**Suggested exercise:** ask something that generates a long response and close the
browser tab mid-stream. Notice in the server logs that generation stops
immediately — no wasted tokens.

---

## Where to go next

You've now covered the essentials, the most common extensions, and three capstone
projects. Further on:

- **Prompt caching** — cache a large, repeated prefix so you pay ~0.1× for it on
  later requests (up to ~90% cheaper). The single biggest cost lever for
  context-heavy apps — and a natural follow-on to this repo's cost theme.
- **Vision** — pass images (and PDFs) to Claude as content blocks alongside text.
- **Citations** — have Claude cite the exact source spans it used from documents
  you provide.
- **The Batch API** — submit many requests asynchronously at 50% off, for
  non-latency-sensitive work.
- **Agents & MCP** — multi-step tool-using loops, and connecting Claude to
  external tools through the Model Context Protocol.

Each of these slots neatly on top of the "send messages, get a message" idea you
started with.

---

## File map

```
hands_on/
  ask.py                    ← capstone CLI: ask a question about a code file
  extract.py                ← capstone CLI: extract validated data from free text
  streaming_server.py       ← capstone server: stream AI responses over SSE
  static/index.html         ← browser UI for the streaming server
utils/
  tokens.py                 ← token counting via the free count_tokens API
  pricing.py                ← price table + cost estimation
snippets/buggy.py           ← a sample file to ask questions about
snippets/meeting_notes.txt  ← sample free-form text for extract.py
examples/
  01_basic_chat.py          ← the minimal request + content blocks
  02_roles.py               ← the system prompt, user / assistant
  03_temperature.py         ← randomness
  04_max_tokens.py          ← length cap + stop_reason
  05_top_p.py               ← nucleus sampling
  06_stop_sequences.py      ← halting generation
  07_token_counting.py      ← tokens & cost
  08_streaming.py           ← stream the answer as it's generated
  09_structured_outputs.py  ← guaranteed schema-conformant JSON
  10_tool_use.py            ← let the model call your functions
  11_thinking.py            ← extended thinking & effort
  12_embeddings.py          ← vectors & semantic similarity (via Voyage AI)
  13_conversation.py        ← multi-turn chat & the stateless API
  14_error_handling.py      ← timeouts, retries & typed exceptions
  15_pydantic_validation.py ← typed, validated responses via Pydantic
  16_rich_output.py         ← Markdown, tables & code blocks in the terminal
  17_sse.py                 ← SSE protocol: raw events, timing, partial accumulation
```
