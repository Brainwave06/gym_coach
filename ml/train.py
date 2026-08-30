"""Train phase (counting) + multi-label error models. Split by athlete, not by row."""

from __future__ import annotations

import json
import os

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    mean_absolute_error,
)
from sklearn.multioutput import MultiOutputClassifier
from sklearn.preprocessing import LabelEncoder

from common.catalog import BASE, get_config

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GYM_DATA = os.path.join(PROJECT_ROOT, "synthetic_gym_dataset")
LEGACY_DATA = os.path.join(PROJECT_ROOT, "data", "ml")
MODEL_DIR = os.path.join(PROJECT_ROOT, "models", "form")

FEATURE_EXTRA = ("primary", "primary_vel", "primary_acc")


def resolve_data_dir():
    gym = os.path.join(GYM_DATA, "sequences.jsonl")
    legacy = os.path.join(LEGACY_DATA, "sequences.jsonl")
    if os.path.isfile(gym):
        return GYM_DATA
    if os.path.isfile(legacy):
        return LEGACY_DATA
    raise FileNotFoundError(
        "No sequences.jsonl in synthetic_gym_dataset/ or data/ml/"
    )


def _normalize_split(split):
    if all(isinstance(split.get(name), list) for name in ("train", "val", "test")):
        return {name: list(split[name]) for name in ("train", "val", "test")}
    assignment = split.get("assignment") or {}
    buckets = {"train": [], "val": [], "test": []}
    for athlete_id, name in assignment.items():
        if name in buckets:
            buckets[name].append(athlete_id)
    if not any(buckets.values()):
        raise ValueError("split.json has no train/val/test lists or assignment map")
    return buckets


def load_sequences():
    data_dir = resolve_data_dir()
    path = os.path.join(data_dir, "sequences.jsonl")
    print("Loading", path)
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    with open(os.path.join(data_dir, "split.json"), encoding="utf-8") as handle:
        split = _normalize_split(json.load(handle))
    return rows, split


def _feature_keys(exercise_id):
    cfg = get_config(exercise_id)
    return list(cfg["checks"].keys()) + list(FEATURE_EXTRA)


def frame_vector(frame, keys, primary_name=None):
    values = []
    for key in keys:
        value = frame.get(key)
        if value is None and primary_name and key == primary_name:
            value = frame.get("primary")
        values.append(0.0 if value is None else float(value))
    return np.array(values, dtype=np.float32)


def _split_rows(sequences, split):
    buckets = {"train": [], "val": [], "test": []}
    lookup = {}
    for name in ("train", "val", "test"):
        for aid in split[name]:
            lookup[aid] = name
    for seq in sequences:
        bucket = lookup.get(seq["athlete_id"], "train")
        buckets[bucket].append(seq)
    return buckets


def build_phase_xy(sequences, exercise_id):
    keys = _feature_keys(exercise_id)
    primary_name = get_config(exercise_id).get("primary_check")
    X, y = [], []
    for seq in sequences:
        if seq["exercise_id"] != exercise_id or seq.get("mode") != "reps":
            continue
        for frame in seq["frames"]:
            X.append(frame_vector(frame, keys, primary_name))
            y.append(frame.get("phase") or "up")
    return np.vstack(X) if X else np.zeros((0, len(keys))), np.array(y), keys


def build_error_xy(sequences, exercise_id):
    cfg = get_config(exercise_id)
    faults = list(cfg.get("fault_checks") or [])
    label_names = faults + ["is_good"]
    keys = _feature_keys(exercise_id)
    primary_name = cfg.get("primary_check")
    X, Y = [], []
    if cfg.get("mode") == "hold":
        for seq in sequences:
            if seq["exercise_id"] != exercise_id:
                continue
            feats = _agg_frames(seq["frames"], keys, primary_name)
            row = [int(seq["labels"].get(n, False)) for n in label_names]
            X.append(feats)
            Y.append(row)
    else:
        for seq in sequences:
            if seq["exercise_id"] != exercise_id:
                continue
            for span in seq.get("rep_spans") or []:
                chunk = seq["frames"][span["start"]:span["end"]]
                feats = _agg_frames(chunk, keys, primary_name)
                lab = span["labels"]
                row = [int(lab.get(n, False)) for n in label_names]
                X.append(feats)
                Y.append(row)
    if not X:
        return np.zeros((0, 1)), np.zeros((0, len(label_names))), keys, label_names
    return np.vstack(X), np.array(Y, dtype=int), keys, label_names


def _agg_frames(frames, keys, primary_name=None):
    if not frames:
        return np.zeros(len(keys) * 4, dtype=np.float32)
    mat = np.vstack([frame_vector(f, keys, primary_name) for f in frames])
    return np.concatenate([
        mat.mean(axis=0),
        mat.min(axis=0),
        mat.max(axis=0),
        mat.std(axis=0),
    ]).astype(np.float32)


def count_from_phases(phases, count_on="return_to_up"):
    count = 0
    seen_down = False
    prev = None
    for p in phases:
        if count_on == "reach_up":
            if p == "down":
                seen_down = True
            if seen_down and p == "up" and prev != "up":
                count += 1
                seen_down = False
        else:
            if p == "down":
                seen_down = True
            if seen_down and p == "up" and prev != "up":
                count += 1
                seen_down = False
        prev = p
    return count


