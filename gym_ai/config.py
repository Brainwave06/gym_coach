"""
Configuration module for Gym AI.
Centralizes paths, credentials, and model configurations with environment variable fallbacks.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
GYM_AI_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = GYM_AI_DIR.parent

# Load .env from project root or current working directory
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Database Configuration (MSSQL FitnessDB)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "")
DB_NAME = os.getenv("DB_NAME", "FitnessDB")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("MSSQL_SA_PASSWORD")
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "3"))

# LLM Configuration (Alibaba DashScope / OpenAI-compatible Qwen)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-max")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60.0"))

# RAG & Vector Store Paths (resolved to absolute paths for resilience)
CHROMA_PERSIST_DIR = str(os.getenv("CHROMA_PERSIST_DIR") or (GYM_AI_DIR / "chroma_docs"))
CHROMA_ENTITIES_DIR = str(os.getenv("CHROMA_ENTITIES_DIR") or (GYM_AI_DIR / "chroma_entities"))
DOCUMENTS_DIR = str(GYM_AI_DIR / "data" / "documents")

# Embedding Model (Qwen / DashScope text-embedding-v3)
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-v3")

# Chat & Memory Configuration
MAX_CHAT_HISTORY = int(os.getenv("MAX_CHAT_HISTORY", "20"))
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.80"))
