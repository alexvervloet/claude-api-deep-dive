"""
Example 14: errors, timeouts, and retries (surviving the real world).

Every example so far assumed the happy path: the request succeeds. In
production it often won't. The network blips, you hit a rate limit, a model
name has a typo, the service is briefly overloaded (Anthropic returns a 529
`overloaded_error` when busy). Code that ignores this crashes on the first
hiccup.

The good news: the Anthropic SDK already does most of the work for you.

  >> The client AUTOMATICALLY RETRIES transient failures (429 rate limits,
  >> 408/409, 5xx server errors including 529 overloads, and connection
  >> errors) with exponential backoff. The default is 2 retries. You usually
  >> don't need a retry loop at all.

What you DO need is two things:

  1. Configure the client's `timeout` and `max_retries` for your use case.
  2. Catch the SDK's typed exceptions so you can react differently to a
     "fix your request" error (bad key, bad model, don't retry) versus a
     "try again later" error (rate limit, overload, which the SDK already did).

The exceptions form a hierarchy. Catch the SPECIFIC ones you handle specially,
then a broad `APIError` as a backstop: most specific first, or the broad one
shadows the rest.

Run it:

    secrun python examples/14_error_handling.py

It deliberately requests a nonexistent model to show a NotFoundError being
caught, then makes a normal call with tuned timeout/retry settings.
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

# Per-client config. `timeout` is in seconds; `max_retries` overrides the
# default of 2. (You can also override per-call with
# `client.with_options(timeout=5).messages.create(...)`.)
client = anthropic.Anthropic(timeout=20.0, max_retries=3)


def ask(model: str, question: str) -> str | None:
    """Make one request, translating each failure into a clear message.

    Order matters: list the specific subclasses before the broad `APIError`,
    or the broad clause catches everything and the specific ones never run.
    """
    try:
        response = client.messages.create(
            model=model,
            max_tokens=256,
            messages=[{"role": "user", "content": question}],
        )
        return "".join(b.text for b in response.content if b.type == "text")

    except anthropic.AuthenticationError:
        # 401: bad/missing key. Not retryable; fix the credentials.
        print("Auth failed: check ANTHROPIC_API_KEY.")
    except anthropic.NotFoundError:
        # 404: usually a typo'd or unavailable model. Not retryable.
        print(f"Model not found: {model!r}. Check the model name.")
    except anthropic.BadRequestError as e:
        # 400: malformed request (e.g. missing max_tokens, bad params).
        print(f"Bad request: {e}")
    except anthropic.RateLimitError:
        # 429: the SDK already retried with backoff and still failed.
        # Back off further, queue the work, or slow your request rate.
        print("Rate limited even after retries. Slow down or try later.")
    except anthropic.APITimeoutError:
        # The request exceeded `timeout` (and exhausted retries).
        print("Request timed out. Consider raising the timeout or streaming.")
    except anthropic.APIConnectionError:
        # Network failure before a response was received.
        print("Network error: could not reach the API. Check your connection.")
    except anthropic.APIStatusError as e:
        # Any other non-2xx (e.g. 500, or 529 overloaded_error). These ARE
        # retried by the SDK; reaching here means the retries were used up.
        print(f"API error {e.status_code} after retries: {e.message}")
    except anthropic.APIError as e:
        # Backstop for anything not caught above.
        print(f"Unexpected API error: {e}")

    return None


# 1. A request that fails predictably: caught and reported, no crash.
print("--- requesting a model that doesn't exist ---")
ask("claude-does-not-exist", "Hello?")

# 2. A normal request that succeeds, using the tuned client.
print("\n--- a normal request ---")
answer = ask("claude-haiku-4-5", "In one sentence, why is retry logic important?")
if answer:
    print(answer)
