"""
Semantic entity resolution across exercises, foods, muscles, and equipment
using Chroma vector embeddings and SQL database lookups.
"""

import logging
from typing import Any, Optional, Sequence, Tuple
from langchain_chroma import Chroma

from gym_ai.config import CHROMA_ENTITIES_DIR
from gym_ai.database.queries import (
    get_equipment_by_id,
    get_exercise_by_id,
    get_food_by_id,
    get_muscle_by_id,
)
from gym_ai.rag.embeddings import get_embeddings

logger = logging.getLogger("gym_ai.rag.entity_search")

_stores = {}


def _get_store(collection_name: str) -> Chroma:
    if collection_name not in _stores:
        _stores[collection_name] = Chroma(
            collection_name=collection_name,
            persist_directory=CHROMA_ENTITIES_DIR,
            embedding_function=get_embeddings(),
        )
    return _stores[collection_name]


def search_exercise(query: str) -> Tuple[Optional[int], Optional[Sequence[Any]]]:
    try:
        store = _get_store("exercise_entities")
        results = store.similarity_search_with_score(query, k=1)
        if not results:
            return None, None
        document, score = results[0]
        exercise_id = int(document.metadata["entity_id"])
        exercise = get_exercise_by_id(exercise_id)
        return exercise_id, exercise
    except Exception as e:
        logger.warning(f"Failed to search exercise for '{query}': {e}")
        return None, None


def search_food(query: str) -> Optional[Sequence[Any]]:
    try:
        store = _get_store("food_entities")
        results = store.similarity_search_with_score(query, k=1)
        if not results:
            return None
        document, score = results[0]
        fdc_id = int(document.metadata["entity_id"])
        return get_food_by_id(fdc_id)
    except Exception as e:
        logger.warning(f"Failed to search food for '{query}': {e}")
        return None


def search_muscle(query: str) -> Optional[Sequence[Any]]:
    try:
        store = _get_store("muscle_entities")
        results = store.similarity_search_with_score(query, k=1)
        if not results:
            return None
        document, score = results[0]
        muscle_id = int(document.metadata["entity_id"])
        return get_muscle_by_id(muscle_id)
    except Exception as e:
        logger.warning(f"Failed to search muscle for '{query}': {e}")
        return None


def search_equipment(query: str) -> Optional[Sequence[Any]]:
    try:
        store = _get_store("equipment_entities")
        results = store.similarity_search_with_score(query, k=1)
        if not results:
            return None
        document, score = results[0]
        equipment_id = int(document.metadata["entity_id"])
        return get_equipment_by_id(equipment_id)
    except Exception as e:
        logger.warning(f"Failed to search equipment for '{query}': {e}")
        return None
