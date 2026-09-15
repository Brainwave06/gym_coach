"""
Embedding model initialization for Gym AI using Alibaba DashScope Qwen embeddings (text-embedding-v3).
Uses the same API key and OpenAI-compatible client.
"""

import logging
from typing import Any, List, Optional
from langchain_core.embeddings import Embeddings
from openai import OpenAI

from gym_ai.config import EMBEDDING_MODEL_NAME, LLM_API_KEY, LLM_BASE_URL

logger = logging.getLogger("gym_ai.rag.embeddings")


class QwenDashScopeEmbeddings(Embeddings):
    """
    Qwen / DashScope Embedding model (text-embedding-v3) via OpenAI-compatible API.
    """
    def __init__(
        self,
        model: str = EMBEDDING_MODEL_NAME,
        api_key: str = LLM_API_KEY,
        base_url: str = LLM_BASE_URL,
    ):
        self.model = model
        effective_key = (api_key or "").strip() or "sk-placeholder-key-not-set"
        self.client = OpenAI(api_key=effective_key, base_url=base_url)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = []
        batch_size = 8
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            cleaned = [t.replace("\n", " ").strip() or " " for t in batch]
            res = self.client.embeddings.create(model=self.model, input=cleaned)
            embeddings.extend([item.embedding for item in res.data])
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        cleaned = text.replace("\n", " ").strip() or " "
        res = self.client.embeddings.create(model=self.model, input=cleaned)
        return res.data[0].embedding


_embeddings_model: Optional[Embeddings] = None


def get_embeddings() -> Embeddings:
    """Return the cached QwenDashScopeEmbeddings instance."""
    global _embeddings_model
    if _embeddings_model is None:
        logger.info(f"Initializing Qwen DashScope embeddings: {EMBEDDING_MODEL_NAME}...")
        _embeddings_model = QwenDashScopeEmbeddings()
    return _embeddings_model


class _EmbeddingsProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_embeddings(), name)


embeddings_model = _EmbeddingsProxy()
