"""
Database queries for FitnessDB (SQL Server) with fallback handling.
"""

import logging
from typing import Any, List, Optional, Sequence
from sqlalchemy import text

from gym_ai.database.connection import get_session, is_database_available

logger = logging.getLogger("gym_ai.database.queries")


def get_exercises() -> List[Sequence[Any]]:
    if not is_database_available():
        return []
    try:
        with get_session() as db:
            result = db.execute(
                text("""
                    SELECT
                        ExerciseID,
                        ExerciseName,
                        Instructions
                    FROM Exercises
                """)
            )
            return result.fetchall()
    except Exception as e:
        logger.error(f"Error querying exercises: {e}")
        return []


def get_exercise_by_id(exercise_id: int) -> Optional[Sequence[Any]]:
    if not is_database_available():
        return None
    try:
        with get_session() as db:
            result = db.execute(
                text("""
                    SELECT
                        ExerciseID,
                        ExerciseName,
                        Instructions
                    FROM Exercises
                    WHERE ExerciseID = :exercise_id
                """),
                {"exercise_id": exercise_id}
            )
            return result.fetchone()
    except Exception as e:
        logger.error(f"Error querying exercise {exercise_id}: {e}")
        return None


def get_foods() -> List[Sequence[Any]]:
    if not is_database_available():
        return []
    try:
        with get_session() as db:
            result = db.execute(
                text("""
                    SELECT
                        fdc_id,
                        description
                    FROM NutritionFacts
                """)
            )
            return result.fetchall()
    except Exception as e:
        logger.error(f"Error querying foods: {e}")
        return []


def get_food_by_id(fdc_id: int) -> Optional[Sequence[Any]]:
    if not is_database_available():
        return None
    try:
        with get_session() as db:
            result = db.execute(
                text("""
                    SELECT
                        fdc_id,
                        description,
                        Calories_kcal,
                        Protein_g,
                        Carbs_g,
                        Fat_g
                    FROM NutritionFacts
                    WHERE fdc_id = :fdc_id
                """),
                {"fdc_id": fdc_id}
            )
            return result.fetchone()
    except Exception as e:
        logger.error(f"Error querying food {fdc_id}: {e}")
        return None


def get_muscles() -> List[Sequence[Any]]:
    if not is_database_available():
        return []
    try:
        with get_session() as db:
            result = db.execute(
                text("""
                    SELECT
                        MuscleID,
                        MuscleName
                    FROM Muscles
                """)
            )
            return result.fetchall()
    except Exception as e:
        logger.error(f"Error querying muscles: {e}")
        return []


def get_muscle_by_id(muscle_id: int) -> Optional[Sequence[Any]]:
    if not is_database_available():
        return None
    try:
        with get_session() as db:
            result = db.execute(
                text("""
                    SELECT
                        MuscleID,
                        MuscleName
                    FROM Muscles
                    WHERE MuscleID = :muscle_id
                """),
                {"muscle_id": muscle_id}
            )
            return result.fetchone()
    except Exception as e:
        logger.error(f"Error querying muscle {muscle_id}: {e}")
        return None


def get_equipments() -> List[Sequence[Any]]:
    if not is_database_available():
        return []
    try:
        with get_session() as db:
            result = db.execute(
                text("""
                    SELECT
                        EquipmentID,
                        EquipmentName
                    FROM Equipments
                """)
            )
            return result.fetchall()
    except Exception as e:
        logger.error(f"Error querying equipments: {e}")
        return []


def get_equipment_by_id(equipment_id: int) -> Optional[Sequence[Any]]:
    if not is_database_available():
        return None
    try:
        with get_session() as db:
            result = db.execute(
                text("""
                    SELECT
                        EquipmentID,
                        EquipmentName
                    FROM Equipments
                    WHERE EquipmentID = :equipment_id
                """),
                {"equipment_id": equipment_id}
            )
            return result.fetchone()
    except Exception as e:
        logger.error(f"Error querying equipment {equipment_id}: {e}")
        return None


def get_exercise_muscles(exercise_id: int) -> List[Sequence[Any]]:
    if not is_database_available():
        return []
    try:
        with get_session() as db:
            result = db.execute(
                text("""
                    SELECT
                        m.MuscleID,
                        m.MuscleName
                    FROM Muscles AS m
                    INNER JOIN Exercise_Muscle_Mapping AS emm
                        ON m.MuscleID = emm.MuscleID
                    WHERE emm.ExerciseID = :exercise_id
                """),
                {"exercise_id": exercise_id}
            )
            return result.fetchall()
    except Exception as e:
        logger.error(f"Error querying exercise muscles for {exercise_id}: {e}")
        return []
