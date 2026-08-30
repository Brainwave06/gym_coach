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

## What this product is

A Windows Python app. Terminal menu + OpenCV camera window. No Flutter UI in this repo.

## What this product is not (yet)

- Mobile app
- REST API
- Chatbot
- Diet engine

Those should **read** `data/dataset/` and `data/coach_handoff.json`. They must not override a `pain` feel or a `form_fade` stop.
