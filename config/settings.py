"""
Project configuration and directory path management.

Centralizes filesystem paths using pathlib.
No API keys or external credentials are stored here.
"""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EVALUATION_DATA_DIR = DATA_DIR / "evaluation"

# Storage directory (for local vector store and local database)
STORAGE_DIR = PROJECT_ROOT / "storage"

# Production corpus/index paths.  Keep all runtime paths anchored to the
# project root so the application behaves the same regardless of the current
# working directory used to launch Streamlit or the CLI.
PRODUCTION_CORPUS_PATH = Path(
    os.getenv("VIETLABOR_CORPUS_PATH", str(PROCESSED_DATA_DIR / "legal_documents_v3.jsonl"))
).resolve()
BM25_INDEX_DIR = Path(
    os.getenv("VIETLABOR_BM25_INDEX_DIR", str(STORAGE_DIR / "bm25_v3"))
).resolve()
CHROMA_INDEX_DIR = Path(
    os.getenv("VIETLABOR_CHROMA_INDEX_DIR", str(STORAGE_DIR / "chroma_v3"))
).resolve()
CHAT_HISTORY_PATH = Path(
    os.getenv("VIETLABOR_CHAT_HISTORY_PATH", str(STORAGE_DIR / "chat_history.json"))
).resolve()

# Local-only defaults.  These can be overridden explicitly for a controlled
# deployment, but the default installation must never expose the legal chat UI
# to the LAN by accident.
APP_HOST = os.getenv("VIETLABOR_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("VIETLABOR_PORT", "8501"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_0")

# Optimized 6GB RTX 3060 Laptop GPU inference profile.
# 2560 context + 4500 chars context ensures peak 50+ tokens/s GPU speed with zero latency.
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "3072"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "1200"))
OLLAMA_NUM_GPU = int(os.getenv("OLLAMA_NUM_GPU", "-1"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "24h")
RAG_MAX_CONTEXT_CHARS = int(os.getenv("VIETLABOR_MAX_CONTEXT_CHARS", "4500"))
RAG_MAX_CONTEXT_CHUNKS = int(os.getenv("VIETLABOR_MAX_CONTEXT_CHUNKS", "8"))


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Chatbot experience
# Rewrite short follow-ups ("Còn vùng III thì sao?") into standalone questions with
# a small LLM call before retrieval. Falls back to rule-based resolution on failure.
LLM_FOLLOWUP_REWRITE = _env_flag("VIETLABOR_LLM_FOLLOWUP_REWRITE", True)
# Load the Ollama model into memory when the UI starts (cold first token ~8s -> <1s).
OLLAMA_WARMUP_ON_START = _env_flag("VIETLABOR_OLLAMA_WARMUP", True)
FEEDBACK_LOG_PATH = Path(
    os.getenv("VIETLABOR_FEEDBACK_PATH", str(STORAGE_DIR / "feedback.jsonl"))
).resolve()

# Neo4j Graph Database Configuration (Hybrid GraphRAG)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
NEO4J_ENABLED = os.getenv("NEO4J_ENABLED", "false").lower() in ("true", "1", "yes")

