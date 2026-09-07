"""AI-GROQ: Groq account + API key + SDK smoke test.

Usage:  python scripts/groq_smoke_test.py
Prereq: GROQ_API_KEY set in local .env (never committed, never hardcoded).

Terminology reminder:
  Groq  = inference API (console.groq.com)     | Llama = model family on Groq
  Claude Pro = the AI Specialist's coding tool | Grok  = unrelated product
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from utils.config import ConfigError, get_groq_api_key  # noqa: E402


def main():
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")  # from .env, never hardcoded
    try:
        api_key = get_groq_api_key()
    except ConfigError as e:
        print(f"CONFIG ERROR: {e}")
        return 1

    from groq import Groq

    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with OK only."}],
        max_tokens=int(os.getenv("GROQ_MAX_TOKENS", "400")),
        timeout=int(os.getenv("GROQ_TIMEOUT_SECONDS", "10")),
    )
    text = (resp.choices[0].message.content or "").strip()
    print(f"Groq OK. Model: {model}. Response: {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
