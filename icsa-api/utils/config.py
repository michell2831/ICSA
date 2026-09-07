"""Central configuration — every value comes from .env (AI-GROQ rule: nothing hardcoded)."""
import os
from dotenv import load_dotenv

load_dotenv()  # loads .env from the working directory (repo root or icsa-api/)


class ConfigError(Exception):
    """Raised when a required environment variable is missing."""


def _bool(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes")


# --- Mock flags (Week 1: all true. Week 2 AI-10: flip to false) ---
USE_MOCK_LLM = _bool("USE_MOCK_LLM")
USE_MOCK_VECTOR_STORE = _bool("USE_MOCK_VECTOR_STORE")
USE_MOCK_LOGGING = _bool("USE_MOCK_LOGGING")
USE_MOCK_ANALYTICS = _bool("USE_MOCK_ANALYTICS")

# --- Groq (inference API). Llama = model family hosted on Groq. ---
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "400"))
GROQ_TIMEOUT_SECONDS = int(os.getenv("GROQ_TIMEOUT_SECONDS", "10"))

# --- Embeddings: local sentence-transformers model (NOT Groq) ---
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
EMBEDDING_DIM = 384

# --- Databases ---
PGVECTOR_URL = os.getenv(
    "PGVECTOR_URL", "postgresql://postgres:postgres@localhost:5433/postgres"
)
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
PSS_DB_URL = os.getenv("PSS_DB_URL", "")


def get_groq_api_key() -> str:
    """Fetch the Groq API key. Raises ConfigError if missing (AI-GROQ AC #7).

    Called lazily so that mock mode (USE_MOCK_LLM=true) never requires a key.
    """
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise ConfigError(
            "GROQ_API_KEY not set. Add it to your local .env "
            "(get a key at console.groq.com). Never commit the real key."
        )
    return key