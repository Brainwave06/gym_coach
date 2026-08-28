"""Last-good-rep clips on disk (also readable later by a backend/chatbot)."""

import glob
import os

import cv2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIPS_DIR = os.path.join(PROJECT_ROOT, "data", "clips")


def clip_dir(exercise_id, kind="good"):
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(exercise_id))
    return os.path.join(CLIPS_DIR, f"{safe}_{kind}")


def save_clip(frames, exercise_id, kind="good"):
    if not frames:
        return None
    folder = clip_dir(exercise_id, kind)
    os.makedirs(folder, exist_ok=True)
    for old in glob.glob(os.path.join(folder, "frame_*.jpg")):
        try:
            os.remove(old)
        except OSError:
            pass
    saved = 0
    step = max(1, len(frames) // 24)
    for i, frame in enumerate(frames[::step][:24]):
        path = os.path.join(folder, f"frame_{i:03d}.jpg")
        if cv2.imwrite(path, frame):
            saved += 1
    return folder if saved else None


def load_clip(exercise_id, kind="good"):
    folder = clip_dir(exercise_id, kind)
    paths = sorted(glob.glob(os.path.join(folder, "frame_*.jpg")))
    frames = []
    for path in paths:
        img = cv2.imread(path)
        if img is not None:
            frames.append(img)
    return frames
