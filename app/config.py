# Backend config
"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
REPORTS_DIR = DATA_DIR / "reports"
FALLBACK_DIR = DATA_DIR / "fallback"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# Create data directories if they don't exist
for d in [CACHE_DIR, REPORTS_DIR, FALLBACK_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- vLLM / Model ---
VLLM_BASE_URL: str = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1/")
MODEL_NAME: str = os.getenv("MODEL_NAME", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
LLM_ENABLE_THINKING: bool = os.getenv("LLM_ENABLE_THINKING", "false").lower() == "true"

# --- Tavily ---
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# --- Search ---
MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "10"))

# --- Server ---
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8080"))
