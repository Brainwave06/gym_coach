"""
AI Exercise Coach — today's workout, practice mode, and weekly report.
"""

import argparse

from common.catalog import BASE, MENU, get_config
from common.exercise_engine import run_exercise
from common.history import current_streak, load_history, print_weekly_report, weekly_report
from common.profile import edit_session_prefs, load_or_onboard, run_onboarding
from common.session_player import run_todays_workout
from common.setup_wizard import run_camera_setup
from common.voice import configure_voice, stop_voice

ALIASES = {
    "s": "squat",
    "p": "plank",
    "u": "pushup",
    "push": "pushup",
    "push-up": "pushup",
    "pushups": "pushup",
    "pushapp": "pushup",
    "l": "lunge",
    "g": "glute_bridge",
    "glute": "glute_bridge",
    "bridge": "glute_bridge",
    "w": "wall_sit",
    "wall": "wall_sit",
    "b": "bird_dog",
    "birddog": "bird_dog",
    "d": "dead_bug",
    "deadbug": "dead_bug",
    "c": "biceps_curl",
    "curl": "biceps_curl",
    "biceps": "biceps_curl",
    "box": "box_squat",
    "knee": "knee_pushup",
    "rdl": "rdl",
    "deadlift": "rdl",
    "dead": "rdl",
    "ohp": "overhead_press",
    "overhead": "overhead_press",
    "press": "overhead_press",
    "shoulder": "overhead_press",
    "shoulder_press": "overhead_press",
    "lateral": "lateral_raise",
    "lat": "lateral_raise",
    "raise": "lateral_raise",
    "lat_raise": "lateral_raise",
}


def choose_practice():
    print("Practice one movement")
    for key, name, label in MENU:
        print(f"  {key}) {label}")
    print("  q) Back")
    while True:
        choice = input("Choose: ").strip().lower()
        if choice in ("q", "quit", "back"):
            return None
        for key, name, _label in MENU:
            if choice == key or choice == name:
                return name
        if choice in ALIASES:
            return ALIASES[choice]
        if choice in BASE:
            return choice
        print("Type 1-9, an exercise name, or q.")


def home_menu(profile):
    streak = current_streak(load_history())
    from common.profile import calculate_biometrics
    bio = calculate_biometrics(profile)
    print()
    print(f"AI Exercise Coach  —  hi {profile.get('name', '')}")
    print(f"  Streak: {streak} day" + ("" if streak == 1 else "s") + f"   Goal: {profile.get('goal', 'health')}")
    print(f"  Height: {bio['height_cm']:.0f} cm   Weight: {bio['weight_kg']:.0f} kg   BMI: {bio['bmi']} ({bio['bmi_category']})")
    print(f"  Target Protein: {bio['protein_target_g']}g/day   Time: {profile.get('time_budget_min', 25)} min")
    print("  1) Today's workout   (warm-up, prescribed sets, cooldown)")
    print("  2) Practice one exercise")
    print("  3) Weekly report")
    print("  4) Redo onboarding")
    print("  5) Camera setup")
    print("  6) Voice and session time")
    print("  7) Update athlete biometrics (height, weight, diet)")
    print("  8) Export user dataset")
    print("  9) Chat with Gym AI Coach")
    print("  q) Quit")
    return input("Choose: ").strip().lower()


