# Chapter 2: The Same Idea, a Second Dialect

*This is the textbook chapter for the Claude API deep dive. The [README](README.md) is the lab manual; this is the lecture. It assumes you have read [Chapter 1](../openai-api-deep-dive/TEXTBOOK.md), because this chapter is deliberately not a rerun. The theory of tokens, statelessness, sampling, and streaming carries over untouched. What this chapter covers is why a second provider is worth learning at all, where Anthropic's design genuinely differs, and what those differences teach you about the design space.*

---

## 2.1 Why learn the same thing twice

There is an old piece of advice in programming languages: your second language teaches you more than your first, because it shows you which of your habits were the language and which were the craft. The same holds for LLM APIs. After the OpenAI dive, you know that you send a list of messages and get a message back. But you do not yet know which parts of that experience are essential and which are one company's taste. The Claude API is close enough to feel familiar within minutes and different enough to draw the line for you.

A word on the company, because its history shows up in its API design. Anthropic was founded in 2021 by former OpenAI researchers, including Dario and Daniela Amodei, with an explicit focus on AI safety research. Its signature training technique, constitutional AI, trains the model to critique and revise its own outputs against a written set of principles, rather than relying only on human raters for every judgment. You do not need to know any of that to call the API. But it explains some of what you will notice: the heavy investment in making the model's reasoning inspectable, the early and thorough tool-use support, and a certain conservatism in the model's default behavior. Companies ship their values the way they ship their org charts.

There is also a blunt practical reason to know both APIs. Real engineering teams increasingly run multi-provider: one model for the expensive reasoning path, another for the cheap high-volume path, a fallback for outages, and a bake-off whenever a new model releases. The engineer who can swap providers in an afternoon, because the differences hold no surprises, is more useful than the one who has memorized one SDK deeply. This entire course is provider-agnostic for that reason.

## 2.2 The response is a list, and that is not pedantry

The first difference you meet is on the very first call. Where a chat completion hands you a string, Claude hands you a list of **content blocks**, each tagged with a type. A plain answer is a list containing one text block, and for about ten minutes this feels like ceremony: why make me loop over a list to get a sentence?

Because the list is load-bearing. When you later ask Claude to think before answering, its reasoning arrives as a `thinking` block sitting in that same list, ahead of the text. When it wants to use one of your tools, the request arrives as a `tool_use` block, possibly alongside text explaining what it is doing. When you send an image, you send it as an `image` block in your own message's content list. One response can carry several of these at once: some visible reasoning, a remark to the user, and two tool calls, each a typed item in a single list.

Compare the alternative. OpenAI's chat completions started with `message.content` as a plain string, and every capability added since has had to live somewhere else: tool calls in a separate `tool_calls` field, refusals in a `refusal` field, and so on, each a new appendix on the response object. Anthropic paid a small ergonomic tax on day one (you loop over blocks even for "hello") and bought a response shape that has absorbed every new capability without changing. This is a classic API design tradeoff, worth filing away for your own APIs: a uniform container costs you in the simple case and pays you in every complicated one.

## 2.3 Small differences that are actually philosophy

A handful of parameter-level differences look like trivia and are not. Each encodes a position on a real question.

**The system prompt is not a message.** On Claude, standing instructions go in a top-level `system` parameter, physically separate from the `messages` list, which contains only `user` and `assistant` turns. On OpenAI, the system prompt is just the first message, structurally identical to any other. Anthropic's separation makes a quiet argument: the developer's instructions and the conversation are different kinds of thing, and the API's shape should say so. It does not make the instructions unbreakable (the Prompt Injection dive will disabuse you of that), but keeping "what the developer configured" apart from "what anyone said" is the right mental model, and here the type system enforces it.

**`max_tokens` is required.** Every Claude request must state the most output it will accept; there is no "up to the model maximum" default. This annoys newcomers precisely because it does its job. Output tokens are the expensive kind, and an unbounded default means your bill's worst case is set by the model's enthusiasm rather than by you. Requiring the cap forces a budgeting decision to the front of every request. After the Production dive you will recognize this as a provider building a guardrail into the interface itself, and you may find you miss it on APIs that let you omit it.

**Temperature runs 0 to 1, not 0 to 2.** Same knob, different scale, and a reminder that these numbers are not portable constants. A temperature copied from an OpenAI code sample into a Claude call means something different. Translate settings when you switch providers; never paste them.

**The stop reason speaks the same truth in a different accent.** Where OpenAI says `finish_reason: "length"`, Claude says `stop_reason: "max_tokens"`; where one says `"stop"`, the other says `"end_turn"`. The lesson from Chapter 1 stands unchanged: check it on every response, because a truncated answer that your code treats as complete is a bug you will not notice until a user does.

**There is no offline tokenizer.** OpenAI publishes its tokenizer, so you can count tokens locally with tiktoken. Anthropic keeps its tokenizer private and instead offers a free, unbilled counting endpoint: exact numbers, but a network call and no view of the individual pieces. Reasonable people disagree about which policy is better; you just need to know which regime you are in, because it changes where "how big is this prompt?" can run (an offline test suite versus something with network access).

## 2.4 Extended thinking: paying for deliberation you can read

Chapter 1 introduced reasoning models as a black box: hidden tokens, better answers, higher bill. Claude's version, **extended thinking**, opens the box partway. Ask for it and the response leads with a `thinking` block: the model working through the problem, considering branches, correcting itself, before the polished answer follows in a text block.

Why does deliberation help at all? A language model produces each token in roughly constant time. If it must answer immediately, the whole solution has to fall out in one forward pass per token of answer, with nowhere to hold intermediate results. Letting it generate reasoning first gives it scratch space: earlier tokens become working memory for later ones. Chain-of-thought prompting (Chapter 3) exploits this by asking nicely; thinking models were trained so the scratch work is a native, dedicated phase rather than a stylistic request.

