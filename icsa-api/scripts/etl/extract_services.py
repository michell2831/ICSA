"""DE-05/DE-06: ETL extraction — PSS service rows → <repo>/data/extracted_services.json.

One-way data flow: PSS DB → extract → pgvector. No writes to PSS, ever.
Primary data source is the REAL PSS database. --use-fixture exists only as a
dev fallback while the read-only credential is pending (notify PM if used).

Run from icsa-api/:
  python scripts/etl/extract_services.py                # real PSS DB
  python scripts/etl/extract_services.py --use-fixture  # dev fallback
  python scripts/etl/extract_services.py --dry-run      # count only, no write
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[2]   # icsa-api/
REPO_ROOT = API_DIR.parent
sys.path.insert(0, str(API_DIR))

from services import pss_service  # noqa: E402

FIXTURE_PATH = API_DIR / "tests" / "fixtures" / "services_fixture.json"
OUTPUT_PATH = REPO_ROOT / "data" / "extracted_services.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-fixture", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.use_fixture:
        services = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        print("NOTE: fixture mode — for dev only. Real runs must use the PSS DB.")
    else:
        services = pss_service.fetch_active_services()

    records = [pss_service.to_embedding_record(dict(s)) for s in services]

    counts = Counter(r["office"] for r in records)
    if args.dry_run:
        print(f"[DRY RUN] {len(records)} active services:")
        for office, n in sorted(counts.items()):
            print(f"  {office}: {n}")
        return

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Extracted {len(records)} services -> {OUTPUT_PATH}")
    for office, n in sorted(counts.items()):
        print(f"  {office}: {n}")


if __name__ == "__main__":
    main()
