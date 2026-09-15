"""
Personalized workout and nutrition plan generator.
Reads athlete profile, recent fatigue, and workout handoffs to synthesize
tomorrow's custom routine and nutrition recommendations.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from common.paths import DATA_ROOT
from gym_ai.llm import generate_answer

logger = logging.getLogger("gym_ai.planner")

PLAN_GENERATION_PROMPT = """
You are the Master AI Strength & Conditioning Coach and Sports Nutritionist for FitPath.

Your mission is to read the athlete's profile and latest workout handoff data, and design:
1. Tomorrow's personalized workout plan (using exercises from the FitPath exercise catalog).
2. Targeted post-workout recovery nutrition guidance.
3. Coach notes acknowledging recent fatigue and form cues.

AVAILABLE EXERCISE CATALOG IDs:
- squat (Squat)
- pushup (Push-up)
- plank (Plank)
- lunge (Lunge)
- glute_bridge (Glute Bridge)
- wall_sit (Wall Sit)
- bird_dog (Bird Dog)
- dead_bug (Dead Bug)
- biceps_curl (Biceps Curl)
- box_squat (Box Squat - regression for knee issues)
- knee_pushup (Knee Push-up - regression for shoulder/strength)

ATHLETE PROFILE:
{profile_json}

LATEST WORKOUT HANDOFF & METRICS:
{handoff_json}

RULES:
1. Respect injuries strictly:
   - If 'knees' in injuries: Avoid heavy lunges; prefer 'box_squat', 'glute_bridge', 'wall_sit'.
   - If 'shoulders' in injuries: Avoid standard push-ups; prefer 'knee_pushup', 'bird_dog', 'dead_bug'.
   - If 'back' in injuries: Emphasize core stability ('bird_dog', 'dead_bug', 'plank').
2. Time Budget: Design the workout to fit within the athlete's time budget (typically 2-4 exercises, 2-3 sets each).
3. Return STRICTLY JSON matching this schema:
{{
  "generated_at": "ISO string",
  "coach_notes": "Encouraging, motivating coaching feedback reflecting their recent session and form",
  "plan": [
    {{
      "exercise_id": "exercise_id from catalog",
      "exercise_name": "Display Name",
      "sets": 2,
      "reps": 10,
      "coaching_focus": "Specific form cue to watch out for"
    }}
  ],
  "nutrition_recovery": {{
    "protein_target_g": 30,
    "hydration_advice": "Hydration tip",
    "recommended_meal": "High-protein recovery meal idea"
  }}
}}
"""


def generate_personalized_plan(
    profile: Optional[Dict[str, Any]] = None,
    handoff: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate tomorrow's workout plan and diet advice using LLM reasoning,
    saving the output to data/workout_plan.json.
    """
    # Load profile if not supplied
    if not profile:
        try:
            from common.profile import load_profile
            profile = load_profile()
        except Exception:
            profile = {}

    profile = profile or {
        "name": "Athlete",
        "goal": "strength",
        "experience": "intermediate",
        "injuries": [],
        "equipment": "bodyweight",
        "time_budget_min": 25,
    }

    # Load handoff if not supplied
    if not handoff:
        handoff_path = os.path.join(DATA_ROOT, "data", "coach_handoff.json")
        if os.path.exists(handoff_path):
            try:
                with open(handoff_path, "r", encoding="utf-8") as f:
                    handoff = json.load(f)
            except Exception:
                handoff = {}

    handoff = handoff or {"notes": "No previous workout recorded."}

    prompt = PLAN_GENERATION_PROMPT.format(
        profile_json=json.dumps(profile, indent=2),
        handoff_json=json.dumps(handoff, indent=2),
    )

    try:
        response_text = generate_answer(prompt, json_mode=True, stream=False)
        plan_data = json.loads(response_text)
    except Exception as e:
        logger.error(f"Failed to generate structured plan via LLM: {e}")
        # Robust fallback plan honoring injuries
        injuries = profile.get("injuries", [])
        if "knees" in injuries:
            plan = [
                {"exercise_id": "glute_bridge", "exercise_name": "Glute Bridge", "sets": 3, "reps": 12, "coaching_focus": "Drive through heels"},
                {"exercise_id": "dead_bug", "exercise_name": "Dead Bug", "sets": 2, "reps": 10, "coaching_focus": "Keep lower back flat"},
            ]
        else:
            plan = [
                {"exercise_id": "squat", "exercise_name": "Squat", "sets": 3, "reps": 10, "coaching_focus": "Keep chest up"},
                {"exercise_id": "pushup", "exercise_name": "Push-up", "sets": 2, "reps": 8, "coaching_focus": "Straight body line"},
            ]

        plan_data = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "coach_notes": f"Personalized recovery session tailored for {profile.get('name', 'Athlete')}.",
            "plan": plan,
            "nutrition_recovery": {
                "protein_target_g": 30,
                "hydration_advice": "Drink at least 500ml of water with electrolytes.",
                "recommended_meal": "Grilled chicken with sweet potato and greens."
            }
        }

    # Persist to data/workout_plan.json
    try:
        plan_dir = os.path.join(DATA_ROOT, "data")
        os.makedirs(plan_dir, exist_ok=True)
        plan_path = os.path.join(plan_dir, "workout_plan.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, indent=2)
        logger.info(f"Saved generated workout plan to {plan_path}")
    except Exception as e:
        logger.error(f"Failed to write workout plan file: {e}")

    return plan_data
