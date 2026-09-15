"""
RAG (Retrieval-Augmented Generation) package for Gym AI.
"""

from gym_ai.rag.embeddings import get_embeddings
from gym_ai.rag.retriever import retrieve_documents
from gym_ai.rag.context_builder import build_context

__all__ = ["get_embeddings", "retrieve_documents", "build_context"]
