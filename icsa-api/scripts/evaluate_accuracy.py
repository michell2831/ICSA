"""AI-15: AI accuracy evaluation — 10 Q&A pairs from tests/eval_dataset.json.

Target: >= 7/10 (70%). If below, proceed to AI-16 prompt tuning.
Usage: uvicorn running (real pipeline, AI-10 done), then:
    python scripts/evaluate_accuracy.py
"""
import json
import os
import time

import requests

BASE = "http://localhost:8000"
dataset = json.load(open("tests/fixtures/eval_dataset.json", encoding="utf-8"))

hits = 0
rows = []
print("=" * 60)
for item in dataset:
    start = time.time()
    r = requests.post(f"{BASE}/api/chat", json={"query": item["query"]}, timeout=30)
    elapsed_ms = int((time.time() - start) * 1000)
    answer = r.json().get("answer", "").lower()
    matched = any(kw.lower() in answer for kw in item["expected_keywords"])
    hits += 1 if matched else 0
    status = "PASS" if matched else "FAIL"
    rows.append((item["query"], item["expected_keywords"], status, elapsed_ms))
    print(f"[{status}] {elapsed_ms:>5}ms | Q: {item['query'][:50]}")
    if not matched:
        print(f"       Expected: {item['expected_keywords']} | Got: {answer[:80]}")
print("=" * 60)
score = f"{hits}/{len(dataset)} ({hits / len(dataset) * 100:.0f}%)"
print(f"Accuracy: {score}")

docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
os.makedirs(docs_dir, exist_ok=True)
report_path = os.path.join(docs_dir, "accuracy-report.md")
with open(report_path, "w", encoding="utf-8") as f:
    f.write(f"# AI Accuracy Report\nDate: {time.strftime('%Y-%m-%d')}\nScore: {score}\n\n")
    f.write("| # | Query | Expected Keywords | Latency | Result |\n|---|---|---|---|---|\n")
    for i, (q, kws, status, ms) in enumerate(rows, 1):
        f.write(f"| {i} | {q} | {', '.join(kws)} | {ms}ms | {status} |\n")
print(f"Report written -> {report_path}")
raise SystemExit(0 if hits >= 7 else 1)