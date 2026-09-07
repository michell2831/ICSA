"""DE-01: PSS read-only PostgreSQL connection check.

Run from icsa-api/:  python scripts/db_connection.py
"""
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from services import pss_service  # noqa: E402
from utils.config import ConfigError  # noqa: E402


def main():
    try:
        counts = pss_service.count_active_services()
    except ConfigError as e:
        print(f"CONFIG ERROR: {e}")
        print("Fallback habang wala pa: python scripts/etl/extract_services.py --use-fixture")
        return 1
    print(f"Connected to PSS DB. Found {counts['total']} active services.")
    for office, n in counts["per_office"].items():
        print(f"  {office}: {n}")
    sample = pss_service.fetch_active_services(limit=5)
    for s in sample:
        print(f"  - [{s['office']}] {s['name'][:60]} (SLA {s['sla_target_value']} {s['sla_target_unit']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
