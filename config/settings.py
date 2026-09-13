"""
Project configuration and directory path management.

Centralizes filesystem paths using pathlib.
No API keys or external credentials are stored here.
"""

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
