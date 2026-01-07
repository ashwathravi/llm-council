"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

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

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "xiaomi/mimo-v2-flash:free",
    "mistralai/devstral-2512:free",
    "nex-agi/deepseek-v3.1-nex-n1:free",
    "anthropic/claude-opus-4.5",
    "x-ai/grok-4.1-fast",
    "openai/gpt-5.2",
    "google/gemini-3-pro-preview"
 #   "google/gemini-3-flash-preview"
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "google/gemini-3-pro-preview"
#CHAIRMAN_MODEL = "google/gemini-3-flash-preview"

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
