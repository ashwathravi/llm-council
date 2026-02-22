"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
# COUNCIL_MODELS = [
#     "openai/gpt-5.2",
#     "google/gemini-3-pro-preview",
#     "anthropic/claude-sonnet-4.5",
#     "x-ai/grok-4",
# ]

# # Chairman model - synthesizes final response
# CHAIRMAN_MODEL = "google/gemini-3-pro-preview"

# Council members - list of OpenRouter model identifiers.
# Defaults favor fast, currently active models (override with COUNCIL_MODELS env if needed).
_DEFAULT_COUNCIL_MODELS = [
    "x-ai/grok-4.1-fast",
    "google/gemini-3-pro-preview",
    "openai/gpt-5.2",
]
_models_raw = os.getenv("COUNCIL_MODELS")
if _models_raw:
    COUNCIL_MODELS = [m.strip() for m in _models_raw.split(",") if m.strip()]
else:
    COUNCIL_MODELS = list(_DEFAULT_COUNCIL_MODELS)

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = os.getenv("CHAIRMAN_MODEL", "x-ai/grok-4.1-fast")

# Performance profile
MAX_MODELS_PER_REQUEST = max(1, _env_int("MAX_MODELS_PER_REQUEST", 10))
MODEL_TIMEOUT_SECONDS = max(5.0, _env_float("MODEL_TIMEOUT_SECONDS", 25.0))
STREAM_TIMEOUT_SECONDS = max(5.0, _env_float("STREAM_TIMEOUT_SECONDS", 45.0))
TITLE_TIMEOUT_SECONDS = max(3.0, _env_float("TITLE_TIMEOUT_SECONDS", 8.0))
FAST_LOCAL_TITLE = _env_bool("FAST_LOCAL_TITLE", True)
TITLE_MODEL = os.getenv("TITLE_MODEL", CHAIRMAN_MODEL)

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Data directory for extracted document storage
DOCUMENTS_DIR = "data/documents"

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# PDF upload limits
PDF_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
PDF_MAX_FILES_PER_CONVERSATION = 5

# Chunking + retrieval config
CHUNK_WORDS = 200
CHUNK_OVERLAP_WORDS = 40
RETRIEVAL_TOP_K = 5
RETRIEVAL_MAX_TOTAL_CHARS = 4000
RETRIEVAL_MAX_CHARS_PER_CHUNK = 1000

# Embedding model
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Origin Detection
if os.getenv("RENDER"):
    APP_ORIGIN = "render"
elif os.getenv("REPLIT_ID") or os.getenv("REPLIT_SLUG"):
    APP_ORIGIN = "replit"
else:
    APP_ORIGIN = "local"

# CORS Configuration
_CORS_ORIGINS_DEFAULT = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
_cors_origins_raw = os.getenv("CORS_ALLOWED_ORIGINS")
if _cors_origins_raw:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
else:
    CORS_ALLOWED_ORIGINS = _CORS_ORIGINS_DEFAULT
