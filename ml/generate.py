"""Synthetic pose-feature dataset: many athletes, realistic class mix, held-out bodies."""

from __future__ import annotations

import hashlib
import json
import os
import random
from dataclasses import dataclass

import numpy as np

from common.catalog import BASE, get_config

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(PROJECT_ROOT, "data", "ml")

# Gym-like fault rates (not 50/50). Beginners fault more; most reps still pass.
FAULT_RATE = {"beginner": 0.42, "intermediate": 0.27, "advanced": 0.14}
DOUBLE_FAULT_GIVEN_FAULT = {"beginner": 0.28, "intermediate": 0.16, "advanced": 0.08}
INCOMPLETE_REP_RATE = 0.06
LABEL_FLIP = 0.06  # annotation noise, like a tired coach


@dataclass
class Athlete:
    athlete_id: str
    experience: str
    height: float
    limb_ratio: float
    tempo: float
    jitter: float
    left_bias: float
    rom: float
    camera_angle_x: float
    camera_angle_y: float
    tendencies: dict


def _rng(seed):
    return np.random.default_rng(seed)


def make_athletes(n=96, seed=7):
    rng = _rng(seed)
    experiences = (
        ["beginner"] * 40 + ["intermediate"] * 36 + ["advanced"] * 20
    )
    rng.shuffle(experiences)
    athletes = []
    for i, exp in enumerate(experiences):
        athletes.append(
            Athlete(
                athlete_id=f"ath_{i:03d}",
                experience=exp,
                height=float(rng.normal(1.70, 0.11)),
                limb_ratio=float(rng.normal(1.0, 0.08)),
                tempo=float(np.clip(rng.normal(1.0, 0.18), 0.65, 1.45)),
                jitter=float(np.clip(rng.uniform(0.6, 2.4), 0.4, 3.0)),
                left_bias=float(rng.normal(0.0, 0.35)),
                rom=float(np.clip(rng.normal(1.0, 0.12), 0.75, 1.2)),
                camera_angle_x=float(rng.uniform(-0.6, 0.6)),
                camera_angle_y=float(rng.uniform(-0.3, 0.4)),
                tendencies={
                    "valgus": float(np.clip(rng.beta(2, 5), 0, 1)),
                    "lean": float(np.clip(rng.beta(2, 6), 0, 1)),
                    "heels": float(np.clip(rng.beta(1.5, 6), 0, 1)),
                    "sag": float(np.clip(rng.beta(2, 5), 0, 1)),
                    "pike": float(np.clip(rng.beta(1.8, 6), 0, 1)),
                    "swing": float(np.clip(rng.beta(2, 6), 0, 1)),
                },
            )
        )
    return athletes


def _check_names(cfg):
    return list(cfg["checks"].keys())


def _faults(cfg):
    return list(cfg.get("fault_checks") or [])


def _primary_up_down(cfg):
    primary = cfg["primary_check"]
    cdef = cfg["checks"][primary]
    up = cdef.get("up_threshold")
    down = cdef.get("down_threshold")
    mode = cfg.get("mode", "reps")
    hold_dir = cfg.get("hold_direction", "above")
    count_on = cfg.get("count_on", "return_to_up")
    return primary, down, up, mode, hold_dir, count_on


def _smooth(values, k=5):
    if len(values) < 3:
        return values
    kernel = np.ones(k) / k
    pad = k // 2
    x = np.pad(values, (pad, pad), mode="edge")
    return np.convolve(x, kernel, mode="valid")[: len(values)]


def _pick_faults(cfg, athlete, rng):
    faults = _faults(cfg)
    rate = FAULT_RATE[athlete.experience]
    if rng.random() > rate:
        return []
    weights = []
    for name in faults:
        key = "lean" if "lean" in name or "torso" in name else (
            "valgus" if "valgus" in name else (
                "heels" if "heel" in name else (
                    "sag" if "sag" in name else (
                        "pike" if "pike" in name else (
                            "swing" if "swing" in name or "flare" in name else "lean"
                        )
                    )
                )
            )
        )
        weights.append(0.15 + athlete.tendencies.get(key, 0.2))
    weights = np.array(weights, dtype=float)
    weights /= weights.sum()
    first = rng.choice(faults, p=weights)
    chosen = [first]
    if rng.random() < DOUBLE_FAULT_GIVEN_FAULT[athlete.experience] and len(faults) > 1:
        rest = [f for f in faults if f != first]
        w2 = np.array([weights[faults.index(f)] for f in rest])
        w2 /= w2.sum()
        chosen.append(rng.choice(rest, p=w2))
    return chosen


