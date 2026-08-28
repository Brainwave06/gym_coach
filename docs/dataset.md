# User dataset

Built for the **backend**, **Flutter app**, and **chatbot**. Schema version: **1.0.0**.

## Rebuild

```text
python main.py --dataset
```

Or home menu **7**. Also rebuilt after a programmed workout (with `coach_handoff.json`).

## Files (`data/dataset/`)

| File | One row is |
|------|------------|
| `users.jsonl` | An athlete (profile + weekly stats) |
| `sessions.jsonl` | A workout, practice, or recovery |
| `form_cues.jsonl` | A coaching cue with a count |
| `manifest.json` | Counts and field names |

Join: `users.user_id` = `sessions.user_id` = `form_cues.user_id`.

## User row (important fields)

```json
{
  "user_id": "usr_…",
  "display_name": "Abdelrahman Atef",
  "synthetic": false,
  "profile": {
    "goal": "strength",
    "experience": "beginner",
    "injuries": ["back"],
    "equipment": "floor",
    "time_budget_min": 25,
    "voice_mode": "full"
  },
  "stats": { "streak": 1, "quality": 0.31, "reps": 70, "good_reps": 22 },
  "imbalance": { "weak_side": null, "note": "…" },
  "progression": {},
  "notes_for_chatbot": "Use profile.goal and injuries…"
}
```

- `synthetic: false` — real person on this PC  
- `synthetic: true` — demo athletes (Lina, Omar, Sara, Karim) for tests  

## Session row

```json
{
  "session_id": "ses_…",
  "user_id": "usr_…",
  "kind": "workout",
  "saved_at": "2026-08-28T20:34:17",
  "plan": "Week 1 Day 1",
  "aborted": false,
  "blocks": [
    {
      "exercise_id": "squat",
      "reps": 8,
      "good_reps": 0,
      "feel": "hard",
      "ended_reason": "target",
      "top_cues": [{ "cue": "Chest collapsing…", "count": 5 }]
    }
  ]
}
```

`kind` is `workout` | `practice` | `recovery`.

## Rules for the chatbot

1. Suggest diet / accessory plan from `profile.goal`, `injuries`, `equipment`, `time_budget_min`.
2. If any block has `"feel": "pain"` or `"ended_reason": "form_fade"`, **do not** prescribe more load on that pattern.
3. Live form, reps, and “was that a good squat?” stay with this CV coach.
4. Computer vision is **not** connected to the chatbot yet. Plan the API later; today you only read these files.

## Related files

| Path | Role |
|------|------|
| `data/profile.json` | Local athlete on this PC |
| `data/history.jsonl` | Raw log (source of the dataset) |
| `data/coach_handoff.json` | Latest snapshot after a session |
| `data/clips/<id>_good/` | JPEG frames of the last good rep (not in JSONL) |