def train_exercise(exercise_id, buckets):
    cfg = get_config(exercise_id)
    os.makedirs(MODEL_DIR, exist_ok=True)
    result = {"exercise_id": exercise_id, "mode": cfg.get("mode", "reps")}

    if cfg.get("mode") == "reps":
        Xtr, ytr, keys = build_phase_xy(buckets["train"], exercise_id)
        Xva, yva, _ = build_phase_xy(buckets["val"], exercise_id)
        Xte, yte, _ = build_phase_xy(buckets["test"], exercise_id)
        if len(Xtr) < 50:
            result["phase"] = {"skipped": True}
        else:
            enc = LabelEncoder()
            ytr_e = enc.fit_transform(ytr)
            clf = RandomForestClassifier(
                n_estimators=140,
                max_depth=14,
                min_samples_leaf=4,
                class_weight="balanced_subsample",
                random_state=0,
                n_jobs=-1,
            )
            clf.fit(Xtr, ytr_e)
            def eval_split(X, y):
                pred = enc.inverse_transform(clf.predict(X))
                return {
                    "accuracy": float(accuracy_score(y, pred)),
                    "macro_f1": float(f1_score(y, pred, average="macro")),
                    "report": classification_report(y, pred, zero_division=0),
                }
            phase_metrics = {
                "val": eval_split(Xva, yva) if len(Xva) else {},
                "test": eval_split(Xte, yte) if len(Xte) else {},
            }
            # counting MAE on test sequences
            true_c, pred_c = [], []
            count_on = cfg.get("count_on", "return_to_up")
            for seq in buckets["test"]:
                if seq["exercise_id"] != exercise_id:
                    continue
                primary_name = cfg.get("primary_check")
                mat = np.vstack(
                    [frame_vector(f, keys, primary_name) for f in seq["frames"]]
                )
                pred = enc.inverse_transform(clf.predict(mat))
                pred_c.append(count_from_phases(pred, count_on))
                true_c.append(int(seq.get("true_count") or 0))
            phase_metrics["count_mae_test"] = float(mean_absolute_error(true_c, pred_c)) if true_c else None
            phase_metrics["count_exact_test"] = (
                float(np.mean(np.array(true_c) == np.array(pred_c))) if true_c else None
            )
            joblib.dump(
                {"model": clf, "encoder": enc, "keys": keys, "count_on": count_on},
                os.path.join(MODEL_DIR, f"{exercise_id}_phase.joblib"),
            )
            result["phase"] = phase_metrics
            result["phase"]["n_train_frames"] = int(len(Xtr))
            result["phase"]["n_test_frames"] = int(len(Xte))

    Xtr, Ytr, keys, label_names = build_error_xy(buckets["train"], exercise_id)
    Xte, Yte, _, _ = build_error_xy(buckets["test"], exercise_id)
    Xva, Yva, _, _ = build_error_xy(buckets["val"], exercise_id)
    if len(Xtr) < 40:
        result["errors"] = {"skipped": True}
        return result

    base = RandomForestClassifier(
        n_estimators=120,
        max_depth=12,
        min_samples_leaf=3,
        random_state=0,
        n_jobs=-1,
    )
    model = MultiOutputClassifier(base)
    model.fit(Xtr, Ytr)

    def err_metrics(X, Y):
        if len(X) == 0:
            return {}
        pred = model.predict(X)
        out = {}
        for i, name in enumerate(label_names):
            out[name] = {
                "f1": float(f1_score(Y[:, i], pred[:, i], zero_division=0)),
                "support_pos": int(Y[:, i].sum()),
                "pred_pos": int(pred[:, i].sum()),
            }
        out["subset_accuracy"] = float(accuracy_score(Y, pred))
        out["macro_f1"] = float(np.mean([out[n]["f1"] for n in label_names]))
        return out

    err = {
        "val": err_metrics(Xva, Yva),
        "test": err_metrics(Xte, Yte),
        "labels": label_names,
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "test_label_rate": {
            n: float(Yte[:, i].mean()) if len(Yte) else 0.0
            for i, n in enumerate(label_names)
        },
    }
    joblib.dump(
        {"model": model, "keys": keys, "label_names": label_names, "agg": True},
        os.path.join(MODEL_DIR, f"{exercise_id}_errors.joblib"),
    )
    result["errors"] = err
    return result


def train_all():
    sequences, split = load_sequences()
    buckets = _split_rows(sequences, split)
    report = {
        "data_dir": resolve_data_dir(),
        "split": {k: len(v) for k, v in split.items() if k in ("train", "val", "test")},
        "n_sequences": len(sequences),
        "exercises": {},
    }
    for exercise_id in BASE:
        print(f"Training {exercise_id}...")
        try:
            report["exercises"][exercise_id] = train_exercise(exercise_id, buckets)
        except Exception as exc:
            report["exercises"][exercise_id] = {"error": str(exc)}
            print(f"  failed: {exc}")
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return report


if __name__ == "__main__":
    train_all()
    print("Wrote", os.path.join(MODEL_DIR, "metrics.json"))