def _base_series(cfg, athlete, n_frames, rng, bottom_ok=True):
    primary, down, up, mode, hold_dir, count_on = _primary_up_down(cfg)
    names = _check_names(cfg)
    series = {n: np.zeros(n_frames) for n in names}
    up_val = 170.0 if up is None else float(up) + 12
    down_val = float(down)
    if mode == "hold":
        if hold_dir == "below":
            target = down_val - 8 * athlete.rom + rng.normal(0, 3)
        else:
            target = (up_val if up is not None else down_val + 20) + rng.normal(0, 3)
        for n in names:
            cdef = cfg["checks"][n]
            thr = float(cdef["down_threshold"])
            series[n][:] = thr + rng.normal(0, 0.04 if "ratio" in cdef["type"] or "offset" in cdef["type"] else 2.0, n_frames)
        if primary in series:
            series[primary][:] = target + rng.normal(0, athlete.jitter, n_frames)
        return series

    # Reps: half-cosine cycles. Ground-truth phase from kinematics, not engine thresholds.
    cycles = max(1, int(round(n_frames / (28 / athlete.tempo))))
    t = np.linspace(0, cycles * 2 * np.pi, n_frames)
    
    # Dynamic time warping: non-linear progression with micro-pauses
    random_walk = np.cumsum(rng.normal(0, 0.15 * athlete.jitter, n_frames))
    t_warped = t + random_walk
    t_warped = np.sort(t_warped) # Ensure time moves forward
    
    depth = 0.55 + 0.45 * athlete.rom
    if not bottom_ok:
        depth *= 0.45
    wave = (1 - np.cos(t_warped)) / 2  # 0 stand, 1 bottom
    
    # Fatigue profile based on archetype
    if athlete.experience == "beginner":
        wobble_scale = 0.15
        fatigue = np.linspace(0.2, 1.0, n_frames)
    elif athlete.experience == "intermediate":
        wobble_scale = 0.08
        fatigue = np.linspace(0.0, 0.5, n_frames)
    else:
        wobble_scale = 0.03
        fatigue = np.zeros(n_frames)
        fatigue[-int(n_frames*0.3):] = np.linspace(0, 0.6, int(n_frames*0.3))
    
    # Add high-frequency wobbles near the hardest part of the rep
    wobble = wave * rng.normal(0, wobble_scale * athlete.jitter, n_frames) * (1 + fatigue)
    wave = np.clip(wave + wobble, 0.0, 1.0)
    
    if count_on == "reach_up":
        wave = 1 - wave  # start down, peak is lockout
        
    prim = up_val - depth * (up_val - (down_val - 12)) * wave
    
    # Use cam_offset just for slight visual variation, but dialed back since math is 2D
    cam_offset = athlete.camera_angle_x * 2.0 + athlete.camera_angle_y * 1.5

    prim = prim + rng.normal(0, athlete.jitter, n_frames) + cam_offset
    series[primary] = prim
    for n in names:
        if n == primary:
            continue
        cdef = cfg["checks"][n]
        thr = float(cdef["down_threshold"])
        typ = cdef["type"]
        scale = 0.03 if ("ratio" in typ or "offset" in typ) else 6.0
        # correlated with depth so faults can appear near the hard part of the rep
        series[n] = thr * 0.4 + (wave * 0.5 + rng.normal(0.15, 0.08)) * scale * 0.2
        if "angle" in typ or typ in ("min_angle", "max_angle", "vertical_angle"):
            series[n] = thr + (0.5 - wave) * 18 + rng.normal(0, athlete.jitter, n_frames) + cam_offset * 1.5
        else:
            # Perspective distortion for ratios
            ratio_cam = (athlete.camera_angle_x * 0.2)
            series[n] = (wave * 0.12 + rng.normal(0, 0.02, n_frames)) * athlete.limb_ratio + ratio_cam
    return series


