"""
Project configuration and directory path management.

Centralizes filesystem paths using pathlib.
No API keys or external credentials are stored here.
"""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _project_path(name: str, default: Path) -> Path:
    """Resolve relative overrides against the project, independent of launch cwd."""
    value = os.getenv(name, "").strip()
    path = Path(value).expanduser() if value else default
    return (path if path.is_absolute() else PROJECT_ROOT / path).resolve()

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
PRODUCTION_CORPUS_PATH = _project_path("VIETLABOR_CORPUS_PATH", PROCESSED_DATA_DIR / "legal_documents_v3.jsonl")
BM25_INDEX_DIR = _project_path("VIETLABOR_BM25_INDEX_DIR", STORAGE_DIR / "bm25_v3")
CHROMA_INDEX_DIR = _project_path("VIETLABOR_CHROMA_INDEX_DIR", STORAGE_DIR / "chroma_v3")
CHAT_HISTORY_PATH = _project_path("VIETLABOR_CHAT_HISTORY_PATH", STORAGE_DIR / "chat_history.json")

# Local-only defaults.  These can be overridden explicitly for a controlled
# deployment, but the default installation must never expose the legal chat UI
# to the LAN by accident.
APP_HOST = os.getenv("VIETLABOR_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("VIETLABOR_PORT", "8501"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_0")

# Leave room for the legal evidence, instructions and a complete explanation
# plus structured findings. These limits remain configurable for local hardware.
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "1800"))
OLLAMA_NUM_GPU = int(os.getenv("OLLAMA_NUM_GPU", "-1"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "24h")
RAG_MAX_CONTEXT_CHARS = int(os.getenv("VIETLABOR_MAX_CONTEXT_CHARS", "5500"))
RAG_MAX_CONTEXT_CHUNKS = int(os.getenv("VIETLABOR_MAX_CONTEXT_CHUNKS", "8"))


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Constrain field types so a malformed flag cannot discard a valid explanation.
OLLAMA_USE_STRICT_SCHEMA = _env_flag("VIETLABOR_STRICT_SCHEMA", True)


# When true, LLM prose may only cite articles present in locked evidence (not the wider context pool).
STRICT_CITATION_OWNERSHIP = _env_flag("VIETLABOR_STRICT_CITATIONS", True)
# Hard-lock evidence from question-pattern anchors (disable to rely on retrieval+selector only).
ANCHOR_HARD_LOCK_ENABLED = _env_flag("VIETLABOR_ANCHOR_HARD_LOCK", True)
# When user question ≈ official Can Tho scenario text, return PBGDPL answer + corpus citations (no LLM).
CAN_THO_OFFICIAL_GROUNDING = _env_flag("VIETLABOR_CAN_THO_OFFICIAL_GROUNDING", False)

# Chatbot experience
# Rewrite short follow-ups ("Còn vùng III thì sao?") into standalone questions with
# a small LLM call before retrieval. Falls back to rule-based resolution on failure.
LLM_FOLLOWUP_REWRITE = _env_flag("VIETLABOR_LLM_FOLLOWUP_REWRITE", True)
# Load the Ollama model into memory when the UI starts (cold first token ~8s -> <1s).
OLLAMA_WARMUP_ON_START = _env_flag("VIETLABOR_OLLAMA_WARMUP", True)
FEEDBACK_LOG_PATH = _project_path("VIETLABOR_FEEDBACK_PATH", STORAGE_DIR / "feedback.jsonl")

# Neo4j Graph Database Configuration (Hybrid GraphRAG)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
NEO4J_ENABLED = os.getenv("NEO4J_ENABLED", "false").lower() in ("true", "1", "yes")

