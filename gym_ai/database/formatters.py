"""
Data formatters for converting database rows into clean, structured strings
for LLM prompt context, with deterministic gram-based nutrition scaling.
"""

from typing import Any, List, Optional, Sequence


def format_food(food: Optional[Sequence[Any]], grams: Optional[float] = None) -> str:
    """
    Format food nutrition data with optional deterministic gram-based scaling.
    Baseline database values are stored per 100g.
    """
    if not food:
        return "No matching food found in database."

    description = food[1]
    base_calories = float(food[2] or 0.0)
    base_protein = float(food[3] or 0.0)
    base_carbs = float(food[4] or 0.0)
    base_fat = float(food[5] or 0.0)

    if grams and grams > 0:
        scale_factor = grams / 100.0
        scaled_cals = round(base_calories * scale_factor, 1)
        scaled_protein = round(base_protein * scale_factor, 2)
        scaled_carbs = round(base_carbs * scale_factor, 2)
        scaled_fat = round(base_fat * scale_factor, 2)

        return f"""
Food: {description} (Portion: {grams:.0f}g - Deterministically scaled from 100g baseline)
Calories: {scaled_cals} kcal
Protein: {scaled_protein} g
Carbs: {scaled_carbs} g
Fat: {scaled_fat} g
Baseline per 100g: {base_calories} kcal | {base_protein}g Protein | {base_carbs}g Carbs | {base_fat}g Fat
""".strip()

    return f"""
Food: {description} (Standard 100g portion)
Calories: {base_calories} kcal
Protein: {base_protein} g
Carbs: {base_carbs} g
Fat: {base_fat} g
""".strip()


def format_exercise(exercise: Optional[Sequence[Any]]) -> str:
    if not exercise:
        return "No matching exercise found in database."
    return f"""
Exercise ID: {exercise[0]}
Exercise Name: {exercise[1]}
Instructions: {exercise[2]}
""".strip()


def format_muscles(muscles: Optional[Sequence[Sequence[Any]]]) -> str:
    if not muscles:
        return "None listed in database."
    muscle_names = [
        muscle[1]
        for muscle in muscles
        if muscle and len(muscle) > 1 and muscle[1]
    ]
    return ", ".join(muscle_names) if muscle_names else "None listed in database."


def format_muscle(muscle: Optional[Sequence[Any]]) -> str:
    if not muscle:
        return "No matching muscle found in database."
    return f"Muscle: {muscle[1]}"


def format_equipment(equipment: Optional[Sequence[Any]]) -> str:
    if not equipment:
        return "No matching equipment found in database."
    return f"Equipment: {equipment[1]}"