def _apply_faults(series, cfg, faults, rng, athlete):
    n = len(next(iter(series.values())))
    
    if athlete.experience == "beginner":
        mid = slice(int(n * 0.10), int(n * 0.90))
    elif athlete.experience == "intermediate":
        mid = slice(int(n * 0.25), int(n * 0.85))
    else:
        mid = slice(int(n * 0.40), int(n * 0.70))
        
    for name in faults:
        cdef = cfg["checks"][name]
        thr = float(cdef["down_threshold"])
        direction = cdef.get("direction", "below")
        typ = cdef["type"]
        mag = rng.uniform(1.15, 1.85)
        if direction == "above":
            bump = abs(thr) * (mag if ("ratio" in typ or "offset" in typ) else mag * 8)
            series[name][mid] = np.maximum(series[name][mid], thr + bump / 4) + rng.normal(0, 0.01, mid.stop - mid.start)
            if "angle" in typ or typ in ("min_angle", "max_angle", "vertical_angle"):
                series[name][mid] = thr + rng.uniform(4, 18) + rng.normal(0, athlete.jitter, mid.stop - mid.start)
        else:
            if "angle" in typ or typ in ("min_angle", "max_angle", "vertical_angle"):
                series[name][mid] = thr - rng.uniform(4, 16) + rng.normal(0, athlete.jitter, mid.stop - mid.start)
            else:
                series[name][mid] = thr - abs(thr) * rng.uniform(0.2, 0.8)
    return series


def _phase_labels(primary, cfg, n_frames):
    _, down, up, mode, hold_dir, count_on = _primary_up_down(cfg)
    labels = np.array(["hold"] * n_frames if mode == "hold" else ["up"] * n_frames, dtype=object)
    if mode == "hold":
        return labels
    vel = np.gradient(primary)
    if count_on == "reach_up":
        going_up = vel > 0.4
        going_down = vel < -0.4
        high = primary > (float(up) if up is not None else float(down) + 20)
        labels[:] = "down"
        labels[going_up] = "transition"
        labels[high] = "up"
    else:
        going_down = vel < -0.35
        going_up = vel > 0.35
        low = primary < float(down) + 8
        labels[:] = "up"
        labels[going_down | low] = "down"
        labels[going_up & ~low] = "transition"
    return labels


def _maybe_flip(labels, rng):
    out = dict(labels)
    for k, v in list(out.items()):
        if k in ("incomplete",):
            continue
        if rng.random() < LABEL_FLIP:
            out[k] = not v
    if out.get("is_good") and any(out.get(f) for f in out if f not in ("is_good", "incomplete")):
        out["is_good"] = False
    return out


def generate_rep(cfg, athlete, rng, incomplete=False):
    tempo_frames = int(rng.integers(22, 48) / athlete.tempo)
    n = max(18, tempo_frames)
    faults = [] if incomplete else _pick_faults(cfg, athlete, rng)
    series = _base_series(cfg, athlete, n, rng, bottom_ok=not incomplete)
    if faults:
        series = _apply_faults(series, cfg, faults, rng, athlete)
    for k in series:
        series[k] = _smooth(series[k], 5)
    primary = series[cfg["primary_check"]]
    phases = _phase_labels(primary, cfg, n)
    fault_set = set(faults)
    labels = {f: (f in fault_set) for f in _faults(cfg)}
    depth_ok = not incomplete
    if cfg.get("mode") == "reps" and not incomplete:
        pdef = cfg["checks"][cfg["primary_check"]]
        if cfg.get("count_on") == "reach_up":
            depth_ok = float(np.max(primary)) >= float(pdef.get("up_threshold") or pdef["down_threshold"])
        else:
            depth_ok = float(np.min(primary)) <= float(pdef["down_threshold"]) + 6
    labels["is_good"] = bool(depth_ok and not fault_set and not incomplete)
    labels["incomplete"] = bool(incomplete)
    if not depth_ok:
        labels["is_good"] = False
    labels = _maybe_flip(labels, rng)
    if incomplete:
        labels["is_good"] = False
        labels["incomplete"] = True
    frames = []
    names = _check_names(cfg)
    vel = np.gradient(primary)
    acc = np.gradient(vel)
    for i in range(n):
        row = {n: float(series[n][i]) for n in names}
        row["primary"] = float(primary[i])
        row["primary_vel"] = float(vel[i])
        row["primary_acc"] = float(acc[i])
        row["phase"] = str(phases[i])
        frames.append(row)
    return {
        "frames": frames,
        "labels": labels,
        "n_frames": n,
        "true_rep": 0 if incomplete else 1,
    }


