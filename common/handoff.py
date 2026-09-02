"""Snapshot the CV coach can hand to a chatbot / Flutter backend later."""

import json
import os
from datetime import datetime

from common.history import load_history, side_imbalance, weekly_report
from common.profile import save_profile

from common.paths import DATA_ROOT
HANDOFF_PATH = os.path.join(DATA_ROOT, "data", "coach_handoff.json")


def write_handoff(profile, extra=None):
    history = load_history()
    payload = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "desktop_cv_coach",
        "athlete": {
            "name": profile.get("name"),
            "goal": profile.get("goal"),
            "experience": profile.get("experience"),
            "injuries": profile.get("injuries") or [],
            "equipment": profile.get("equipment"),
            "time_budget_min": profile.get("time_budget_min"),
            "voice_mode": profile.get("voice_mode"),
        },
        "progression": profile.get("progression") or {},
        "camera_setup": profile.get("camera_setup"),
        "weekly": weekly_report(history),
        "imbalance": side_imbalance(history),
        "notes_for_chatbot": (
            "Computer vision owns form, reps, and live cues. "
            "Use this snapshot to suggest diet or a complementary plan. "
            "Do not override a pain flag or a form_fade stop."
        ),
    }
    if extra:
        payload.update(extra)
    os.makedirs(os.path.dirname(HANDOFF_PATH), exist_ok=True)
    with open(HANDOFF_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    save_profile(profile)
    try:
        from common.user_dataset import export_dataset
        export_dataset(include_demo=True)
    except OSError:
        pass
    return HANDOFF_PATH
