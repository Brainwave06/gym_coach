# For teammates (Flutter, backend, chatbot)

This repo is the **computer-vision coach**. You do not need to run MediaPipe in Flutter.

## Split of responsibility

| Layer | Owns |
|-------|------|
| This desktop app | Webcam, pose, form cues, reps/holds, local profile, dataset export |
| Flutter | Mobile UX, login, showing plans the backend returns |
| Backend | Users, auth, storing dataset/handoff if you upload it |
| Chatbot | Diet + written workout *suggestions* from user JSON |

## What you can use today (no live camera link)

1. Copy `data/dataset/*.jsonl` + `manifest.json` into your backend seed or fixtures.
2. Treat `user_id` as the athlete key.
3. Chatbot prompt context: `users.jsonl` profile + last few `sessions.jsonl` blocks + `form_cues.jsonl`.
4. After a real session on the desktop, also read `data/coach_handoff.json`.

## What to build later (not in this repo)

- Upload handoff/dataset from the PC (or a shared folder) to the API  
- Map `user_id` to the Flutter account  
- Chatbot tool: “given this CV snapshot, suggest dinner + tomorrow's accessories”  
- Do **not** let the bot override pain / form_fade  

## Demo users in the dataset

| `user_id` | Name | Notes |
|-----------|------|--------|
| `usr_demo_lina` | Lina Hassan | Beginner, knees, fat loss, 15 min |
| `usr_demo_omar` | Omar Farid | Intermediate, dumbbells, strength |
| `usr_demo_sara` | Sara Nabil | Shoulders, health, recovery session |
| `usr_demo_karim` | Karim Adel | Advanced, back, one `feel: pain` lunge |

The live machine user has `synthetic: false` and a generated `usr_…` id in `data/profile.json`.

## How testers run the CV coach

See [getting-started.md](getting-started.md). Zip + `run.bat`. Webcam required.
