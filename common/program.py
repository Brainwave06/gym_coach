from datetime import datetime, timedelta

from common.history import load_history, side_imbalance
from common.profile import blocked_exercises

# 4-week rotating full-body template. Day index 0,1,2 within each week.
_TEMPLATE = (
    ("squat", "pushup", "plank", "glute_bridge"),
    ("lunge", "biceps_curl", "wall_sit", "bird_dog"),
    ("squat", "pushup", "dead_bug", "plank"),
)

REGRESS = {
    "pushup": "knee_pushup",
    "knee_pushup": "knee_pushup",
}

PROGRESS = {
    "knee_pushup": "pushup",
}

_BILATERAL = {"lunge", "biceps_curl", "bird_dog"}


def _quality(row):
    reps = float(row.get("reps") or 0)
    good = float(row.get("good_reps") or 0)
    if reps <= 0:
        hold = float(row.get("hold_time") or 0)
        good_hold = float(row.get("good_time") or 0)
        if hold <= 0:
            return None
        return good_hold / hold
    return good / reps


def _latest_by_exercise(history):
    latest = {}
    for row in history:
        name = (row.get("exercise_id") or row.get("exercise") or "").lower()
        if not name:
            continue
        latest[name] = row
        for block in row.get("blocks") or []:
            bid = (block.get("exercise_id") or block.get("exercise") or "").lower()
            if bid:
                latest[bid] = block
    return latest


def _parse_when(row):
    raw = row.get("saved_at") or ""
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _pick_variant(exercise_id, profile, latest):
    blocked = blocked_exercises(profile)
    experience = profile.get("experience", "beginner")
    current = exercise_id
    saved = (profile.get("progression") or {}).get(exercise_id) or {}
    if saved.get("variant"):
        current = saved["variant"]
    elif experience == "beginner" and exercise_id in REGRESS:
        current = REGRESS[exercise_id]
    row = latest.get(current) or latest.get(exercise_id)
    if row is not None and not saved.get("variant"):
        quality = _quality(row)
        if quality is not None and quality < 0.5 and current in REGRESS:
            current = REGRESS[current]
        elif quality is not None and quality >= 0.85 and current in PROGRESS:
            current = PROGRESS[current]
    if current in blocked:
        fallback = REGRESS.get(current)
        if fallback and fallback not in blocked:
            return fallback
        return None
    return current


def _targets(exercise_id, profile, latest, week):
    experience = profile.get("experience", "beginner")
    base_reps = {"beginner": 6, "intermediate": 8, "advanced": 10}[experience]
    base_sets = {"beginner": 2, "intermediate": 3, "advanced": 3}[experience]
    hold = {"beginner": 20, "intermediate": 30, "advanced": 40}[experience]
    hold += min(week, 3) * 5
    reps = base_reps + min(week, 3)
    saved = (profile.get("progression") or {}).get(exercise_id) or {}
    if saved:
        return {
            "sets": int(saved.get("sets") or base_sets),
            "reps": int(saved.get("reps") or reps),
            "hold": int(saved.get("hold") or hold),
            "rest": 25,
        }
    row = latest.get(exercise_id)
    if row:
        quality = _quality(row)
        if quality is not None and quality >= 0.8:
            if row.get("mode") == "hold":
                hold = int(max(hold, (row.get("good_time") or hold) + 5))
            else:
                prev = int(row.get("target_reps") or row.get("reps") or reps)
                reps = prev + 1
        elif quality is not None and quality < 0.5:
            reps = max(5, reps - 2)
            hold = max(15, hold - 5)
    return {"sets": base_sets, "reps": reps, "hold": hold, "rest": 25}


def apply_time_budget(plan, minutes):
    minutes = int(minutes or 25)
    blocks = list(plan.get("blocks") or [])
    if minutes <= 15:
        for block in blocks:
            block["sets"] = 1
            block["rest"] = 15
        plan["blocks"] = blocks[:2]
        plan["include_cooldown"] = False
        plan["warmup_scale"] = 0.5
    elif minutes <= 25:
        for block in blocks:
            block["sets"] = min(int(block.get("sets") or 2), 2)
        plan["blocks"] = blocks[:3]
        plan["include_cooldown"] = True
        plan["warmup_scale"] = 1.0
    else:
        plan["include_cooldown"] = True
        plan["warmup_scale"] = 1.0
    plan["time_budget_min"] = minutes
    return plan


def maybe_add_imbalance_block(plan):
    imb = side_imbalance(load_history())
    plan["imbalance"] = imb
    weak = imb.get("weak_side")
    if not weak:
        return plan
    for block in plan.get("blocks") or []:
        if block.get("exercise_id") in _BILATERAL:
            block["emphasis"] = weak
            block["sets"] = int(block.get("sets") or 1) + 1
            break
    return plan


def should_suggest_recovery(history=None):
    history = history if history is not None else load_history()
    sessions = [r for r in history if r.get("kind") in ("workout", "recovery")]
    if not sessions:
        return False, ""
    last = sessions[-1]
    when = _parse_when(last)
    if when is None:
        return False, ""
    if datetime.now() - when > timedelta(hours=36):
        return False, ""
    if last.get("kind") == "recovery":
        return False, ""
    faded = any((b.get("ended_reason") == "form_fade") for b in last.get("blocks") or [])
    if faded:
        return True, "Form faded last session. A 12-minute mobility day is smarter."
    if not last.get("aborted"):
        return True, "You already trained in the last day. Recovery is optional."
    return False, ""


def recovery_plan(profile):
    blocked = blocked_exercises(profile)
    candidates = [
        {"exercise_id": "bird_dog", "sets": 1, "reps": 0, "hold": 25, "rest": 15},
        {"exercise_id": "dead_bug", "sets": 1, "reps": 0, "hold": 25, "rest": 15},
        {"exercise_id": "glute_bridge", "sets": 2, "reps": 6, "hold": 0, "rest": 15},
    ]
    blocks = [b for b in candidates if b["exercise_id"] not in blocked]
    return {
        "kind": "recovery",
        "week": 0,
        "day": 0,
        "name": "Recovery / mobility (~12 min)",
        "blocks": blocks,
        "include_cooldown": False,
        "warmup_scale": 1.0,
        "time_budget_min": 12,
    }


def today_plan(profile, recovery=False):
    if recovery:
        return recovery_plan(profile)
    history = load_history()
    workouts = [r for r in history if r.get("kind") == "workout"]
    day_index = len(workouts) % 3
    week = min(len(workouts) // 3, 3)
    latest = _latest_by_exercise(history)
    blocks = []
    for exercise_id in _TEMPLATE[day_index]:
        chosen = _pick_variant(exercise_id, profile, latest)
        if not chosen:
            continue
        target = _targets(chosen, profile, latest, week)
        blocks.append({
            "exercise_id": chosen,
            "sets": target["sets"],
            "reps": target["reps"],
            "hold": target["hold"],
            "rest": target["rest"],
        })
    plan = {
        "kind": "workout",
        "week": week + 1,
        "day": day_index + 1,
        "name": f"Week {week + 1} Day {day_index + 1}",
        "blocks": blocks,
    }
    apply_time_budget(plan, profile.get("time_budget_min", 25))
    maybe_add_imbalance_block(plan)
    return plan