def run_chat_coach(profile):
    import sys
    from common.profile import calculate_biometrics, load_profile
    from gym_ai import generate_personalized_plan, run_pipeline

    active_profile = load_profile() or profile
    bio = calculate_biometrics(active_profile)

    print("\n" + "=" * 52)
    print(f"      FitPath Gym AI Coach Mode — {active_profile.get('name', 'Athlete')}")
    print("=" * 52)
    print(f"Metrics: {bio['height_cm']:.0f} cm | {bio['weight_kg']:.0f} kg | BMI: {bio['bmi']} ({bio['bmi_category']})")
    print(f"Targets: {bio['protein_target_g']}g protein/day | {bio['water_target_liters']}L water/day")
    print("Ask anything about gym workouts, technique, injury rehab, or diet.")
    print("Tips: Say 'my weight is 80kg' to update stats anytime.")
    print("Commands: 'plan' (create routine), 'meal <path>' (analyze meal photo), 'prs' (view best lifts), 'menu' (return)\n")

    chat_history = []
    athlete_context = {"athlete": active_profile}

    # Proactive Post-Workout Debriefing check
    try:
        from gym_ai.debrief import generate_post_workout_debrief, load_coach_handoff
        handoff = load_coach_handoff()
        if handoff and (handoff.get("last_session") or handoff.get("latest_report")):
            print("Coach is reviewing your latest computer-vision workout session...\n")
            debrief_msg = generate_post_workout_debrief(active_profile, handoff)
            print(f"Coach > {debrief_msg}\n")
            chat_history.append({"role": "assistant", "content": debrief_msg})
    except Exception:
        pass

    while True:
        try:
            user_input = input(f"{profile.get('name', 'You')} > ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() in ("back", "exit", "quit", "q", "menu"):
            break

        if user_input.lower() in ("meal", "food") or user_input.lower().startswith("meal ") or user_input.lower().startswith("food "):
            img_path = ""
            if " " in user_input:
                img_path = user_input.split(maxsplit=1)[1].strip().strip('"').strip("'")

            meals_dir = os.path.join(DATA_ROOT, "data", "meals")
            resolved_path = None
            if img_path and os.path.exists(img_path):
                resolved_path = img_path
            elif img_path and os.path.exists(os.path.join(meals_dir, img_path)):
                resolved_path = os.path.join(meals_dir, img_path)
            elif not img_path:
                # Look for newest image in data/meals/
                if os.path.exists(meals_dir):
                    valid_exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
                    imgs = [
                        os.path.join(meals_dir, f) for f in os.listdir(meals_dir)
                        if f.lower().endswith(valid_exts)
                    ]
                    if imgs:
                        imgs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                        resolved_path = imgs[0]
                        print(f"[Detected latest photo in data/meals/: {os.path.basename(resolved_path)}]")

            if resolved_path and os.path.exists(resolved_path):
                print(f"\nCoach is visually analyzing your meal plate ({os.path.basename(resolved_path)}) with Qwen-VL...")
                try:
                    import base64
                    from gym_ai.vision.meal_analyzer import analyze_meal
                    with open(resolved_path, "rb") as img_f:
                        b64 = base64.b64encode(img_f.read()).decode("utf-8")
                    meal_res = analyze_meal(image_b64_or_url=b64, profile=active_profile)
                    print(f"\n[Plate Analysis: {meal_res.get('meal_name')}]")
                    for item in meal_res.get("items", []):
                        print(f"  - {item['name']} ({item['portion_g']}g): {item['calories']} kcal | {item['protein_g']}g P | {item['carbs_g']}g C | {item['fat_g']}g F")
                    print(f"\nTotal: {meal_res.get('total_calories')} kcal | {meal_res.get('total_protein_g')}g protein | {meal_res.get('total_carbs_g')}g carbs | {meal_res.get('total_fat_g')}g fat")
                    comp = meal_res.get("target_comparison", {})
                    print(f"Target Coverage: {comp.get('meal_protein_coverage_pct')}% of daily protein ({comp.get('daily_protein_target_g')}g)")
                    print(f"\nCoach Advice: {meal_res.get('coach_feedback')}\n")
                except Exception as e:
                    print(f"[Could not analyze meal: {e}]\n")
            else:
                print(f"\n[No meal image found. Place your plate photo in '{meals_dir}' or type 'meal <path_to_image>']\n")
            continue

        if user_input.lower() in ("plan", "new plan", "generate plan"):
            print("\nCoach is creating your personalized workout and nutrition plan...")
            try:
                plan = generate_personalized_plan(profile=profile)
                print(f"\n[Coach]: {plan.get('coach_notes')}")
                print("\nTomorrow's Planned Routine:")
                for ex in plan.get("plan", []):
                    print(f"  - {ex.get('exercise_name')}: {ex.get('sets')} sets x {ex.get('reps')} reps ({ex.get('coaching_focus')})")
                rec = plan.get("nutrition_recovery", {})
                print(f"\nTarget Nutrition: {rec.get('protein_target_g')}g protein | Meal: {rec.get('recommended_meal')}\n")
            except Exception as e:
                print(f"[Could not generate plan: {e}]\n")
            continue

        print("\nCoach > ", end="", flush=True)
        try:
            stream_gen = run_pipeline(
                query=user_input,
                chat_history=chat_history,
                stream=True,
                athlete_context=athlete_context,
            )
            full_text = ""
            for chunk in stream_gen:
                sys.stdout.write(chunk)
                sys.stdout.flush()
                full_text += chunk
            print("\n")
            chat_history.append({"role": "user", "content": user_input})
            chat_history.append({"role": "assistant", "content": full_text})
            if len(chat_history) > 20:
                chat_history = chat_history[-20:]
        except Exception as e:
            print(f"\n[Coach error: {e}]\n")


def practice(name, profile):
    configure_voice(profile.get("voice_mode") or "full", profile.get("cue_gap_seconds") or 4.0, profile.get("voice_gender") or "Female")
    run_exercise(
        get_config(name),
        options={
            "voice": True,
            "prefer_full": True,
            "voice_mode": profile.get("voice_mode") or "full",
            "voice_gender": profile.get("voice_gender") or "Female",
            "cue_gap_seconds": profile.get("cue_gap_seconds") or 4.0,
        },
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="AI exercise coach.")
    parser.add_argument(
        "exercise",
        nargs="?",
        help="Practice this exercise, or 'today' for the programmed session.",
    )
    parser.add_argument("--onboard", action="store_true", help="Redo intake questions.")
    parser.add_argument(
        "--dataset",
        action="store_true",
        help="Export the user dataset for the backend/chatbot and exit.",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Open interactive Gym AI chat coach immediately.",
    )
    args = parser.parse_args(argv)

    if args.onboard:
        profile = run_onboarding()
    else:
        profile = load_or_onboard()
    configure_voice(profile.get("voice_mode") or "full", profile.get("cue_gap_seconds") or 4.0, profile.get("voice_gender") or "Female")

    if args.dataset:
        from common.user_dataset import print_dataset_summary
        print_dataset_summary()
        return

    if args.chat:
        run_chat_coach(profile)
        return

    if args.exercise:
        if args.exercise.lower() in ("today", "workout", "session"):
            run_todays_workout(profile)
            return
        name = ALIASES.get(args.exercise.lower(), args.exercise.lower())
        if name not in BASE:
            print("Unknown exercise. Try: today, squat, plank, pushup, ...")
            return
        practice(name, profile)
        return

    while True:
        choice = home_menu(profile)
        if choice in ("1", "today", "t", "w"):
            run_todays_workout(profile)
        elif choice in ("2", "practice", "p"):
            name = choose_practice()
            if name:
                practice(name, profile)
        elif choice in ("3", "report", "r"):
            print_weekly_report(weekly_report(load_history()))
        elif choice in ("4", "onboard", "o"):
            profile = run_onboarding()
        elif choice in ("5", "camera", "setup"):
            run_camera_setup(profile)
        elif choice in ("6", "voice", "time"):
            profile = edit_session_prefs(profile)
            configure_voice(profile.get("voice_mode") or "full", profile.get("cue_gap_seconds") or 4.0, profile.get("voice_gender") or "Female")
        elif choice in ("7", "bio", "biometrics", "weight", "height"):
            from common.profile import edit_biometrics
            profile = edit_biometrics(profile)
        elif choice in ("8", "dataset"):
            from common.user_dataset import print_dataset_summary
            print_dataset_summary()
        elif choice in ("9", "chat", "coach", "c"):
            run_chat_coach(profile)
        elif choice in ("q", "quit", "exit"):
            stop_voice()
            return
        else:
            print("Type 1-9, or q.")


if __name__ == "__main__":
    main()