Being able to read the scratch work matters more than it first appears. When a model gets a hard question wrong, the transcript of its thinking usually shows you where: a misread constraint, a wrong assumption adopted early and never revisited. That converts debugging from vibes to evidence. One honest caution, established by interpretability research (Anthropic's own among it): a model's stated reasoning is not guaranteed to be a faithful record of its actual computation. Read thinking blocks as a useful window, not a sworn deposition.

The control surface here is **effort**: how hard to think, dialed low for routine questions and high for genuinely hard ones. And this points at where the whole field is heading. On Anthropic's newest models, the classic sampling knobs (temperature, top_p, top_k) are gone entirely; sending them is an error. Steering has moved from "how random should the word choices be" to "how much deliberation should this question get." The knobs you learned remain worth knowing, both because the workhorse models still use them and because they teach you what sampling is. But you are learning them at the moment the frontier is trading them in, and it is better to know that than to discover it from an error message.

## 2.5 Tool use, and a company that went all in on it

The tool-use loop on Claude is the loop from Chapter 1 with the names changed: you describe tools, the model replies with a `tool_use` block naming one and supplying arguments, you execute it, you send back a `tool_result` block, and the model continues. Nothing conceptually new.

What is worth knowing is the emphasis. Anthropic has bet heavily on Claude as a model that *acts*: it is the model inside Claude Code, one of the most widely used agentic coding tools, and Anthropic created the Model Context Protocol (MCP), an open standard for connecting models to tools and data, which the rest of the industry, OpenAI included, went on to adopt. That protocol gets its own dive later in the series. The practical consequence for you is that the patterns in this repo's tool-use example are not a side feature; they are the foundation the second half of this course keeps building on, and the ecosystem around this particular provider assumes you know them.

Structured outputs, similarly, work the way Chapter 1 taught: supply a schema (or a Pydantic model), get output constrained to match. The concepts transfer; only the parameter names differ. That is the recurring good news of this chapter.

## 2.6 Caching you must ask for, and the missing endpoint

Two differences are less about philosophy and more about operations, and both affect real bills.

**Prompt caching is explicit.** OpenAI caches repeated prompt prefixes automatically and quietly discounts them. Anthropic makes you mark the cacheable region yourself with a `cache_control` annotation, and prices it sharply: writing the cache costs about 1.25 times the normal input rate, and reading it costs about a tenth. The structural rule is identical on both platforms (constant material first, variable question last, because caching is a prefix match), but the explicit version changes your posture. Automatic caching is a discount that happens to you; explicit caching is a design decision you make, with a small penalty when you mark something that never repeats and a large reward when you mark the right thing. For context-heavy applications, a system prompt plus reference documents re-read at a tenth of the price is routinely the single largest cost lever available, bigger than model choice.

**There are no first-party embeddings.** Anthropic does not offer an embeddings endpoint at all; it points customers at Voyage AI, a specialist provider. So a realistic Claude application is a two-vendor system: Voyage embeds, Claude reasons. This dive's RAG capstone is built that way on purpose, because the arrangement teaches something the single-vendor version hides: an AI application is an assembly of separable services (generation, embeddings, and later reranking, moderation, evaluation), and the generation model is just the most famous part. Mixing vendors per component is normal practice, not a workaround.

One more operational note: alongside the usual 429s and 5xxs, Claude has a status code of its own, 529, meaning the service is overloaded. The SDK retries it like the others. You only need to recognize it so an incident dashboard does not send you searching for a bug in your own request.

## 2.7 The dialect map

For reference, the differences in one place. Everything not listed here transfers directly.

| Concern | OpenAI (Chat Completions) | Claude (Messages) |
|---|---|---|
| Response shape | `message.content` string, plus side fields | list of typed content blocks |
| System instructions | first message, role `system` | top-level `system` parameter |
| Output cap | `max_tokens` optional | `max_tokens` required |
| Temperature range | 0 to 2 | 0 to 1 (removed on newest models) |
| "Why did it stop?" | `finish_reason`: `stop`, `length` | `stop_reason`: `end_turn`, `max_tokens` |
| Token counting | offline, tiktoken | free API endpoint, tokenizer private |
| Prompt caching | automatic | explicit `cache_control`, ~1.25x write / ~0.1x read |
| Embeddings | first-party endpoint | none; Voyage AI recommended |
| Reasoning | hidden reasoning tokens | visible `thinking` blocks, effort control |
| Overload signal | 429 / 5xx | those, plus 529 |

Read down that table and a pattern emerges. None of these differences touch the one big idea; all of them are positions on second-order questions (who sets the budget, what is visible, what is automatic). That is what "dialect" means, and it is why the third provider you meet, whoever it is, will take you an afternoon.

## 2.8 Where this chapter leaves you

The lab mirrors the OpenAI dive deliberately: the same four capstones (ask a question about code, extract structured data, stream to a browser, build RAG from scratch), rebuilt in the second dialect. Doing the same builds twice sounds redundant and is the opposite; it is the controlled experiment that separates the concepts from the syntax. If you did the first dive, you will move fast, and the moments of friction (looping over content blocks, being forced to pick a max_tokens, wiring a second vendor for embeddings) are exactly the curriculum.

From here the course stops teaching interfaces and starts teaching judgment. You now have two providers' worth of evidence that the API call is the easy part. The next chapter takes the request you already know how to send and asks the harder question: what should the words in it actually say?

---

*Lab manual: [README.md](README.md) · Exercises: [EXERCISES.md](EXERCISES.md) · Previous: [The API Call](../openai-api-deep-dive/TEXTBOOK.md) · Next: [Prompt Engineering](../prompt-engineering-deep-dive/TEXTBOOK.md)*
