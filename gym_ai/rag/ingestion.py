"""
Ingestion script for Gym AI knowledge documents using Qwen text-embedding-v3.
"""

import logging
import os
from typing import List
from langchain_chroma import Chroma
from langchain_core.documents import Document

from gym_ai.config import CHROMA_PERSIST_DIR, DOCUMENTS_DIR
from gym_ai.rag.embeddings import get_embeddings

logger = logging.getLogger("gym_ai.rag.ingestion")


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 80) -> List[str]:
    """Split text into overlapping character chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def ingest_documents() -> int:
    """Read all markdown/text documents in data/documents and build the Chroma vector store."""
    if not os.path.exists(DOCUMENTS_DIR):
        raise FileNotFoundError(f"Documents directory not found at: {DOCUMENTS_DIR}")

    docs: List[Document] = []
    for root, _, files in os.walk(DOCUMENTS_DIR):
        for f in sorted(files):
            if f.endswith(".txt") or f.endswith(".md"):
                file_path = os.path.join(root, f)
                rel_path = os.path.relpath(file_path, DOCUMENTS_DIR).replace("\\", "/")
                with open(file_path, "r", encoding="utf-8") as handle:
                    content = handle.read()

                chunks = chunk_text(content)
                for idx, chunk in enumerate(chunks):
                    docs.append(
                        Document(
                            page_content=chunk,
                            metadata={"source": rel_path, "chunk_id": idx}
                        )
                    )

    if not docs:
        logger.warning("No documents found to ingest.")
        return 0

    embeddings = get_embeddings()

    # Create / overwrite vector store
    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name="gym_documents",
        persist_directory=CHROMA_PERSIST_DIR,
    )
    logger.info(f"Successfully ingested {len(docs)} document chunks into {CHROMA_PERSIST_DIR}.")
    return len(docs)


if __name__ == "__main__":
    count = ingest_documents()
    print(f"Ingestion complete: {count} chunks indexed with Qwen text-embedding-v3.")