def generate_hold(cfg, athlete, rng):
    n = int(rng.integers(40, 90))
    faults = _pick_faults(cfg, athlete, rng)
    series = _base_series(cfg, athlete, n, rng, bottom_ok=True)
    if faults:
        series = _apply_faults(series, cfg, faults, rng, athlete)
    for k in series:
        series[k] = _smooth(series[k], 7)
    primary = series[cfg["primary_check"]]
    vel = np.gradient(primary)
    acc = np.gradient(vel)
    names = _check_names(cfg)
    frames = []
    for i in range(n):
        row = {n: float(series[n][i]) for n in names}
        row["primary"] = float(primary[i])
        row["primary_vel"] = float(vel[i])
        row["primary_acc"] = float(acc[i])
        row["phase"] = "hold"
        frames.append(row)
    labels = {f: (f in faults) for f in _faults(cfg)}
    labels["is_good"] = not bool(faults)
    labels["incomplete"] = False
    labels = _maybe_flip(labels, rng)
    return {"frames": frames, "labels": labels, "n_frames": n, "true_rep": 0}


def generate_sequence(exercise_id, athlete, rng):
    cfg = get_config(exercise_id)
    if cfg.get("mode") == "hold":
        item = generate_hold(cfg, athlete, rng)
        item.update({
            "exercise_id": exercise_id,
            "athlete_id": athlete.athlete_id,
            "experience": athlete.experience,
            "mode": "hold",
        })
        return item

    n_reps = int(rng.integers(4, 11))
    reps = []
    true_count = 0
    for _ in range(n_reps):
        incomplete = rng.random() < INCOMPLETE_REP_RATE
        rep = generate_rep(cfg, athlete, rng, incomplete=incomplete)
        true_count += rep["true_rep"]
        reps.append(rep)
    # stitch frames with short rest
    frames = []
    rep_spans = []
    for rep in reps:
        start = len(frames)
        frames.extend(rep["frames"])
        rest = int(rng.integers(3, 8))
        last = frames[-1]
        for _ in range(rest):
            rest_row = dict(last)
            rest_row["primary_vel"] = 0.0
            rest_row["primary_acc"] = 0.0
            rest_row["phase"] = "up" if cfg.get("count_on") != "reach_up" else "down"
            frames.append(rest_row)
        rep_spans.append({
            "start": start,
            "end": start + rep["n_frames"],
            "labels": rep["labels"],
            "true_rep": rep["true_rep"],
        })
    return {
        "exercise_id": exercise_id,
        "athlete_id": athlete.athlete_id,
        "experience": athlete.experience,
        "mode": "reps",
        "frames": frames,
        "rep_spans": rep_spans,
        "true_count": true_count,
        "labels": {},
    }


def export_dataset(n_athletes=72, seed=11):
    os.makedirs(OUT_DIR, exist_ok=True)
    athletes = make_athletes(n_athletes, seed)
    ids = [a.athlete_id for a in athletes]
    rng_split = _rng(seed + 99)
    rng_split.shuffle(ids)
    n_test = max(16, int(0.22 * len(ids)))
    n_val = max(12, int(0.16 * len(ids)))
    test_ids = set(ids[:n_test])
    val_ids = set(ids[n_test:n_test + n_val])
    train_ids = set(ids[n_test + n_val:])

    exercises = list(BASE.keys())
    sequences = []
    for athlete in athletes:
        arng = _rng(seed + int(hashlib.md5(athlete.athlete_id.encode()).hexdigest()[:8], 16))
        for ex in exercises:
            n_seq = 2
            for _ in range(n_seq):
                sequences.append(generate_sequence(ex, athlete, arng))

    path = os.path.join(OUT_DIR, "sequences.jsonl")
    with open(path, "w", encoding="utf-8") as handle:
        for seq in sequences:
            handle.write(json.dumps(seq) + "\n")

    split = {
        "train": sorted(train_ids),
        "val": sorted(val_ids),
        "test": sorted(test_ids),
        "n_sequences": len(sequences),
        "n_athletes": len(athletes),
        "notes": (
            "Split is by athlete_id so test bodies never appear in training. "
            "Fault rates follow gym-like imbalance. Features are pose checks only "
            "(no sex, injury, or experience as model inputs)."
        ),
    }
    with open(os.path.join(OUT_DIR, "split.json"), "w", encoding="utf-8") as handle:
        json.dump(split, handle, indent=2)
    meta = {
        "athletes": [
            {
                "athlete_id": a.athlete_id,
                "experience": a.experience,
                "height": round(a.height, 3),
                "tempo": round(a.tempo, 3),
            }
            for a in athletes
        ]
    }
    with open(os.path.join(OUT_DIR, "athletes.json"), "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2)
    return split, path


if __name__ == "__main__":
    split, path = export_dataset()
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in split.items()}, indent=2))
    print(path)
