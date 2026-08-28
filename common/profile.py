import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_PATH = os.path.join(PROJECT_ROOT, "data", "profile.json")

INJURY_BLOCKS = {
    "knees": {"lunge", "wall_sit"},
    "back": {"dead_bug"},
    "shoulders": {"pushup", "knee_pushup", "plank", "biceps_curl"},
}


def load_profile():
    if not os.path.exists(PROFILE_PATH):
        return None
    with open(PROFILE_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def save_profile(profile):
    os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as handle:
        json.dump(profile, handle, indent=2)
    return PROFILE_PATH


def _pick(prompt, options):
    print(prompt)
    for key, label in options:
        print(f"  {key}) {label}")
    allowed = {key for key, _ in options}
    while True:
        choice = input("Choice: ").strip().lower()
        if choice in allowed:
            return choice
        print("Pick one of:", ", ".join(sorted(allowed)))


def run_onboarding():
    print()
    print("Quick intake — same questions a coach asks on day one.")
    name = input("What should I call you? ").strip() or "Athlete"
    goal = _pick("Goal?", [
        ("1", "Get stronger"),
        ("2", "Lose fat / feel fitter"),
        ("3", "Move better / general health"),
    ])
    experience = _pick("Training experience?", [
        ("1", "Beginner"),
        ("2", "Some experience"),
        ("3", "Advanced"),
    ])
    print("Injuries? Type any of: knees, back, shoulders, none")
    injury_raw = input("Injuries: ").strip().lower()
    injuries = []
    for token in ("knees", "back", "shoulders"):
        if token in injury_raw:
            injuries.append(token)
    equipment = _pick("Equipment?", [
        ("1", "Floor only"),
        ("2", "Dumbbells too"),
    ])
    time_budget = _pick("How long do you usually have?", [
        ("1", "15 minutes"),
        ("2", "25 minutes"),
        ("3", "40 minutes"),
    ])
    voice_mode = _pick("Voice while you train?", [
        ("1", "Talk normally"),
        ("2", "Quiet — fewer cues"),
        ("3", "Text only — no speech"),
    ])
    profile = {
        "name": name,
        "goal": {"1": "strength", "2": "fat_loss", "3": "health"}[goal],
        "experience": {"1": "beginner", "2": "intermediate", "3": "advanced"}[experience],
        "injuries": injuries,
        "equipment": "dumbbells" if equipment == "2" else "floor",
        "time_budget_min": {"1": 15, "2": 25, "3": 40}[time_budget],
        "voice_mode": {"1": "full", "2": "quiet", "3": "text"}[voice_mode],
        "cue_gap_seconds": 4.0,
        "progression": {},
        "camera_setup": None,
    }
    save_profile(profile)
    print(f"Saved profile for {name}.")
    return ensure_defaults(profile)


def ensure_defaults(profile):
    profile.setdefault("time_budget_min", 25)
    profile.setdefault("voice_mode", "full")
    profile.setdefault("cue_gap_seconds", 4.0)
    profile.setdefault("progression", {})
    profile.setdefault("camera_setup", None)
    if not profile.get("user_id"):
        import hashlib
        seed = (profile.get("name") or "athlete").strip().lower()
        profile["user_id"] = "usr_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
        save_profile(profile)
    return profile


def load_or_onboard():
    profile = load_profile()
    if profile:
        return ensure_defaults(profile)
    return ensure_defaults(run_onboarding())


def edit_session_prefs(profile):
    print()
    print(f"Current: {profile.get('time_budget_min')} min, voice={profile.get('voice_mode')}")
    time_budget = _pick("Session length?", [
        ("1", "15 minutes"),
        ("2", "25 minutes"),
        ("3", "40 minutes"),
    ])
    voice_mode = _pick("Voice?", [
        ("1", "Talk normally"),
        ("2", "Quiet — fewer cues"),
        ("3", "Text only"),
    ])
    profile["time_budget_min"] = {"1": 15, "2": 25, "3": 40}[time_budget]
    profile["voice_mode"] = {"1": "full", "2": "quiet", "3": "text"}[voice_mode]
    profile["cue_gap_seconds"] = 8.0 if profile["voice_mode"] == "quiet" else 4.0
    save_profile(profile)
    print("Saved.")
    return profile


def update_progression(profile, exercise_id, feel, quality, ended_reason, sets, reps, hold, variant=None):
    """Write next-session targets after pain / hard / easy."""
    ensure_defaults(profile)
    entry = dict(profile["progression"].get(exercise_id) or {})
    entry["variant"] = variant or entry.get("variant") or exercise_id
    entry["sets"] = int(sets or entry.get("sets") or 2)
    entry["reps"] = int(reps or entry.get("reps") or 8)
    entry["hold"] = int(hold or entry.get("hold") or 25)
    entry["last_feel"] = feel
    entry["last_quality"] = None if quality is None else round(float(quality), 3)
    entry["last_ended"] = ended_reason

    if feel == "pain" or ended_reason == "form_fade":
        entry["sets"] = max(1, entry["sets"] - 1)
        entry["reps"] = max(5, entry["reps"] - 2)
        entry["hold"] = max(15, entry["hold"] - 5)
        from common.program import REGRESS
        if entry["variant"] in REGRESS:
            entry["variant"] = REGRESS[entry["variant"]]
    elif feel == "easy" and (quality is None or quality >= 0.8):
        entry["reps"] = min(15, entry["reps"] + 1)
        entry["hold"] = min(60, entry["hold"] + 5)
        from common.program import PROGRESS
        if entry["variant"] in PROGRESS:
            entry["variant"] = PROGRESS[entry["variant"]]
    profile["progression"][exercise_id] = entry
    profile["progression"][entry["variant"]] = entry
    return entry


def blocked_exercises(profile):
    blocked = set()
    for injury in profile.get("injuries") or []:
        blocked |= INJURY_BLOCKS.get(injury, set())
    if profile.get("equipment") != "dumbbells":
        blocked.add("biceps_curl")
    return blocked
