"""
Proactive Post-Workout Debrief synthesizer for Gym AI.
Connects computer-vision workout results directly to conversational coaching.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from common.paths import DATA_ROOT
from common.profile import calculate_biometrics, load_profile
from gym_ai.llm import generate_answer

logger = logging.getLogger("gym_ai.debrief")

DEBRIEF_SYSTEM_PROMPT = """
You are Gym AI, a world-class, encouraging, and science-informed gym coach and sports nutritionist.
You are delivering an immediate, proactive post-workout debriefing to your athlete based on their freshly completed computer-vision workout session.

Coaching Directives:
1. Warm, High-Energy Greeting: Acknowledge their hard work and celebrate their effort immediately.
2. Objective Performance Review: Reference exact numbers from the workout (exercise name, total reps, good reps count, form quality percentage).
3. Biomechanical Breakdown: If form faults or cues were flagged (e.g. knees inward, back rounding, shoulder swinging), explain constructively WHY it happened (fatigue, weak abductors, core bracing) and how to correct it.
4. Effort & Fatigue Analysis: If RPE, RIR, or velocity loss is provided, comment on their exertion (e.g. pushing near muscular failure or maintaining clean speed).
5. Injury Awareness: If the athlete has known injuries or pain flags, explicitly ensure they are safe and provide injury-safe recovery cues.
6. Nutritional Recovery: Recommend target protein and hydration intake tailored to their calculated biometrics.
7. Open Handoff Question: End with an empathetic question asking how their body feels or if they need a post-workout recovery meal suggestion.

Keep your response inspiring, concise, and structured with clear bullet points.
""".strip()


def load_coach_handoff() -> Optional[Dict[str, Any]]:
    """Load latest coach handoff file from disk if available."""
    handoff_path = os.path.join(DATA_ROOT, "data", "coach_handoff.json")
    if not os.path.exists(handoff_path):
        return None
    try:
        with open(handoff_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading coach handoff: {e}")
        return None


def generate_post_workout_debrief(
    profile: Optional[Dict[str, Any]] = None,
    handoff: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Synthesize an intelligent, hyper-personalized post-workout debrief
    from the computer vision session and the athlete's biometric profile.
    """
    if not profile:
        profile = load_profile() or {}
    if not handoff:
        handoff = load_coach_handoff() or {}

    athlete_name = profile.get("name") or "Athlete"
    injuries = profile.get("injuries") or []
    goal = profile.get("goal") or "fitness"
    bio = calculate_biometrics(profile)

    last_session = handoff.get("last_session") or handoff.get("latest_report") or {}
    weekly = handoff.get("weekly") or {}
    imbalance = handoff.get("imbalance") or {}

    exercise_name = last_session.get("exercise") or "Workout Session"
    reps = last_session.get("reps", 0)
    good_reps = last_session.get("good_reps", 0)
    hold_time = last_session.get("hold_time", 0.0)
    top_cues = last_session.get("top_cues") or []
    worst_cue = last_session.get("worst_cue") or ""
    final_rpe = last_session.get("final_rpe")
    final_rir = last_session.get("final_rir")
    max_loss = last_session.get("max_velocity_loss_pct")

    context_prompt = f"""
ATHLETE PROFILE:
- Name: {athlete_name}
- Height: {bio['height_cm']} cm | Weight: {bio['weight_kg']} kg | BMI: {bio['bmi']}
- Daily Protein Target: {bio['protein_target_g']}g
- Daily Hydration Target: {bio['water_target_liters']}L
- Primary Goal: {goal}
- Injury Flags: {', '.join(injuries) if injuries else 'None reported'}

COMPLETED CV WORKOUT STATS:
- Exercise: {exercise_name}
- Completed Reps: {reps} (Good Reps: {good_reps})
- Hold Duration: {hold_time}s
- Effort / Fatigue: RPE {final_rpe if final_rpe else 'N/A'} (RIR ~{final_rir if final_rir is not None else 'N/A'}), Max Velocity Drop: {max_loss if max_loss else 0.0}%
- Most Frequent Form Cues: {json.dumps(top_cues[:3])}
- Rough-Rep Cue: {worst_cue or 'None'}
- Imbalance Notes: {imbalance.get('note', 'Even balance')}
- Weekly Volume Completed: {weekly.get('reps', reps)} reps across {weekly.get('workouts', 1)} workouts

Generate the post-workout coaching debrief for {athlete_name}.
"""

    try:
        debrief = generate_answer(
            prompt=context_prompt,
            system_prompt=DEBRIEF_SYSTEM_PROMPT,
            stream=False,
        )
        return debrief.strip()
    except Exception as e:
        logger.error(f"Failed to generate LLM debrief: {e}")
        # Fallback concise debrief
        return (
            f"Awesome work on completing your {reps} reps of {exercise_name}, {athlete_name}! "
            f"You logged {good_reps} clean reps with great dedication. "
            f"{f'Keep an eye on form cues: {worst_cue}. ' if worst_cue else ''}"
            f"Make sure to refuel with around {bio['protein_target_g'] / 4:.0f}g of protein and rehydrate. "
            f"How is your body feeling right now?"
        )
