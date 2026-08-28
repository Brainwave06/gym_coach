"""
User dataset for the Flutter app, backend, and diet/workout chatbot.

Files under data/dataset/:
  users.jsonl       one user profile + summary stats per line
  sessions.jsonl    one workout / practice / recovery per line
  form_cues.jsonl   one coaching cue observation per line
  manifest.json     counts + schema version

Live rows come from this machine's profile + history.jsonl.
Demo rows are labeled synthetic=true so they can seed a competition backend
without mixing into the real athlete.
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta

from common.history import current_streak, load_history, side_imbalance, weekly_report
from common.profile import load_profile, save_profile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(PROJECT_ROOT, "data", "dataset")
SCHEMA_VERSION = "1.0.0"


def make_user_id(name, salt=""):
    raw = f"{(name or 'athlete').strip().lower()}|{salt}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"usr_{digest}"


def ensure_user_id(profile):
    if not profile.get("user_id"):
        profile["user_id"] = make_user_id(profile.get("name"), salt=str(uuid.uuid4())[:8])
        save_profile(profile)
    return profile["user_id"]


def _slug_exercise(block):
    return (
        block.get("exercise_id")
        or str(block.get("exercise") or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _session_id(user_id, saved_at, index):
    raw = f"{user_id}|{saved_at}|{index}"
    return "ses_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _clean_block(block):
    return {
        "exercise_id": _slug_exercise(block) or None,
        "exercise": block.get("exercise"),
        "mode": block.get("mode"),
        "reps": int(block.get("reps") or 0),
        "good_reps": int(block.get("good_reps") or 0),
        "hold_time": float(block.get("hold_time") or 0),
        "good_time": float(block.get("good_time") or 0),
        "feel": block.get("feel"),
        "ended_reason": block.get("ended_reason"),
        "target_reps": block.get("target_reps"),
        "target_hold": block.get("target_hold"),
        "side_stats": block.get("side_stats") or {},
        "top_cues": [
            {
                "cue": item.get("cue") if isinstance(item, dict) else str(item),
                "count": int(item.get("count", 1) if isinstance(item, dict) else 1),
            }
            for item in (block.get("top_cues") or [])
        ],
    }


def sessions_from_history(user_id, history):
    sessions = []
    cues = []
    for index, row in enumerate(history):
        saved_at = row.get("saved_at") or datetime.now().isoformat(timespec="seconds")
        sid = _session_id(user_id, saved_at, index)
        if row.get("kind") in ("workout", "recovery"):
            blocks = [_clean_block(b) for b in (row.get("blocks") or [])]
            session = {
                "session_id": sid,
                "user_id": user_id,
                "kind": row.get("kind"),
                "saved_at": saved_at,
                "plan": row.get("plan"),
                "week": row.get("week"),
                "day": row.get("day"),
                "aborted": bool(row.get("aborted")),
                "time_budget_min": row.get("time_budget_min"),
                "blocks": blocks,
            }
        elif row.get("exercise") or row.get("exercise_id"):
            block = _clean_block(row)
            session = {
                "session_id": sid,
                "user_id": user_id,
                "kind": "practice",
                "saved_at": saved_at,
                "plan": None,
                "week": None,
                "day": None,
                "aborted": row.get("ended_reason") == "quit",
                "time_budget_min": None,
                "blocks": [block],
            }
        else:
            continue
        sessions.append(session)
        for block in session["blocks"]:
            for item in block.get("top_cues") or []:
                cues.append({
                    "user_id": user_id,
                    "session_id": sid,
                    "exercise_id": block.get("exercise_id"),
                    "cue": item["cue"],
                    "count": item["count"],
                    "saved_at": saved_at,
                })
    return sessions, cues


def user_record(profile, history, synthetic=False):
    user_id = profile.get("user_id") or make_user_id(profile.get("name"))
    weekly = weekly_report(history)
    return {
        "user_id": user_id,
        "display_name": profile.get("name") or "Athlete",
        "synthetic": bool(synthetic),
        "source": "desktop_cv_coach" if not synthetic else "demo_seed",
        "profile": {
            "goal": profile.get("goal"),
            "experience": profile.get("experience"),
            "injuries": list(profile.get("injuries") or []),
            "equipment": profile.get("equipment"),
            "time_budget_min": profile.get("time_budget_min"),
            "voice_mode": profile.get("voice_mode"),
        },
        "progression": profile.get("progression") or {},
        "stats": {
            "streak": current_streak(history),
            "workouts": weekly.get("workouts"),
            "sessions": weekly.get("sessions"),
            "reps": weekly.get("reps"),
            "good_reps": weekly.get("good_reps"),
            "quality": weekly.get("quality"),
            "hold_time": weekly.get("hold_time"),
        },
        "imbalance": side_imbalance(history),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "notes_for_chatbot": (
            "Use profile.goal and injuries for diet/plan suggestions. "
            "Honor pain feels and form_fade. CV coach owns live form."
        ),
    }


def _demo_block(exercise_id, name, mode, reps, good, feel, cues, hold=0, good_hold=0):
    return {
        "exercise_id": exercise_id,
        "exercise": name,
        "mode": mode,
        "reps": reps,
        "good_reps": good,
        "hold_time": hold,
        "good_time": good_hold,
        "feel": feel,
        "ended_reason": "target",
        "top_cues": [{"cue": c, "count": n} for c, n in cues],
        "side_stats": {},
    }


def demo_users():
    """Four fake athletes so the backend/chatbot has a starter dataset."""
    base = datetime.now() - timedelta(days=10)
    people = [
        {
            "user_id": "usr_demo_lina",
            "name": "Lina Hassan",
            "goal": "fat_loss",
            "experience": "beginner",
            "injuries": ["knees"],
            "equipment": "floor",
            "time_budget_min": 15,
            "sessions": [
                {
                    "kind": "workout",
                    "plan": "Week 1 Day 1",
                    "week": 1,
                    "day": 1,
                    "aborted": False,
                    "saved_at": (base + timedelta(days=1)).isoformat(timespec="seconds"),
                    "blocks": [
                        _demo_block("box_squat", "Box Squat", "reps", 12, 9, "hard",
                                    [("Sit the hips back", 2), ("Good depth!", 9)]),
                        _demo_block("knee_pushup", "Knee Push-up", "reps", 10, 7, "hard",
                                    [("Keep a straight line", 3)]),
                        _demo_block("plank", "Plank", "hold", 0, 0, "easy",
                                    [("Don't sag", 1)], hold=25, good_hold=20),
                    ],
                },
                {
                    "kind": "workout",
                    "plan": "Week 1 Day 2",
                    "week": 1,
                    "day": 2,
                    "aborted": False,
                    "saved_at": (base + timedelta(days=3)).isoformat(timespec="seconds"),
                    "blocks": [
                        _demo_block("glute_bridge", "Glute Bridge", "reps", 14, 12, "easy",
                                    [("Strong lockout!", 12)]),
                        _demo_block("bird_dog", "Bird Dog", "hold", 0, 0, "hard",
                                    [("Hips square", 4)], hold=20, good_hold=16),
                    ],
                },
            ],
        },
        {
            "user_id": "usr_demo_omar",
            "name": "Omar Farid",
            "goal": "strength",
            "experience": "intermediate",
            "injuries": [],
            "equipment": "dumbbells",
            "time_budget_min": 40,
            "sessions": [
                {
                    "kind": "workout",
                    "plan": "Week 2 Day 1",
                    "week": 2,
                    "day": 1,
                    "aborted": False,
                    "saved_at": (base + timedelta(days=2)).isoformat(timespec="seconds"),
                    "blocks": [
                        _demo_block("squat", "Squat", "reps", 24, 20, "easy",
                                    [("Good depth!", 20), ("Heels down", 2)],
                                    ),
                        _demo_block("pushup", "Push-up", "reps", 18, 14, "hard",
                                    [("Clean push-up!", 14), ("Hips sagging", 4)]),
                        _demo_block("biceps_curl", "Biceps Curl", "reps", 20, 16, "easy",
                                    [("Elbow pinned", 3)]),
                    ],
                },
                {
                    "kind": "practice",
                    "plan": None,
                    "week": None,
                    "day": None,
                    "aborted": False,
                    "saved_at": (base + timedelta(days=4)).isoformat(timespec="seconds"),
                    "blocks": [
                        _demo_block("lunge", "Lunge", "reps", 16, 8, "hard",
                                    [("Front knee racing past toes", 6), ("Solid lunge (right)!", 5),
                                     ("Solid lunge (left)!", 3)]),
                    ],
                },
            ],
        },
        {
            "user_id": "usr_demo_sara",
            "name": "Sara Nabil",
            "goal": "health",
            "experience": "beginner",
            "injuries": ["shoulders"],
            "equipment": "floor",
            "time_budget_min": 25,
            "sessions": [
                {
                    "kind": "recovery",
                    "plan": "Recovery / mobility (~12 min)",
                    "week": 0,
                    "day": 0,
                    "aborted": False,
                    "saved_at": (base + timedelta(days=5)).isoformat(timespec="seconds"),
                    "blocks": [
                        _demo_block("glute_bridge", "Glute Bridge", "reps", 12, 10, "easy",
                                    [("Even through both heels", 2)]),
                        _demo_block("dead_bug", "Dead Bug", "hold", 0, 0, "hard",
                                    [("Ribs down", 3)], hold=25, good_hold=18),
                    ],
                },
            ],
        },
        {
            "user_id": "usr_demo_karim",
            "name": "Karim Adel",
            "goal": "strength",
            "experience": "advanced",
            "injuries": ["back"],
            "equipment": "dumbbells",
            "time_budget_min": 40,
            "sessions": [
                {
                    "kind": "workout",
                    "plan": "Week 3 Day 1",
                    "week": 3,
                    "day": 1,
                    "aborted": False,
                    "saved_at": (base + timedelta(days=6)).isoformat(timespec="seconds"),
                    "blocks": [
                        _demo_block("squat", "Squat", "reps", 30, 28, "easy",
                                    [("Good depth!", 28)]),
                        _demo_block("lunge", "Lunge", "reps", 20, 11, "pain",
                                    [("Torso tipping", 5), ("Solid lunge (right)!", 8)]),
                    ],
                },
            ],
        },
    ]

    users = []
    sessions = []
    cues = []
    for person in people:
        fake_history = []
        for sess in person["sessions"]:
            if sess["kind"] in ("workout", "recovery"):
                fake_history.append({
                    "kind": sess["kind"],
                    "plan": sess["plan"],
                    "week": sess["week"],
                    "day": sess["day"],
                    "aborted": sess["aborted"],
                    "saved_at": sess["saved_at"],
                    "blocks": sess["blocks"],
                })
            else:
                block = sess["blocks"][0]
                fake_history.append({**block, "saved_at": sess["saved_at"]})
        profile = {
            "user_id": person["user_id"],
            "name": person["name"],
            "goal": person["goal"],
            "experience": person["experience"],
            "injuries": person["injuries"],
            "equipment": person["equipment"],
            "time_budget_min": person["time_budget_min"],
            "voice_mode": "full",
            "progression": {},
        }
        users.append(user_record(profile, fake_history, synthetic=True))
        more_s, more_c = sessions_from_history(person["user_id"], fake_history)
        sessions.extend(more_s)
        cues.extend(more_c)
    return users, sessions, cues


def _write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def export_dataset(include_demo=True):
    os.makedirs(DATASET_DIR, exist_ok=True)
    profile = load_profile() or {"name": "Athlete"}
    if not profile.get("user_id"):
        profile["user_id"] = make_user_id(profile.get("name"), salt="live")
        if os.path.exists(os.path.join(PROJECT_ROOT, "data", "profile.json")):
            save_profile(profile)

    history = load_history()
    live_user = user_record(profile, history, synthetic=False)
    live_sessions, live_cues = sessions_from_history(live_user["user_id"], history)

    users = [live_user]
    sessions = list(live_sessions)
    cues = list(live_cues)
    if include_demo:
        d_users, d_sessions, d_cues = demo_users()
        users.extend(d_users)
        sessions.extend(d_sessions)
        cues.extend(d_cues)

    users_path = os.path.join(DATASET_DIR, "users.jsonl")
    sessions_path = os.path.join(DATASET_DIR, "sessions.jsonl")
    cues_path = os.path.join(DATASET_DIR, "form_cues.jsonl")
    manifest_path = os.path.join(DATASET_DIR, "manifest.json")
    _write_jsonl(users_path, users)
    _write_jsonl(sessions_path, sessions)
    _write_jsonl(cues_path, cues)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "users": len(users),
        "sessions": len(sessions),
        "form_cues": len(cues),
        "files": {
            "users": "users.jsonl",
            "sessions": "sessions.jsonl",
            "form_cues": "form_cues.jsonl",
        },
        "fields": {
            "users": ["user_id", "display_name", "synthetic", "profile", "stats", "imbalance", "progression"],
            "sessions": ["session_id", "user_id", "kind", "saved_at", "blocks"],
            "form_cues": ["user_id", "session_id", "exercise_id", "cue", "count", "saved_at"],
        },
        "notes": (
            "synthetic=true rows are demo athletes for backend/chatbot tests. "
            "Join users.user_id to sessions.user_id. "
            "Chatbot should not treat pain or form_fade as a cue to push harder."
        ),
    }
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest


def print_dataset_summary(manifest=None):
    manifest = manifest or export_dataset()
    print()
    print("=== User dataset ===")
    print(f"Schema {manifest['schema_version']}")
    print(f"Users: {manifest['users']}   sessions: {manifest['sessions']}   cues: {manifest['form_cues']}")
    print(f"Folder: {DATASET_DIR}")
    print("  users.jsonl")
    print("  sessions.jsonl")
    print("  form_cues.jsonl")
    print("  manifest.json")
    print()
    return manifest
