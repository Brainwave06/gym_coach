# Getting started

## What you need

- Windows 10/11
- Python **3.10, 3.11, or 3.12** ([python.org](https://www.python.org/downloads/) — tick **Add python.exe to PATH**)
- A webcam
- Internet on the **first** launch (packages + pose model)

## Run on this machine (developers)

From the project folder, with the existing venv:

```powershell
cd D:\claude_code
.\venv\Scripts\python.exe main.py
```

Or activate the venv and run `python main.py`.

### Useful commands

| Command | What it does |
|---------|----------------|
| `python main.py` | Terminal home menu |
| `python main.py today` | Skip menu, start today's workout |
| `python main.py squat` | Practice squat (also: plank, pushup, lunge, …) |
| `python main.py --onboard` | Redo intake questions |
| `python main.py --dataset` | Rebuild `data/dataset/` and exit |

## First-time onboarding

The first launch asks:

- Name
- Goal (strength / fat loss / general health)
- Experience (beginner / intermediate / advanced)
- Injuries (`knees`, `back`, `shoulders`, or none)
- Equipment (floor only / dumbbells)
- Session length (15 / 25 / 40 minutes)
- Voice (full / quiet / text only)

Saved to `data/profile.json`.

## Home menu

```
1) Today's workout
2) Practice one exercise
3) Weekly report
4) Redo onboarding
5) Camera setup
6) Voice and session time
7) Export user dataset
q) Quit
```

## Run as a tester (friends)

Do **not** send the whole folder (`venv` is large and often broken on another PC).

1. On your PC, double-click `pack_for_friends.bat` (or run `pack_for_friends.ps1`).
2. Send `dist\AI_Exercise_Coach_YYYYMMDD.zip`.
3. They unzip and **double-click `run.bat`**.
4. First run creates a local `venv`, installs `requirements.txt`, downloads the pose model into `models/`.

`run.bat` is the only launcher testers need.

## Pose model

If `models/pose_landmarker_full.task` (or lite) is missing, the app downloads it from Google's MediaPipe storage on first use.

## Camera

- Good light, full body in frame
- Use menu **5** once to check light, distance, and front vs side
- Sideways for most lifts; squat faces the camera (see [exercises.md](exercises.md))

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| `Python was not found` | Install 3.11, add to PATH, reopen the terminal |
| Camera does not open | Close Zoom/Teams, try another USB camera |
| Pose never locks | Step back, brighter room, menu **5** |
| Packages fail to install | Python 3.13 may not work; use 3.11 |
| Speech overlapping | Menu **6** → Quiet or Text only |
| `q` does not quit | Click the camera window first, then press `q` |
