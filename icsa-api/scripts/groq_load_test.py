"""AI-11: Groq production validation — 5 sequential live queries.

Usage: uvicorn must be running (real mode), then:
    python scripts/groq_load_test.py
All 5 must return HTTP 200 without RateLimitError.
"""
import time

import requests

BASE = "http://localhost:8000"
QUERIES = [
    "Good Moral Certificate requirements",
    "TOR steps",
    "Medical cert documents",
    "Library clearance",
    "Enrollment steps",
]

ok = 0
for q in QUERIES:
    r = requests.post(f"{BASE}/api/chat", json={"query": q}, timeout=30)
    d = r.json()
    print(f"Q: {q[:30]:<30} | {r.status_code} | {d.get('response_time_ms')}ms")
    ok += 1 if r.status_code == 200 else 0
    time.sleep(1)

print(f"\n{ok}/5 returned HTTP 200")
raise SystemExit(0 if ok == 5 else 1)
