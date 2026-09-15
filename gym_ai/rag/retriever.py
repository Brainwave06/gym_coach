"""
Vector store retriever for Gym AI knowledge documents.
"""

import logging
from typing import List, Tuple
from langchain_chroma import Chroma
from langchain_core.documents import Document

from gym_ai.config import CHROMA_PERSIST_DIR
from gym_ai.rag.embeddings import get_embeddings

logger = logging.getLogger("gym_ai.rag.retriever")

_vector_store = None


def get_vector_store() -> Chroma:
    global _vector_store
    if _vector_store is None:
        _vector_store = Chroma(
            collection_name="gym_documents",
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=get_embeddings(),
        )
    return _vector_store


def retrieve_documents(query: str, k: int = 3) -> List[Tuple[Document, float]]:
    """Retrieve top-k relevant knowledge documents along with similarity scores."""
    try:
        store = get_vector_store()
        return store.similarity_search_with_score(query, k=k)
    except Exception as e:
        logger.error(f"Error retrieving documents for '{query}': {e}")
        return []
