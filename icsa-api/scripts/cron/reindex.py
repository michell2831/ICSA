#!/usr/bin/env python3
"""DE-07: Nightly re-index — ETL extract + batch embed, logged to <repo>/logs/reindex.log.

Cron (2 AM daily):
  0 2 * * * cd /path/to/icsa-ai-service/icsa-api && python scripts/cron/reindex.py
Manual trigger (from icsa-api/):
  python scripts/cron/reindex.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = API_DIR.parent
LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
log_path = LOG_DIR / "reindex.log"
start = datetime.datetime.now()

result = subprocess.run(
    [sys.executable, "scripts/etl/extract_services.py"],
    capture_output=True, text=True, cwd=API_DIR,
)
embed = subprocess.run(
    [sys.executable, "scripts/run_embedding.py"],
    capture_output=True, text=True, cwd=API_DIR,
)

with open(log_path, "a") as f:
    f.write(f"{start:%Y-%m-%d %H:%M:%S} | extract: {result.returncode} | embed: {embed.returncode}\n")

print("Reindex complete:", start)
if result.returncode or embed.returncode:
    print("WARNING — non-zero exit code. Check logs/reindex.log and stderr:")
    print(result.stderr[-500:] if result.stderr else "", embed.stderr[-500:] if embed.stderr else "")
