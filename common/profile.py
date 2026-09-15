import json
import os

from common.paths import DATA_ROOT
PROFILE_PATH = os.path.join(DATA_ROOT, "data", "profile.json")

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


def calculate_biometrics(profile):
    """
    Calculate metabolic and fitness targets based on height, weight, age, and goal.
    Uses the Mifflin-St Jeor formula and evidence-based sports nutrition ratios.
    """
    height_cm = float(profile.get("height_cm") or 175.0)
    weight_kg = float(profile.get("weight_kg") or 70.0)
    age = int(profile.get("age") or 25)
    gender = str(profile.get("gender") or "male").lower()
    goal = str(profile.get("goal") or "health").lower()

    # BMI calculation
    height_m = max(0.5, height_cm / 100.0)
    bmi = round(weight_kg / (height_m ** 2), 1)
    if bmi < 18.5:
        bmi_cat = "Underweight"
    elif bmi < 25.0:
        bmi_cat = "Normal weight"
    elif bmi < 30.0:
        bmi_cat = "Overweight"
    else:
        bmi_cat = "Obese"

    # Mifflin-St Jeor Basal Metabolic Rate (BMR)
    if "f" in gender or "woman" in gender or "female" in gender:
        bmr = round(10 * weight_kg + 6.25 * height_cm - 5 * age - 161)
    else:
        bmr = round(10 * weight_kg + 6.25 * height_cm - 5 * age + 5)

    # Activity factor estimation (1.35x sedentary to light training)
    tdee = round(bmr * 1.35)

    # Goal-adjusted calories & protein
    if goal == "fat_loss":
        target_calories = max(1200, tdee - 400)
        protein_ratio = 2.2  # Higher protein to preserve lean muscle in deficit
    elif goal == "strength":
        target_calories = tdee + 250
        protein_ratio = 2.0
    else:
        target_calories = tdee
        protein_ratio = 1.8

    protein_target_g = round(weight_kg * protein_ratio, 1)
    water_target_l = round(weight_kg * 0.035, 1)

    return {
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "age": age,
        "gender": gender,
        "bmi": bmi,
        "bmi_category": bmi_cat,
        "bmr_kcal": bmr,
        "estimated_tdee_kcal": tdee,
        "target_calories_kcal": target_calories,
        "protein_target_g": protein_target_g,
        "water_target_liters": water_target_l,
        "dietary_preferences": profile.get("dietary_preferences", "none"),
    }


def run_onboarding():
    print()
    print("=" * 48)
    print("  FitPath Intake — Building Your Coach Profile")
    print("=" * 48)
    name = input("What should I call you? ").strip() or "Athlete"

    # Physical Biometrics for Coach
    print("\n[Physical Metrics for Accurate Coaching & Nutrition]")
    try:
        height_raw = input("Height in cm (e.g. 175)? ").strip()
        height_cm = float(height_raw) if height_raw else 175.0
    except ValueError:
        height_cm = 175.0

    try:
        weight_raw = input("Weight in kg (e.g. 75)? ").strip()
        weight_kg = float(weight_raw) if weight_raw else 70.0
    except ValueError:
        weight_kg = 70.0

    try:
        age_raw = input("Age in years (e.g. 25)? ").strip()
        age = int(age_raw) if age_raw else 25
    except ValueError:
        age = 25

    gender_choice = _pick("Biological sex (for metabolic BMR calculation)?", [
        ("1", "Male"),
        ("2", "Female"),
        ("3", "Other / Prefer not to say"),
    ])
    gender = {"1": "male", "2": "female", "3": "unspecified"}[gender_choice]

    diet_pref = input("Any dietary restrictions or preferences (e.g., none, vegetarian, high-protein, keto)? ").strip()
    dietary_preferences = diet_pref if diet_pref else "none"

    print("\n[Training Preferences]")
    goal = _pick("Primary Goal?", [
        ("1", "Get stronger / Build muscle"),
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
    voice_gender = _pick("Voice model?", [
        ("1", "Female"),
        ("2", "Male"),
    ])
    profile = {
        "name": name,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "age": age,
        "gender": gender,
        "dietary_preferences": dietary_preferences,
        "goal": {"1": "strength", "2": "fat_loss", "3": "health"}[goal],
        "experience": {"1": "beginner", "2": "intermediate", "3": "advanced"}[experience],
        "injuries": injuries,
        "equipment": "dumbbells" if equipment == "2" else "floor",
        "time_budget_min": {"1": 15, "2": 25, "3": 40}[time_budget],
        "voice_mode": {"1": "full", "2": "quiet", "3": "text"}[voice_mode],
        "voice_gender": {"1": "Female", "2": "Male"}[voice_gender],
        "cue_gap_seconds": 4.0,
        "progression": {},
        "camera_setup": None,
    }
    save_profile(profile)
    bio = calculate_biometrics(profile)
    print(f"\nProfile saved for {name}!")
    print(f"  Height: {height_cm} cm | Weight: {weight_kg} kg | BMI: {bio['bmi']} ({bio['bmi_category']})")
    print(f"  Target Protein: {bio['protein_target_g']}g/day | Daily Water: {bio['water_target_liters']}L")
    return ensure_defaults(profile)


def edit_biometrics(profile):
    """Interactive editor to update athlete weight, height, and dietary preferences."""
    print()
    print("=== Update Athlete Biometrics ===")
    print(f"Current Height: {profile.get('height_cm', 175)} cm")
    print(f"Current Weight: {profile.get('weight_kg', 70)} kg")
    print(f"Dietary Preferences: {profile.get('dietary_preferences', 'none')}")

    h_input = input("New Height in cm (press Enter to keep): ").strip()
    if h_input:
        try:
            profile["height_cm"] = float(h_input)
        except ValueError:
            pass

    w_input = input("New Weight in kg (press Enter to keep): ").strip()
    if w_input:
        try:
            profile["weight_kg"] = float(w_input)
        except ValueError:
            pass

    d_input = input("New Dietary preferences (press Enter to keep): ").strip()
    if d_input:
        profile["dietary_preferences"] = d_input

    save_profile(profile)
    bio = calculate_biometrics(profile)
    print("\nBiometrics updated successfully!")
    print(f"  BMI: {bio['bmi']} ({bio['bmi_category']}) | Protein Target: {bio['protein_target_g']}g/day")
    return profile


def ensure_defaults(profile):
    profile.setdefault("height_cm", 175.0)
    profile.setdefault("weight_kg", 70.0)
    profile.setdefault("age", 25)
    profile.setdefault("gender", "unspecified")
    profile.setdefault("dietary_preferences", "none")
    profile.setdefault("time_budget_min", 25)
    profile.setdefault("voice_mode", "full")
    profile.setdefault("voice_gender", "Female")
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
    voice_gender = _pick("Voice model?", [
        ("1", "Female"),
        ("2", "Male"),
    ])
    profile["time_budget_min"] = {"1": 15, "2": 25, "3": 40}[time_budget]
    profile["voice_mode"] = {"1": "full", "2": "quiet", "3": "text"}[voice_mode]
    profile["voice_gender"] = {"1": "Female", "2": "Male"}[voice_gender]
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
