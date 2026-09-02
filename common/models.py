import os
import urllib.request

from common.paths import ASSET_ROOT

MODELS_DIR = os.path.join(ASSET_ROOT, "models")

FULL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)
LITE_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)


def _candidates():
    names = (
        "pose_landmarker_full.task",
        "pose_landmarker_heavy.task",
        "pose_landmarker_lite.task",
    )
    roots = (MODELS_DIR, ASSET_ROOT, os.path.join(ASSET_ROOT, "squat"), os.getcwd())
    paths = []
    for root in roots:
        for name in names:
            paths.append(os.path.join(root, name))
            paths.append(os.path.join(root, "models", name))
    return paths


def _download(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"Downloading pose model to {dest} ...")
    urllib.request.urlretrieve(url, dest)
    return dest


def resolve_model_path(prefer_full=True):
    existing = [path for path in _candidates() if os.path.exists(path)]
    if prefer_full:
        for path in existing:
            if "full" in os.path.basename(path) or "heavy" in os.path.basename(path):
                return path
    if existing:
        return existing[0]

    full_dest = os.path.join(MODELS_DIR, "pose_landmarker_full.task")
    lite_dest = os.path.join(MODELS_DIR, "pose_landmarker_lite.task")
    if prefer_full:
        try:
            return _download(FULL_URL, full_dest)
        except Exception as exc:
            print(f"Could not download full model ({exc}). Trying lite.")
    try:
        return _download(LITE_URL, lite_dest)
    except Exception:
        return lite_dest
