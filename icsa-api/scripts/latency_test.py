"""AI-17: Response latency test — all 10 eval queries must finish < 6000ms.

Usage: uvicorn running (real pipeline), then:
    python scripts/latency_test.py
NOTE: the first query pre-warms the embedding model — measured from query #1
onward but a warm-up ping is sent first so results reflect steady state.
"""
import json
import time

import requests

BASE = "http://localhost:8000"
dataset = json.load(open("tests/fixtures/eval_dataset.json", encoding="utf-8"))

requests.post(f"{BASE}/api/chat", json={"query": "warm up"}, timeout=60)

results = []
for item in dataset:
    start = time.time()
    requests.post(f"{BASE}/api/chat", json={"query": item["query"]}, timeout=30)
    ms = int((time.time() - start) * 1000)
    results.append(ms)
    print(f"[{'OK' if ms < 6000 else 'SLOW'}] {ms:>5}ms | {item['query'][:40]}")

mn, mx, avg = min(results), max(results), sum(results) // len(results)
print(f"\nMin: {mn}ms | Max: {mx}ms | Avg: {avg}ms")

with open("../docs/performance-report.md", "w", encoding="utf-8") as f:
    f.write(
        f"# Performance Report\nDate: {time.strftime('%Y-%m-%d')}\n\n"
        f"| Metric | Value |\n|---|---|\n| Min | {mn}ms |\n| Max | {mx}ms |\n"
        f"| Avg | {avg}ms |\n| SLA target | < 6000ms per query |\n"
        f"| Result | {'PASS' if mx < 6000 else 'FAIL'} |\n"
    )
print("Report written -> ../docs/performance-report.md")
assert mx < 6000, "FAIL: At least one query exceeded 6000ms"
