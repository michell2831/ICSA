"""AI-09: Idempotent batch embedding run — services JSON → pgvector.

Run from icsa-api/:
  python scripts/run_embedding.py                 # <repo>/data/extracted_services.json (real PSS data)
  python scripts/run_embedding.py --use-fixture   # dev fallback (15 records)
  python scripts/run_embedding.py --dry-run       # count only

Local all-MiniLM-L6-v2 only. Groq is NOT used here.
Tip: pwede rin via API — POST /api/admin/reindex (diretso PSS → pgvector).
"""
import argparse
import json
import sys
import time
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = API_DIR.parent
sys.path.insert(0, str(API_DIR))

from services.embedding_service import generate_embeddings_batch  # noqa: E402
from services.pss_service import to_embedding_record  # noqa: E402
from services.vector_store import store_embeddings  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--input", default=str(REPO_ROOT / "data" / "extracted_services.json"))
parser.add_argument("--use-fixture", action="store_true")
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()

input_path = (
    API_DIR / "tests" / "fixtures" / "services_fixture.json"
    if args.use_fixture else Path(args.input)
)
services = json.loads(Path(input_path).read_text(encoding="utf-8"))
print(f"Loaded {len(services)} services from {input_path}")
if args.dry_run:
    sys.exit(0)

# Fixture records have no text_chunk yet — build with the canonical formatter.
if services and "text_chunk" not in services[0]:
    services = [to_embedding_record(dict(s)) for s in services]

texts = [s["text_chunk"] for s in services if s.get("text_chunk")]
start = time.time()
embeddings = generate_embeddings_batch(texts)
for i, svc in enumerate(services):
    svc["embedding"] = embeddings[i]
store_embeddings(services)
print(f"Done. Upserted {len(services)} records. Duration: {time.time() - start:.1f}s")
