FROM python:3.11-slim
WORKDIR /app
# Install CPU-only PyTorch first (shrinks image from 5 GB of Nvidia CUDA wheels down to ~180 MB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install cron daemon — used by the icsa-reindex-cron sidecar service
# (docker-compose.yml) to schedule nightly re-indexing (DE-07).
# Adds ~2 MB to the image. The main icsa-api container ignores it.
RUN apt-get update && apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/*

# Pre-download the embedding model at BUILD time, not runtime. Without this,
# every container recreation (docker-compose down / --force-recreate /
# rebuild) wipes the container's writable layer, forcing a fresh ~75s+
# download from huggingface.co on the very next real chat request — which
# blows straight through the 25s pipeline timeout and shows the user the
# generic "took too long" message even though nothing is actually broken.
# Baking it into the image means it downloads exactly once, at build time,
# and every container started from this image already has it on disk.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]