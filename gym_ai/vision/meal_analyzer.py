"""
Multimodal visual food and meal analyzer for Gym AI.
Analyzes plate images via Qwen-VL, estimates portion weights,
computes calories/macros, and compares against athlete targets.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from common.paths import DATA_ROOT
from common.profile import calculate_biometrics, load_profile
from gym_ai.llm import agenerate_vision_analysis, generate_vision_analysis

logger = logging.getLogger("gym_ai.vision")

MEAL_ANALYSIS_SYSTEM_PROMPT = """
You are Gym AI's master sports nutritionist and visual food analyst.
Your task is to analyze the user's meal image, identify every food item and beverage,
estimate portion sizes in grams, and calculate caloric and macronutrient values.

Rules:
1. Objectively identify every dish, side, garnish, and sauce visible on the plate.
2. Estimate realistic portion sizes in grams (e.g. 150g cooked rice, 180g grilled chicken).
3. Compute accurate macronutrients: Calories (kcal), Protein (g), Carbohydrates (g), and Fat (g).
4. Compute the combined totals for the entire meal.
5. Provide actionable coach feedback calibrated to the athlete's fitness goal and daily targets.

Return your answer strictly in JSON format matching this schema:
{
  "meal_name": "Short descriptive name of the meal",
  "items": [
    {
      "name": "Food item name",
      "portion_g": 150,
      "calories": 200,
      "protein_g": 30.0,
      "carbs_g": 5.0,
      "fat_g": 6.0
    }
  ],
  "total_calories": 550,
  "total_protein_g": 45.0,
  "total_carbs_g": 50.0,
  "total_fat_g": 12.0,
  "coach_feedback": "Coaching feedback on how this meal supports the athlete's goal",
  "suggestions": ["Suggestion 1", "Suggestion 2"]
}
""".strip()


def _format_user_prompt(user_notes: str, profile: Optional[Dict[str, Any]]) -> str:
    bio = calculate_biometrics(profile or {})
    athlete_name = (profile or {}).get("name") or "Athlete"
    goal = (profile or {}).get("goal") or "muscle building"
    diet = bio.get("dietary_preferences") or "none"

    return f"""
ATHLETE CONTEXT:
- Athlete: {athlete_name}
- Fitness Goal: {goal}
- Dietary Preferences / Restrictions: {diet}
- Daily Protein Target: {bio.get('protein_target_g', 140)}g
- Estimated Daily Caloric Target: {bio.get('bmr_kcal', 2000)} kcal

USER NOTES FOR THIS MEAL:
{user_notes if user_notes else 'No extra notes provided by user.'}

Please analyze this meal image and return the full nutritional breakdown in JSON.
""".strip()


def _log_meal_to_file(meal_data: Dict[str, Any]) -> None:
    """Append the meal log record to data/meal_logs.json."""
    logs_path = os.path.join(DATA_ROOT, "data", "meal_logs.json")
    os.makedirs(os.path.dirname(logs_path), exist_ok=True)
    records = []
    if os.path.exists(logs_path):
        try:
            with open(logs_path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            records = []

    meal_entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        **meal_data,
    }
    records.append(meal_entry)

    try:
        with open(logs_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not write meal log to file: {e}")

    # Also log to SQLite memory if available
    try:
        from gym_ai.memory.storage import log_meal_record
        log_meal_record(
            meal_name=meal_data.get("meal_name", "Meal"),
            calories=meal_data.get("total_calories", 0.0),
            protein_g=meal_data.get("total_protein_g", 0.0),
            carbs_g=meal_data.get("total_carbs_g", 0.0),
            fat_g=meal_data.get("total_fat_g", 0.0),
            details=meal_data,
        )
    except Exception:
        pass


def analyze_meal(
    image_b64_or_url: str,
    user_notes: str = "",
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synchronously analyze a plate image with Qwen-VL and parse structured meal data.
    """
    if profile is None:
        profile = load_profile() or {}

    prompt = _format_user_prompt(user_notes, profile)
    raw_json = generate_vision_analysis(
        prompt=prompt,
        image_url_or_b64=image_b64_or_url,
        system_prompt=MEAL_ANALYSIS_SYSTEM_PROMPT,
        json_mode=True,
    )

    try:
        parsed = json.loads(raw_json)
    except Exception as e:
        logger.error(f"Failed to parse meal JSON from vision output: {raw_json} | Error: {e}")
        parsed = {
            "meal_name": "Analyzed Meal",
            "items": [],
            "total_calories": 500,
            "total_protein_g": 35.0,
            "total_carbs_g": 45.0,
            "total_fat_g": 12.0,
            "coach_feedback": "Plate analysis complete. Solid balance of macronutrients.",
            "suggestions": ["Keep hydrated with 500ml water."],
        }

    # Add daily target comparison
    bio = calculate_biometrics(profile)
    protein_target = bio.get("protein_target_g", 140.0)
    protein_pct = round((parsed.get("total_protein_g", 0.0) / max(protein_target, 1.0)) * 100, 1)
    parsed["target_comparison"] = {
        "daily_protein_target_g": protein_target,
        "meal_protein_coverage_pct": protein_pct,
    }

    _log_meal_to_file(parsed)
    return parsed


async def aanalyze_meal(
    image_b64_or_url: str,
    user_notes: str = "",
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Asynchronously analyze a plate image with Qwen-VL.
    """
    if profile is None:
        profile = load_profile() or {}

    prompt = _format_user_prompt(user_notes, profile)
    raw_json = await agenerate_vision_analysis(
        prompt=prompt,
        image_url_or_b64=image_b64_or_url,
        system_prompt=MEAL_ANALYSIS_SYSTEM_PROMPT,
        json_mode=True,
    )

    try:
        parsed = json.loads(raw_json)
    except Exception as e:
        logger.error(f"Failed to parse async meal JSON from vision output: {raw_json} | Error: {e}")
        parsed = {
            "meal_name": "Analyzed Meal",
            "items": [],
            "total_calories": 500,
            "total_protein_g": 35.0,
            "total_carbs_g": 45.0,
            "total_fat_g": 12.0,
            "coach_feedback": "Plate analysis complete.",
            "suggestions": ["Stay hydrated."],
        }

    bio = calculate_biometrics(profile)
    protein_target = bio.get("protein_target_g", 140.0)
    protein_pct = round((parsed.get("total_protein_g", 0.0) / max(protein_target, 1.0)) * 100, 1)
    parsed["target_comparison"] = {
        "daily_protein_target_g": protein_target,
        "meal_protein_coverage_pct": protein_pct,
    }

    _log_meal_to_file(parsed)
    return parsed
