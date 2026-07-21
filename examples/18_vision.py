"""
Example 18: vision: sending an image alongside text.

Every example so far sent only text. Claude is multimodal: it can also *see*
images. The request shape barely changes: the user message's `content` becomes a
*list of blocks*, where each block is either a `text` block or an `image` block.
You can then ask "what's in this picture?", read a screenshot, or pull data out of
a photo.

Two ways to provide the image, both shown here:
  - a public URL Claude fetches (`source` of type `"url"`), or
  - a local file you read and send as base64 (`source` of type `"base64"` with a
    `media_type`), which is what real apps usually do, since the image rides inside the
    request and needs no public hosting.

Images are billed as input tokens too, and the count scales with the image's pixel
dimensions: a big screenshot can cost more than a page of text. Downscale before
sending if you care about cost. (Claude *reads* images; it does not *generate*
them; image generation isn't part of the API.)

Run it (uses a public sample image):

    secrun python examples/18_vision.py

    # or point it at your own local image (sent as base64):
    secrun python examples/18_vision.py path/to/image.png
"""

import base64
import os
import sys

import anthropic
from anthropic.types import MessageParam
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("Set ANTHROPIC_API_KEY via secrun (see SECRETS.md) and try again.")

client = anthropic.Anthropic()

# A stable, public sample image: GitHub's Octocat mascot.
SAMPLE_URL = "https://avatars.githubusercontent.com/u/583231?v=4"


def image_block_from_path(path: str) -> dict:
    """Read a local image and build a base64 `image` block.

    Claude needs the bytes (base64-encoded) and the `media_type`. We guess the
    type from the extension; the API accepts png, jpeg, gif, and webp.
    """
    ext = os.path.splitext(path)[1].lower().lstrip(".") or "png"
    media_type = f"image/{'jpeg' if ext == 'jpg' else ext}"
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("ascii")
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}


# Build the image block: a local file if one was passed, else the public URL.
if len(sys.argv) > 1:
    path = sys.argv[1]
    if not os.path.exists(path):
        sys.exit(f"No such file: {path}")
    image_block = image_block_from_path(path)
    print(f"[sending local image as base64: {path}]\n")
else:
    # The URL form: Claude's server fetches the image itself.
    image_block = {"type": "image", "source": {"type": "url", "url": SAMPLE_URL}}
    print("[sending a public sample image by URL]\n")

# The one new idea: `content` is a LIST of blocks (a text block + an image block),
# not a plain string.
messages: list[MessageParam] = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image in two sentences. What stands out?"},
            image_block,  # type: ignore[list-item]
        ],
    }
]

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=300,
    messages=messages,
)

print(next(b.text for b in response.content if b.type == "text"))
print(f"\n[tokens: input {response.usage.input_tokens}, output {response.usage.output_tokens}]")
print("Notice the input tokens: the image itself is most of them. Bigger image = more tokens.")
