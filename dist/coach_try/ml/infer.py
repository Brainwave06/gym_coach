"""Load trained form models. Falls back to None if files are missing."""

from __future__ import annotations

import os

import numpy as np

try:
    import joblib
except ImportError:
    joblib = None

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJECT_ROOT, "models", "form")

_CACHE = {}


def _path(exercise_id, kind):
    return os.path.join(MODEL_DIR, f"{exercise_id}_{kind}.joblib")


def load_bundle(exercise_id, kind):
    key = (exercise_id, kind)
    if key in _CACHE:
        return _CACHE[key]
    if joblib is None:
        return None
    path = _path(exercise_id, kind)
    if not os.path.exists(path):
        _CACHE[key] = None
        return None
    bundle = joblib.load(path)
    _CACHE[key] = bundle
    return bundle


def _vec(values, keys):
    return np.array([float(values.get(k) or 0.0) for k in keys], dtype=np.float32)


def predict_phase(exercise_id, frame_values):
    bundle = load_bundle(exercise_id, "phase")
    if not bundle:
        return None, 0.0
    x = _vec(frame_values, bundle["keys"]).reshape(1, -1)
    proba = bundle["model"].predict_proba(x)
    idx = int(np.argmax(proba[0]))
    label = bundle["encoder"].inverse_transform([idx])[0]
    conf = float(proba[0][idx])
    return label, conf


def classify_rep(exercise_id, frame_list):
    """frame_list: list of dicts with check names + primary/vel/acc."""
    bundle = load_bundle(exercise_id, "errors")
    if not bundle or not frame_list:
        return None
    keys = bundle["keys"]
    mat = np.vstack([_vec(f, keys) for f in frame_list])
    feats = np.concatenate([mat.mean(0), mat.min(0), mat.max(0), mat.std(0)]).reshape(1, -1)
    pred = bundle["model"].predict(feats)[0]
    names = bundle["label_names"]
    out = {n: bool(pred[i]) for i, n in enumerate(names)}
    try:
        probas = bundle["model"].predict_proba(feats)
        confs = []
        for i, p in enumerate(probas):
            # each output is (n, 2) or (n, 1)
            arr = np.asarray(p)
            if arr.ndim == 2 and arr.shape[1] == 2:
                confs.append(float(arr[0, int(pred[i])]))
            else:
                confs.append(float(np.max(arr[0])))
        out["_confidence"] = float(np.mean(confs)) if confs else 0.5
    except Exception:
        out["_confidence"] = 0.55
    return out


def ml_available(exercise_id):
    return load_bundle(exercise_id, "errors") is not None
