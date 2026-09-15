# Docs

This folder is the product spec for the **desktop CV coach**. The Flutter app, backend, and chatbot are built by teammates; this repo owns live form, reps, and the user dataset they can consume later.

## Read in this order

1. [getting-started.md](getting-started.md) — run it, pack a zip for testers
2. [features.md](features.md) — full feature list
3. [exercises.md](exercises.md) — movements and camera angle
4. [controls.md](controls.md) — keys during a set
5. [dataset.md](dataset.md) — `data/dataset/` for backend/chatbot
6. [for-teammates.md](for-teammates.md) — how CV connects later (no wiring yet)
7. [architecture.md](architecture.md) — files and data paths
8. [ml-report.md](ml-report.md) — form models trained on `synthetic_gym_dataset/`
9. [data-generation-prompt.md](data-generation-prompt.md) — how to get more data without filming people

## Project Architecture & Modules

1. **Computer Vision Coach**: 12 compound and isolation exercises with live MediaPipe pose tracking, rep counting, and form correction.
2. **Gym AI Coach & RAG**: Personalized sports nutrition advice, workout generation, proactive post-workout debriefs, and conversational memory.
3. **Multimodal Vision**: Plate photo food analysis using Qwen-VL with calorie and macronutrient breakdown.
4. **FastAPI Backend**: Complete REST and WebSocket API (`api.py` / `backend/main.py`) with universal CORS, JWT auth, athlete biometrics, and workout sync.
5. **Mobile & Web Frontend (`frontend/`)**: Cross-platform Flutter application with live camera streaming, chat, and dashboard.
