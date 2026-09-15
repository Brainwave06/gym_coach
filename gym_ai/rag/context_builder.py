"""
Context builder for RAG query answers.
Filters retrieved documents against similarity score thresholds.
"""

from typing import List, Tuple
from langchain_core.documents import Document

from gym_ai.config import SCORE_THRESHOLD
from gym_ai.rag.retriever import retrieve_documents


def build_context(query: str, threshold: float = SCORE_THRESHOLD) -> str:
    """
    Retrieve documents and build a formatted context string,
    filtering out results with distance scores above threshold.
    """
    try:
        results: List[Tuple[Document, float]] = retrieve_documents(query)
    except Exception:
        return "[Unable to retrieve documents from knowledge base at this time.]"

    filtered_results = [
        (doc, score)
        for doc, score in results
        if score <= threshold
    ]

    if not filtered_results:
        return "[No relevant documents found in the gym knowledge base for this query.]"

    context_blocks = []
    for doc, score in filtered_results:
        source = doc.metadata.get("source", "fitness_docs")
        context_blocks.append(f"--- Document ({source}) ---\n{doc.page_content}")

    return "\n\n".join(context_blocks).strip() or "[No relevant documents found in the gym knowledge base for this query.]"
