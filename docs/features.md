# Features

Everything below is implemented in this desktop coach.

## Session flow

- **Today's workout** — 4-week rotating 3-day plan, then warm-up, prescribed sets, optional cooldown
- **Practice** — one movement, no full plan
- **Recovery / mobility (~12 min)** — offered if you already trained in the last day or form faded
- **Time budget** — 15 / 25 / 40 minutes trims sets, drops blocks, and may skip cooldown
- **Teach + setup + 2.5s calibrate** before counting
- **Rest between sets** (space skips rest)
- **Pain check in the terminal** after each programmed exercise: `p` pain / `h` hard / `e` easy / `s` skip

## Live coaching (camera)

- MediaPipe pose skeleton on the video
- Rep counting or hold timers
- Form cues (depth, sag, heels, knees, etc.)
- **Does not count** when pose confidence is low (“I'm not sure”)
- **ML form helper** (optional) — error labels from `models/form/` if present; counting stays rule-based. See [ml-report.md](ml-report.md).
- **Form fade** — stops the set if the last reps are mostly bad
- **Tempo** — cues a slower eccentric if the lowering is too fast
- **Last good rep** — saved under `data/clips/` and replayed before the next set of that move
- **Rough-rep clip** — ~2s buffer replayed after a bad set
- **L/R labels** on bilateral moves; extra set if one side lags

## Voice

- Windows SAPI (PowerShell)
- **Full** — normal cues
- **Quiet** — fewer spoken lines (longer gap)
- **Text only** — prints `[coach] …`, no speech
- `q` kills speech immediately

## Warm-up and cooldown

- Camera on the left, follow-along stick figure on the right
- Warm-up: march, arm circles, hip openers (~90s)
- Cooldown: easy march, shoulder rolls, breathe (~60s)
- Recovery day: longer easy mobility follow-along, then light holds
- **Space** skips the current drill (new press only; holding space does not skip twice)
- **q** aborts

## Programming intelligence

- Beginner regressions: squat → box squat, push-up → knee push-up
- Injuries block unsafe moves (knees / back / shoulders)
- No dumbbells → biceps curl is skipped
- **Auto-progression** — after pain / hard / easy, next session's sets, reps, hold, and variant are stored on the profile
- Goal is stored for teammates (diet/plan); this app does not yet change the 3-day template by goal

## Camera setup wizard

Menu **5**: brightness, how much of the frame you fill, front vs side. Press **s** to save on the profile.

## History and reports

- `data/history.jsonl` — every practice and workout
- Weekly report: streak, good-rep rate, top cues, imbalance note
- Streak on the home menu

## Dataset and handoff (for the rest of the team)

- `data/dataset/` — users / sessions / form cues (JSONL). See [dataset.md](dataset.md)
- `data/coach_handoff.json` — last snapshot after a programmed workout
- Four **synthetic** demo athletes ship in the dataset so backend/chatbot can test without your camera
- Menu **7** or `python main.py --dataset` rebuilds the files

## Sharing a try-build

- `run.bat` — testers' launcher
- `pack_for_friends.bat` — zip without `venv` or personal history
