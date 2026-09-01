import time

import cv2
import numpy as np

from common.catalog import get_config
from common.exercise_engine import run_exercise
from common.handoff import write_handoff
from common.history import append_session, load_history, print_weekly_report, weekly_report
from common.profile import save_profile, update_progression
from common.program import should_suggest_recovery, today_plan
from common.voice import configure_voice, speak, stop_voice
from common.warmup import run_cooldown, run_recovery, run_warmup


def _banner_window(title, lines, seconds, keys_hint="space skip   q abort"):
    end = time.time() + seconds
    while time.time() < end:
        left = max(0, end - time.time())
        frame = np.zeros((420, 860, 3), dtype=np.uint8)
        cv2.putText(frame, title, (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        y = 140
        for line in lines:
            cv2.putText(frame, line[:70], (40, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 1)
            y += 36
        cv2.putText(frame, f"{left:.0f}s    {keys_hint}", (40, 380),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        cv2.imshow("Coach", frame)
        key = cv2.waitKey(100) & 0xFF
        if key == ord(" "):
            break
        if key == ord("q"):
            stop_voice()
            try:
                cv2.destroyWindow("Coach")
            except cv2.error:
                pass
            return False
    try:
        cv2.destroyWindow("Coach")
    except cv2.error:
        pass
    return True


def _pain_check(name):
    print()
    print(f"After {name}: any pain, or just hard?")
    print("  p) Pain — we will regress next time")
    print("  h) Hard but OK")
    print("  e) Easy")
    print("  s) Skip this question")
    while True:
        choice = input("p / h / e / s: ").strip().lower()
        if choice in ("p", "h", "e", "s"):
            return {"p": "pain", "h": "hard", "e": "easy", "s": "skip"}[choice]
        if choice in ("q", "quit"):
            return "quit"
        print("Type p, h, e, s, or q.")


def _block_quality(record):
    reps = float(record.get("reps") or 0)
    good = float(record.get("good_reps") or 0)
    if reps > 0:
        return good / reps
    hold = float(record.get("hold_time") or 0)
    good_hold = float(record.get("good_time") or 0)
    if hold > 0:
        return good_hold / hold
    return None


def _voice_options(profile):
    return {
        "voice": True,
        "voice_mode": profile.get("voice_mode") or "full",
        "voice_gender": profile.get("voice_gender") or "Female",
        "cue_gap_seconds": profile.get("cue_gap_seconds") or 4.0,
        "prefer_full": True,
    }


def run_todays_workout(profile):
    configure_voice(profile.get("voice_mode") or "full", profile.get("cue_gap_seconds") or 4.0, profile.get("voice_gender") or "Female")
    recovery = False
    suggest, reason = should_suggest_recovery()
    if suggest:
        print()
        print(reason)
        print("  y) 12-minute recovery / mobility")
        print("  n) Regular workout")
        pick = input("Choose y/n: ").strip().lower()
        recovery = pick in ("y", "yes")

    plan = today_plan(profile, recovery=recovery)
    speak(
        f"{profile.get('name', 'Athlete')}, today is {plan['name']}. Let's go.",
        force=True,
    )
    print()
    print(plan["name"])
    if plan.get("time_budget_min"):
        print(f"  Time budget: {plan['time_budget_min']} min")
    imb = plan.get("imbalance") or {}
    if imb.get("note"):
        print(f"  {imb['note']}")
    for block in plan["blocks"]:
        cfg = get_config(block["exercise_id"])
        extra = f"{block['sets']}x{block['reps']}" if cfg["mode"] == "reps" else f"hold {block['hold']}s"
        emphasis = f"  extra {block['emphasis']} side" if block.get("emphasis") else ""
        print(f"  - {cfg['display_name']}  {extra}{emphasis}")
    print()

    if recovery:
        if not run_recovery():
            stop_voice()
            return None
    else:
        if not run_warmup(scale=plan.get("warmup_scale") or 1.0):
            stop_voice()
            return None

    blocks_out = []
    aborted = False
    for index, block in enumerate(plan["blocks"], start=1):
        cfg = get_config(block["exercise_id"])
        teach = cfg.get("teach") or cfg.get("setup_hint", "")
        if block.get("emphasis"):
            teach = f"{teach} Extra attention on the {block['emphasis']} side."
        speak(f"Next, {cfg['display_name']}. {teach}", force=True)
        if not _banner_window(
            f"{index}/{len(plan['blocks'])}  {cfg['display_name']}",
            [teach, "Watch the skeleton. One cue at a time. I stay quiet if I'm unsure."],
            8,
        ):
            stop_voice()
            aborted = True
            break

        target_reps = block["sets"] * block["reps"] if cfg.get("mode") == "reps" else 0
        options = {
            "teach": teach,
            "teach_seconds": 5,
            "target_reps": target_reps,
            "target_sets": block["sets"],
            "set_size": block["reps"],
            "rest_seconds": block["rest"],
            "target_hold": block["hold"] if cfg.get("mode") == "hold" else 0,
            "auto_finish": True,
            "wait_summary": False,
            "save_history": False,
            "replay_worst": True,
        }
        options.update(_voice_options(profile))
        record = run_exercise(cfg, options=options)
        if record is None or record.get("ended_reason") == "quit":
            stop_voice()
            aborted = True
            break
        record["exercise_id"] = block["exercise_id"]
        record["target_reps"] = target_reps
        record["target_hold"] = block["hold"]
        feel = _pain_check(cfg["display_name"])
        if feel == "quit":
            stop_voice()
            aborted = True
            break
        record["feel"] = feel
        record.pop("worst_clip", None)
        record.pop("good_clip", None)
        if record["feel"] == "pain":
            speak("We stop that pattern. No pushing through sharp pain.", force=True)
        update_progression(
            profile,
            block["exercise_id"],
            feel,
            _block_quality(record),
            record.get("ended_reason"),
            block["sets"],
            block["reps"],
            block["hold"],
            variant=block["exercise_id"],
        )
        blocks_out.append(record)

    if not aborted and plan.get("include_cooldown", True):
        if run_cooldown():
            speak("That's the session. Nice work.", force=True)
        else:
            stop_voice()
    elif not aborted:
        speak("That's the session. Nice work.", force=True)

    workout = {
        "kind": "recovery" if recovery else "workout",
        "plan": plan["name"],
        "week": plan["week"],
        "day": plan["day"],
        "athlete": profile.get("name"),
        "time_budget_min": plan.get("time_budget_min"),
        "blocks": blocks_out,
        "aborted": aborted,
    }
    try:
        append_session(workout)
    except OSError as exc:
        print(f"Could not save workout: {exc}")
    save_profile(profile)
    try:
        path = write_handoff(profile, extra={"last_session": {
            "kind": workout["kind"],
            "plan": workout["plan"],
            "aborted": aborted,
        }})
        print(f"Chatbot snapshot: {path}")
    except OSError as exc:
        print(f"Could not write coach handoff: {exc}")

    print()
    print("=== Workout summary ===")
    for block in blocks_out:
        if block.get("mode") == "hold":
            print(f"{block.get('exercise')}: {block.get('hold_time')}s hold, feel={block.get('feel')}")
        else:
            print(
                f"{block.get('exercise')}: {block.get('good_reps')}/{block.get('reps')} good"
                f"  feel={block.get('feel')}  {block.get('ended_reason') or ''}"
            )
    print_weekly_report(weekly_report(load_history()))
    return workout
