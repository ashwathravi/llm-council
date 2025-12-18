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
    "moonshotai/kimi-k2:free",
    "deepseek/deepseek-r1-0528:free"
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "mistralai/devstral-2512:free"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
