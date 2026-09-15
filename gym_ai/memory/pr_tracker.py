"""
Strength Personal Record (PR) tracker and 1RM calculator.
Implements the Epley 1RM formula and natural-language PR parsing.
"""

import re
from typing import Any, Dict, Optional


def calculate_epley_1rm(weight_kg: float, reps: int) -> float:
    """
    Calculate estimated One-Rep Max (1RM) using the established Epley formula:
    1RM = weight * (1 + reps / 30)
    For a 1-rep lift, returns the exact weight lifted.
    """
    if reps <= 0 or weight_kg <= 0:
        return 0.0
    if reps == 1:
        return round(float(weight_kg), 1)
    estimated = weight_kg * (1.0 + float(reps) / 30.0)
    return round(estimated, 1)


def parse_pr_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract exercise name, weight (kg), and reps from natural-language strings.
    Examples:
    - "I benched 80kg for 5 reps today"
    - "New squat PR: 120kg x 3"
    - "Deadlift 150 kg for 2 reps"
    - "Hit 65kg overhead press for 8 reps"
    """
    q = text.lower().strip()

    # Pattern 1: Explicit 'PR' or 'Hit' or 'Benched' with weight and reps
    # e.g. "bench 80kg for 5 reps", "squat PR: 100 kg x 5"
    exercise_keywords = r"(bench press|bench|squat|deadlift|rdl|overhead press|ohp|shoulder press|bicep curl|curl|lateral raise|pushup|pullup)"
    
    # Check weight: e.g. 80kg, 80 kg, 80 kilos
    weight_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kilos?|kilograms?)\b", q)
    # Check reps: e.g. for 5 reps, x 5, 5 reps
    reps_match = re.search(r"(?:x\s*|for\s*)?(\d+)\s*(?:reps?|rep)\b", q)
    if not reps_match:
        # Check 'x 5' pattern
        x_match = re.search(r"[xX]\s*(\d+)\b", q)
        if x_match:
            reps_match = x_match

    # Find which exercise
    ex_match = re.search(exercise_keywords, q)

    if weight_match and ex_match:
        try:
            weight = float(weight_match.group(1))
            reps = int(reps_match.group(1)) if reps_match else 1
            raw_ex = ex_match.group(1).strip()
            # Normalize exercise name
            normalized_map = {
                "bench": "Bench Press",
                "bench press": "Bench Press",
                "squat": "Squat",
                "deadlift": "Deadlift",
                "rdl": "Romanian Deadlift",
                "ohp": "Overhead Press",
                "overhead press": "Overhead Press",
                "shoulder press": "Overhead Press",
                "bicep curl": "Biceps Curl",
                "curl": "Biceps Curl",
                "lateral raise": "Lateral Raise",
                "pushup": "Push-up",
                "pullup": "Pull-up",
            }
            clean_ex = normalized_map.get(raw_ex, raw_ex.title())
            if 5.0 <= weight <= 500.0 and 1 <= reps <= 50:
                return {
                    "exercise": clean_ex,
                    "weight_kg": weight,
                    "reps": reps,
                    "estimated_1rm": calculate_epley_1rm(weight, reps),
                }
        except Exception:
            pass

    return None


def is_pr_inquiry(query: str) -> bool:
    """Check if the user is asking about their personal records or 1RM."""
    q = query.lower().strip()
    return bool(re.search(
        r"\b(what('s| is| are)|show|tell me|display|check|see|list)\s+.*?\b(prs?|personal records?|1rm|one rep max|max lift)\b|"
        r"\b(my\s+([a-z\s]+?\s+)?(prs?|personal records?|1rm|one rep max))\b|"
        r"\b(how much can i (bench|squat|deadlift|lift|press))\b",
        q
    ))


def format_pr_summary(exercise_name: Optional[str] = None) -> str:
    """Format stored PRs into a clean coaching report."""
    from gym_ai.memory.storage import get_all_personal_records
    prs = get_all_personal_records(exercise_name=exercise_name)
    if not prs:
        return "You don't have any Personal Records (PRs) logged yet. When you hit a heavy set, tell me (e.g. 'I benched 80kg for 5 reps') and I'll track your 1RM progression!"

    lines = ["🏆 **Your Athlete Personal Records (PRs):**\n"]
    best_prs = {}
    for pr in prs:
        ex = pr["exercise_name"]
        if ex not in best_prs or pr["estimated_1rm"] > best_prs[ex]["estimated_1rm"]:
            best_prs[ex] = pr

    for ex, pr in sorted(best_prs.items()):
        lines.append(
            f"- **{ex}**: **{pr['weight_kg']} kg** x **{pr['reps']} reps**  *(Estimated 1RM: {pr['estimated_1rm']} kg)*  —  *{pr['achieved_at'][:10]}*"
        )

    lines.append("\nKeep up the great lifting! Progressive overload is driving your gains.")
    return "\n".join(lines)
