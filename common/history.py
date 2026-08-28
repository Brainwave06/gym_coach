import json
import os
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(PROJECT_ROOT, "data", "history.jsonl")


def append_session(record):
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    record = dict(record)
    record.pop("worst_clip", None)
    record.pop("good_clip", None)
    for block in record.get("blocks") or []:
        if isinstance(block, dict):
            block.pop("worst_clip", None)
            block.pop("good_clip", None)
    record.setdefault("saved_at", datetime.now().isoformat(timespec="seconds"))
    with open(HISTORY_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    return HISTORY_PATH


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    rows = []
    with open(HISTORY_PATH, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _parse_when(row):
    raw = row.get("saved_at") or ""
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def workout_dates(rows):
    days = []
    for row in rows:
        if row.get("kind") == "workout" or row.get("exercise"):
            when = _parse_when(row)
            if when:
                days.append(when.date())
    return sorted(set(days))


def current_streak(rows):
    days = workout_dates(rows)
    if not days:
        return 0
    streak = 0
    cursor = datetime.now().date()
    if days[-1] < cursor - timedelta(days=1):
        return 0
    while cursor in days or (streak == 0 and cursor - timedelta(days=1) in days):
        if cursor in days:
            streak += 1
            cursor -= timedelta(days=1)
        elif streak == 0:
            cursor -= timedelta(days=1)
        else:
            break
    return streak


def weekly_report(rows, days=7):
    cutoff = datetime.now() - timedelta(days=days)
    recent = [r for r in rows if (_parse_when(r) or datetime.min) >= cutoff]
    workouts = [r for r in recent if r.get("kind") == "workout"]
    sessions = [r for r in recent if r.get("kind") != "workout" and r.get("exercise")]
    if not sessions and workouts:
        for workout in workouts:
            sessions.extend(workout.get("blocks") or [])

    total_reps = sum(int(s.get("reps") or 0) for s in sessions)
    good_reps = sum(int(s.get("good_reps") or 0) for s in sessions)
    hold = sum(float(s.get("hold_time") or 0) for s in sessions)
    cues = {}
    for session in sessions:
        for item in session.get("top_cues") or []:
            cue = item.get("cue") if isinstance(item, dict) else str(item)
            count = item.get("count", 1) if isinstance(item, dict) else 1
            cues[cue] = cues.get(cue, 0) + count
    top = sorted(cues.items(), key=lambda kv: kv[1], reverse=True)[:5]
    quality = (good_reps / total_reps) if total_reps else None
    return {
        "days": days,
        "sessions": len(sessions),
        "workouts": len(workouts),
        "reps": total_reps,
        "good_reps": good_reps,
        "quality": quality,
        "hold_time": round(hold, 1),
        "streak": current_streak(rows),
        "top_cues": [{"cue": c, "count": n} for c, n in top],
        "skipped_note": _skipped_note(rows),
        "imbalance": side_imbalance(rows),
    }


def side_imbalance(rows):
    """Which side looked weaker across recent bilateral work."""
    left_good = left_n = right_good = right_n = 0
    for row in rows:
        blocks = row.get("blocks") if row.get("kind") == "workout" else [row]
        for block in blocks or []:
            stats = block.get("side_stats") or {}
            left = stats.get("left") or {}
            right = stats.get("right") or {}
            left_n += int(left.get("reps") or 0)
            left_good += int(left.get("good") or 0)
            right_n += int(right.get("reps") or 0)
            right_good += int(right.get("good") or 0)
    if left_n < 4 or right_n < 4:
        return {"weak_side": None, "note": "Not enough left/right reps yet."}
    left_q = left_good / left_n
    right_q = right_good / right_n
    if left_q + 0.12 < right_q:
        weak = "left"
    elif right_q + 0.12 < left_q:
        weak = "right"
    else:
        return {
            "weak_side": None,
            "left_quality": round(left_q, 2),
            "right_quality": round(right_q, 2),
            "note": "Left and right are roughly even.",
        }
    return {
        "weak_side": weak,
        "left_quality": round(left_q, 2),
        "right_quality": round(right_q, 2),
        "note": f"Your {weak} side is lagging. Extra work there next session.",
    }


def _skipped_note(rows):
    days = workout_dates(rows)
    if not days:
        return "No sessions yet — today is a good day to start."
    last = days[-1]
    gap = (datetime.now().date() - last).days
    if gap >= 2:
        return f"You last trained {gap} days ago. A short session still counts."
    return ""


def print_weekly_report(report):
    print()
    print(f"=== Last {report['days']} days ===")
    print(f"Workouts: {report['workouts']}   exercise clips: {report['sessions']}")
    print(f"Streak: {report['streak']} day(s)")
    if report["quality"] is not None:
        print(f"Good-rep rate: {report['quality']:.0%}  ({report['good_reps']}/{report['reps']})")
    print(f"Hold time: {report['hold_time']}s")
    if report["top_cues"]:
        print("Most common cues:")
        for item in report["top_cues"]:
            print(f"  {item['count']}x  {item['cue']}")
    if report.get("imbalance") and report["imbalance"].get("note"):
        print(report["imbalance"]["note"])
    if report["skipped_note"]:
        print(report["skipped_note"])
    print()
