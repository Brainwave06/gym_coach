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
    print()
    print(f"AI Exercise Coach  —  hi {profile.get('name', '')}")
    print(f"  Streak: {streak} day" + ("" if streak == 1 else "s"))
    print(f"  Time: {profile.get('time_budget_min', 25)} min   Voice: {profile.get('voice_mode', 'full')}")
    print("  1) Today's workout   (warm-up, prescribed sets, cooldown)")
    print("  2) Practice one exercise")
    print("  3) Weekly report")
    print("  4) Redo onboarding")
    print("  5) Camera setup")
    print("  6) Voice and session time")
    print("  7) Export user dataset")
    print("  q) Quit")
    return input("Choose: ").strip().lower()


def practice(name, profile):
    configure_voice(profile.get("voice_mode") or "full", profile.get("cue_gap_seconds") or 4.0)
    run_exercise(
        get_config(name),
        options={
            "voice": True,
            "prefer_full": True,
            "voice_mode": profile.get("voice_mode") or "full",
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
    args = parser.parse_args(argv)

    if args.onboard:
        profile = run_onboarding()
    else:
        profile = load_or_onboard()
    configure_voice(profile.get("voice_mode") or "full", profile.get("cue_gap_seconds") or 4.0)

    if args.dataset:
        from common.user_dataset import print_dataset_summary
        print_dataset_summary()
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
            configure_voice(profile.get("voice_mode") or "full", profile.get("cue_gap_seconds") or 4.0)
        elif choice in ("7", "dataset"):
            from common.user_dataset import print_dataset_summary
            print_dataset_summary()
        elif choice in ("q", "quit", "exit"):
            stop_voice()
            return
        else:
            print("Type 1-7, or q.")


if __name__ == "__main__":
    main()
