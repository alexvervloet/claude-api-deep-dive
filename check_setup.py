"""
Setup check: run this first.

Before you run any example, run:

    secrun python check_setup.py

It answers one question: "Is my environment ready?" It checks your Python
version, that the dependencies are installed, and that your API key is in place
and tells you exactly what to fix if something's off. It makes NO API calls,
so it costs nothing and works even before you've added a key.

This script deliberately uses only Python's standard library, so it runs even
when nothing has been `pip install`ed yet, so it can tell you that the
dependencies are missing instead of crashing.
"""

import importlib.util
import os
import sys

# ANSI colors: fall back to plain text if the terminal doesn't support them.
_USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def _c(text, code):
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def ok(msg):
    print(f"  {_c('✓', '32')} {msg}")


def warn(msg):
    print(f"  {_c('!', '33')} {msg}")


def fail(msg):
    print(f"  {_c('✗', '31')} {msg}")


HERE = os.path.dirname(os.path.abspath(__file__))

# Each entry: (import name, pip name, what it's for, required?)
DEPENDENCIES = [
    ("anthropic", "anthropic", "the Claude SDK, needed by every example", True),
    ("dotenv", "python-dotenv", "reads .env config (key comes from secrun)", True),
    ("pydantic", "pydantic", "validated outputs (examples 15, extract.py)", True),
    ("rich", "rich", "pretty terminal output (example 16, extract.py)", True),
    ("fastapi", "fastapi", "the streaming server capstone", True),
    ("uvicorn", "uvicorn", "runs the streaming server", True),
    ("voyageai", "voyageai", "embeddings only (example 12), optional", False),
]


def check_python():
    print("Python version")
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 10):
        ok(f"Python {major}.{minor} (3.10+ required)")
        return True
    fail(f"Python {major}.{minor}: this repo needs Python 3.10 or newer.")
    print("    Install a newer Python from https://www.python.org/downloads/")
    return False


def check_dependencies():
    print("\nDependencies")
    missing_required = []
    missing_optional = []
    for import_name, pip_name, purpose, required in DEPENDENCIES:
        if importlib.util.find_spec(import_name) is not None:
            ok(f"{pip_name}: {purpose}")
        elif required:
            fail(f"{pip_name} MISSING: {purpose}")
            missing_required.append(pip_name)
        else:
            warn(f"{pip_name} not installed: {purpose}")
            missing_optional.append(pip_name)

    if missing_required:
        print("\n    Install everything with:")
        print("        pip install -r requirements.txt")
    return not missing_required


def _read_env_file():
    """Parse .env without needing python-dotenv to be installed yet."""
    env_path = os.path.join(HERE, ".env")
    values = {}
    if not os.path.exists(env_path):
        return None
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def check_api_key():
    print("\nAPI key")
    env = _read_env_file()
    if env is None:
        fail(".env file not found.")
        print("    Create it with:  cp .env.example .env")
        print("    (Config only; your key loads separately via secrun. See SECRETS.md.)")
        return False

    # Prefer a real environment variable, fall back to the .env value.
    key = os.getenv("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_API_KEY", "")
    if not key or key == "sk-ant-your-key-here":
        fail("ANTHROPIC_API_KEY is not set.")
        print("    Store it in your keychain and run `secrun python check_setup.py` . See SECRETS.md.")
        return False
    if not key.startswith("sk-ant-"):
        warn("ANTHROPIC_API_KEY is set but doesn't look like a Claude key "
             "(it usually starts with 'sk-ant-'). Double-check it.")
        return True
    ok("ANTHROPIC_API_KEY is set and looks right.")

    voyage = os.getenv("VOYAGE_API_KEY") or env.get("VOYAGE_API_KEY", "")
    if voyage and voyage != "pa-your-voyage-key-here":
        ok("VOYAGE_API_KEY is set (optional, for the embeddings example).")
    else:
        warn("VOYAGE_API_KEY not set; only needed for example 12 (embeddings). "
             "Skip it if you're not doing that one.")
    return True


def main():
    print(_c("Checking your setup for the Claude API deep dive...\n", "1"))
    results = [check_python(), check_dependencies(), check_api_key()]

    print()
    if all(results):
        print(_c("All set! 🎉", "1;32"))
        print("Start here:  secrun python examples/01_basic_chat.py")
        return 0
    print(_c("Not ready yet. Fix the ✗ items above, then run this again.", "1;31"))
    print("(The ! items are optional and safe to ignore for now.)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
