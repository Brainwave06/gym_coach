# Getting started

## What you need

- Windows 10/11
- Python **3.10, 3.11, or 3.12** ([python.org](https://www.python.org/downloads/) — tick **Add python.exe to PATH**)
- A webcam
- Internet on **first** launch (packages + pose model)

## Fastest path (for testers)

1. Unzip `AI_Exercise_Coach_YYYYMMDD.zip` (see [07-share-with-friends.md](07-share-with-friends.md)).
2. Double-click **`run.bat`**.
3. Wait for `pip` and the pose model download.
4. Answer onboarding in the **terminal** (name, goal, injuries, time, voice).
5. Type **`1`** for today’s workout or **`2`** to practice one move.

Keep the **terminal** and the **camera window** both visible. Menus are typed in the terminal; form is in the camera window.

## Developers (this repo)

From `d:\claude_code` (or wherever you cloned):

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Useful launches:

```bat
python main.py
python main.py today
python main.py squat
python main.py --dataset
python main.py --onboard
```

## First-run checklist

1. **Camera setup** (menu `5`) — light, distance, full body. Press `s` to save.
2. **Voice and time** (menu `6`) — 15 / 25 / 40 minutes; full / quiet / text-only voice.
3. Stand far enough that **ankles and head** are in frame.
4. **Front** for squats (face the camera). **Side** for plank, push-up, lunge, etc.

## If it fails

| Problem | What to try |
|---|---|
| `Python was not found` | Reinstall Python, enable PATH, open a **new** terminal |
| Camera never opens | Close Zoom/Teams; try another USB cam; Windows camera privacy on |
| Model missing | First run needs internet; files land in `models/pose_landmarker_*.task` |
| Voice talks over itself | Menu `6` → Quiet or Text only |
| Pose never locks | Better light, step back, follow the on-screen view hint |

## Project layout (short)

```
main.py                 terminal home
run.bat                 one-click for friends
common/                 engine, plan, voice, dataset
squat/ plank/ ...       per-exercise configs
models/                 pose .task (downloaded)
data/                   profile, history, clips, dataset
docs/                   this folder
```
