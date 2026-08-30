# Architecture

## Layout

```text
main.py                 terminal menu
run.bat                 tester launcher
requirements.txt
common/
  exercise_engine.py    camera loop, HUD, counting
  session_player.py     today's workout
  program.py            plan, time budget, recovery, progression use
  catalog.py            exercise configs
  warmup.py             warm-up / cooldown / recovery follow-along
  voice.py              Windows speech
  profile.py            onboarding, prefs, progression writes
  history.py            jsonl log + weekly report
  setup_wizard.py       camera check
  clips.py              last-good-rep JPEGs
  user_dataset.py       dataset export
  handoff.py            coach_handoff.json
  models.py             pose .task path / download
squat/, plank/, …       per-exercise config
data/                   local only (not packed for friends)
models/                 pose_landmarker_*.task
docs/                   this documentation
synthetic_gym_dataset/  synthetic pose JSONL + split (form ML)
models/form/            trained error/phase forests
```

## Data written at runtime

| File | Written by |
|------|------------|
| `data/profile.json` | Onboarding, prefs, progression, camera setup |
| `data/history.jsonl` | Each practice/workout |
| `data/dataset/*.jsonl` | Export / after workout |
| `data/coach_handoff.json` | After programmed workout |
| `data/clips/` | Good-rep frames |

Do not commit personal `profile.json` / `history.jsonl` if you publish the repo.

## Engine loop (short)

1. Open webcam, MediaPipe Pose Landmarker (VIDEO mode)  
2. Teach banner → setup (body visible) → calibrate thresholds  
3. Active: update reps or hold; skip counting if uncertain  
4. Buffer last ~2s of frames for worst/good clips  
5. Summary + optional clip replay; `q` stops voice  

## Packing

`pack_for_friends.ps1` copies source + `docs` + `run.bat`, **not** `venv`, pose `.task` files, or personal `data/`.
