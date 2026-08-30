import numpy as np
from config import EXERCISES, CAMERA

EXPERIENCE_FAULT_PROB = {"beginner": 0.42, "intermediate": 0.27, "advanced": 0.14}
EXPERIENCE_SECOND_FAULT = {"beginner": (0.18, 0.28), "intermediate": (0.12, 0.20), "advanced": (0.08, 0.14)}
INCOMPLETE_RATE = 0.06
LABEL_FLIP_RANGE = (0.05, 0.08)

FPS_CHOICES_REPS = [18, 20, 24]
FPS_CHOICES_HOLD = [15, 18, 20, 25]

# (exercise_id, feature_name) -> (degrees_scale, sign). sign=-1 means the fault
# *reduces* the angle from its straight/neutral baseline (e.g. a bent knee).
ANGLE_FAULT_OVERRIDE = {
    ("squat", "torso_lean"): (12, 1), ("box_squat", "torso_lean"): (10, 1),
    ("lunge", "torso_lean"): (8, 1), ("biceps_curl", "torso_lean"): (8, 1),
    ("wall_sit", "torso_lean"): (8, 1),
    ("pushup", "knee"): (30, -1), ("plank", "knee"): (30, -1),
    ("glute_bridge", "knee"): (25, -1),
}
DEFAULT_ANGLE_FAULT_SCALE = 10.0
RATIO_FAULT_SCALE = 0.30


def fault_bump_params(exercise_id, name, kind):
    if kind == "ratio":
        return RATIO_FAULT_SCALE, 1
    return ANGLE_FAULT_OVERRIDE.get((exercise_id, name), (DEFAULT_ANGLE_FAULT_SCALE, 1))


def fault_weights(faults, rng):
    """Assign popularity weights so some faults stay rarer than others."""
    w = np.ones(len(faults))
    # make every 3rd fault (by list position) rarer, deterministic-ish but seeded
    for i in range(len(faults)):
        if i % 3 == 2:
            w[i] = 0.45
    w = w * rng.uniform(0.8, 1.2, size=len(faults))
    return w / w.sum()


def moving_average(x, window):
    if window <= 1:
        return x
    kernel = np.ones(window) / window
    pad = window // 2
    xp = np.pad(x, (pad, pad), mode="edge")
    out = np.convolve(xp, kernel, mode="valid")
    return out[: len(x)]


def apply_dropout(mat, dropout_rate, rng):
    """mat: (n_frames, n_features). Repeat previous frame's values at dropped indices."""
    n = mat.shape[0]
    if n < 2:
        return mat
    drop_idx = np.where(rng.random(n) < dropout_rate)[0]
    drop_idx = drop_idx[drop_idx > 0]
    out = mat.copy()
    for i in drop_idx:
        out[i] = out[i - 1]
    return out


def bump_shape(progress, peak=0.85, width=0.35):
    """Bell-shaped bump peaking near the hard part of the rep (progress in [0,1])."""
    return np.exp(-0.5 * ((progress - peak) / width) ** 2)


def choose_faults(exercise_faults, experience, rng, severity_scale):
    """Decide which faults (if any) apply, biasing toward the athlete's experience level
    and using a latent-severity draw rather than a fixed clone threshold."""
    p_any = EXPERIENCE_FAULT_PROB[experience]
    chosen = []
    if rng.random() < p_any and len(exercise_faults) > 0:
        w = fault_weights(exercise_faults, rng)
        first = rng.choice(exercise_faults, p=w)
        chosen.append(first)
        lo, hi = EXPERIENCE_SECOND_FAULT[experience]
        p_second = rng.uniform(lo, hi)
        remaining = [f for f in exercise_faults if f != first]
        if remaining and rng.random() < p_second:
            w2 = fault_weights(remaining, rng)
            second = rng.choice(remaining, p=w2)
            chosen.append(second)
    severities = {}
    for f in chosen:
        latent = rng.uniform(0.5, 1.1) * np.clip(severity_scale, 0.7, 1.4)
        severities[f] = float(np.clip(latent, 0.3, 1.5))
    return severities


def flip_labels(labels, rng):
    p = rng.uniform(*LABEL_FLIP_RANGE)
    out = {}
    for k, v in labels.items():
        if rng.random() < p:
            out[k] = (not v)
        else:
            out[k] = v
    return out


def gen_rep_progress_track(n_frames, direction_sign, rest_val, hard_val, dwell=False):
    """direction_sign: +1 means progress rises from rest->hard (0->1); the caller maps
    progress to actual values via rest+progress*(hard-rest)."""
    n_down = int(n_frames * 0.5)
    n_up = n_frames - n_down
    if dwell:
        dwell_n = max(1, int(n_frames * 0.12))
        n_down = max(2, n_down - dwell_n // 2)
        n_up = max(2, n_frames - n_down - dwell_n)
    t_down = np.linspace(0, 1, n_down)
    prog_down = 0.5 - 0.5 * np.cos(np.pi * t_down)  # ease in/out, 0->1
    if dwell:
        prog_dwell = np.ones(dwell_n)
        t_up = np.linspace(0, 1, n_up)
        prog_up = 1 - (0.5 - 0.5 * np.cos(np.pi * t_up))
        prog = np.concatenate([prog_down, prog_dwell, prog_up])
    else:
        t_up = np.linspace(0, 1, n_up)
        prog_up = 1 - (0.5 - 0.5 * np.cos(np.pi * t_up))
        prog = np.concatenate([prog_down, prog_up])
    return prog


def gen_reps_session(athlete, exercise_id, session_idx, rng):
    cfg = EXERCISES[exercise_id]
    fps = int(rng.choice(FPS_CHOICES_REPS))
    tempo_scale = {"slow": 1.5, "normal": 1.0, "fast": 0.7}[athlete["tempo"]]
    rom_scale = {"stiff": 0.75, "normal": 1.0, "mobile": 1.08}[athlete["rom"]]

    n_completed = int(rng.integers(4, 11))
    n_incomplete = int(rng.binomial(n_completed, INCOMPLETE_RATE / (1 - INCOMPLETE_RATE) + 0.005))
    rep_plan = [True] * n_completed + [False] * n_incomplete
    rng.shuffle(rep_plan)  # True = completed, False = incomplete

    faults_list = cfg["faults"]
    rest_phase = cfg["rest_phase"]
    dwell = cfg.get("dwell_at_hard", False)

    # per-athlete small idiosyncratic offsets on rest/hard angles
    athlete_off = rng.normal(0, 2.0)

    all_frames = []
    rep_spans = []
    frame_cursor = 0

    def rest_segment(n):
        nonlocal frame_cursor
        for _ in range(n):
            all_frames.append({"progress": 0.0, "phase": rest_phase, "fault_active": {}})
        frame_cursor += n

    # small leading rest
    rest_segment(int(fps * rng.uniform(0.2, 0.5)))

    for completed in rep_plan:
        base_dur = fps * rng.uniform(1.0, 1.6) * tempo_scale
        n_frames_rep = max(6, int(base_dur))
        if not completed:
            # incomplete: only partially approach the hard part, then bail back to rest
            max_progress = rng.uniform(0.25, 0.7)
            n_down = int(n_frames_rep * 0.55)
            n_up = n_frames_rep - n_down
            t_down = np.linspace(0, 1, n_down)
            prog_down = max_progress * (0.5 - 0.5 * np.cos(np.pi * t_down))
            t_up = np.linspace(0, 1, n_up)
            prog_up = max_progress * (1 - (0.5 - 0.5 * np.cos(np.pi * t_up)))
            prog = np.concatenate([prog_down, prog_up])
            fault_active = {}
            labels_raw = {f: False for f in faults_list}
            labels_raw["is_good"] = False
            labels_raw["incomplete"] = True
        else:
            prog = gen_rep_progress_track(n_frames_rep, +1, 0, 1, dwell=dwell)
            severities = choose_faults(faults_list, athlete["experience"], rng, athlete["severity_scale"])
            fault_active = severities
            labels_raw = {f: (f in severities) for f in faults_list}
            labels_raw["is_good"] = (len(severities) == 0)
            labels_raw["incomplete"] = False

        start_idx = frame_cursor
        for j, p in enumerate(prog):
            if rest_phase == "up":
                # rising progress (toward hard part) => phase "down"; falling => "up"
                going_toward_hard = j < len(prog) / 2
                ph = "down" if going_toward_hard else "up"
            else:
                going_toward_hard = j < len(prog) / 2
                ph = "up" if going_toward_hard else "down"
            if p > 0.93 and completed:
                ph = "transition"
            all_frames.append({"progress": float(p), "phase": ph, "fault_active": fault_active})
        frame_cursor += len(prog)
        end_idx = frame_cursor - 1

        if completed:
            labels_final = flip_labels(labels_raw, rng)
            rep_spans.append({
                "start": start_idx, "end": end_idx, "true_rep": 1,
                "labels": labels_final,
            })
        else:
            labels_final = flip_labels(labels_raw, rng)
            rep_spans.append({
                "start": start_idx, "end": end_idx, "true_rep": 0,
                "labels": labels_final,
            })

        # small rest between reps
        rest_n = int(fps * rng.uniform(0.1, 0.35))
        rest_segment(rest_n)

    n_frames_total = len(all_frames)

    # --- build primary series ---
    rest_angle = cfg["rest_angle"] + athlete_off
    hard_angle = cfg["rest_angle"] + (cfg["hard_angle"] - cfg["rest_angle"]) * rom_scale + athlete_off * 0.3
    primary_vals = np.array([
        rest_angle + f["progress"] * (hard_angle - rest_angle) for f in all_frames
    ])

    series_vals = {}
    for name, spec in cfg["series"].items():
        if spec["kind"] == "angle":
            rest_v = spec["rest"] + rng.normal(0, 1.5)
            hard_v = spec["rest"] + (spec["hard"] - spec["rest"]) * rom_scale + rng.normal(0, 1.5)
            base = np.array([rest_v + f["progress"] * (hard_v - rest_v) for f in all_frames])
            scale, sign = fault_bump_params(exercise_id, name, "angle")
            bump = np.zeros(n_frames_total)
            for i, f in enumerate(all_frames):
                if name in f["fault_active"]:
                    sev = f["fault_active"][name]
                    bump[i] = sign * sev * scale * bump_shape(f["progress"])
            base = base + bump
        else:  # ratio
            base_level = spec["base"] * rng.uniform(0.5, 1.3) + abs(athlete["left_bias"]) * 0.5
            base = np.full(n_frames_total, base_level)
            # add fault bump keyed to this feature name
            scale, sign = fault_bump_params(exercise_id, name, "ratio")
            bump = np.zeros(n_frames_total)
            for i, f in enumerate(all_frames):
                if name in f["fault_active"]:
                    sev = f["fault_active"][name]
                    bump[i] = sign * sev * scale * bump_shape(f["progress"])
            base = np.clip(base + bump, -0.4, 0.6)
        series_vals[name] = base

    # smoothing
    window = int(rng.integers(3, 8))
    primary_vals = moving_average(primary_vals, window)
    for name in series_vals:
        series_vals[name] = moving_average(series_vals[name], window)

    # jitter
    jscale = athlete["jitter_scale"]
    primary_vals = primary_vals + rng.normal(0, 1.0 * jscale, n_frames_total)
    for name, spec in cfg["series"].items():
        std = 1.0 * jscale if spec["kind"] == "angle" else 0.012 * jscale
        series_vals[name] = series_vals[name] + rng.normal(0, std, n_frames_total)

    # stack into matrix for dropout (hold-last-value on missing frames)
    names = list(cfg["series"].keys())
    mat = np.column_stack([primary_vals] + [series_vals[n] for n in names])
    mat = apply_dropout(mat, athlete["dropout_rate"], rng)
    primary_vals = mat[:, 0]
    for i, n in enumerate(names):
        series_vals[n] = mat[:, i + 1]

    # derivatives (computed post-dropout, reflecting stale-frame flat velocity)
    primary_vel = np.gradient(primary_vals) * fps
    primary_acc = np.gradient(primary_vel) * fps

    frames_out = []
    for i, f in enumerate(all_frames):
        rec = {}
        for n in names:
            rec[n] = round(float(series_vals[n][i]), 3)
        rec["primary"] = round(float(primary_vals[i]), 3)
        rec["primary_vel"] = round(float(primary_vel[i]), 3)
        rec["primary_acc"] = round(float(primary_acc[i]), 3)
        rec["phase"] = f["phase"]
        frames_out.append(rec)

    session = {
        "exercise_id": exercise_id,
        "athlete_id": athlete["athlete_id"],
        "experience": athlete["experience"],
        "mode": "reps",
        "fps": fps,
        "true_count": n_completed,
        "frames": frames_out,
        "rep_spans": rep_spans,
    }
    return session


def gen_hold_session(athlete, exercise_id, session_idx, rng):
    cfg = EXERCISES[exercise_id]
    fps = int(rng.choice(FPS_CHOICES_HOLD))
    duration = rng.uniform(2.0, 5.0)
    n_frames = max(int(fps * duration), 10)

    faults_list = cfg["faults"]
    severities = choose_faults(faults_list, athlete["experience"], rng, athlete["severity_scale"])
    labels_raw = {f: (f in severities) for f in faults_list}
    labels_raw["is_good"] = (len(severities) == 0)

    # primary series: mostly stable around a rest value, with slow wander + fault drift
    if cfg.get("primary_kind") == "ratio":
        base_level = cfg["primary_base"] * rng.uniform(0.5, 1.3)
    else:
        base_level = cfg["primary_rest"] + rng.normal(0, 2.0)
    t = np.linspace(0, 1, n_frames)
    slow_wander = 0.5 * np.sin(2 * np.pi * t * rng.uniform(0.3, 0.8) + rng.uniform(0, 6.28))
    primary_vals = np.full(n_frames, base_level) + slow_wander * (1.0 if cfg.get("primary_kind") != "ratio" else 0.01)

    series_vals = {}
    for name, spec in cfg["series"].items():
        if spec["kind"] == "angle":
            base = np.full(n_frames, spec["rest"] + rng.normal(0, 2.0))
            base = base + 0.6 * np.sin(2 * np.pi * t * rng.uniform(0.2, 0.6) + rng.uniform(0, 6.28))
        else:
            base_level = spec["base"] * rng.uniform(0.5, 1.3) + abs(athlete["left_bias"]) * 0.5
            base = np.full(n_frames, base_level)
        # sustained fault contribution: ramps in over first ~20% then holds, with slow variation
        if name in severities:
            sev = severities[name]
            scale, sign = fault_bump_params(exercise_id, name, spec["kind"])
            ramp = np.clip(t / 0.2, 0, 1)
            wobble = 1 + 0.15 * np.sin(2 * np.pi * t * rng.uniform(0.3, 0.7))
            base = base + sign * sev * scale * ramp * wobble
        if spec["kind"] == "ratio":
            base = np.clip(base, -0.4, 0.6)
        series_vals[name] = base

    # primary fault contribution if the primary itself carries a fault name match (e.g. plank body_line isn't a fault key but is primary)
    window = int(rng.integers(3, 8))
    primary_vals = moving_average(primary_vals, window)
    for name in series_vals:
        series_vals[name] = moving_average(series_vals[name], window)

    jscale = athlete["jitter_scale"]
    primary_std = 0.02 * jscale if cfg.get("primary_kind") == "ratio" else 0.8 * jscale
    primary_vals = primary_vals + rng.normal(0, primary_std, n_frames)
    for name, spec in cfg["series"].items():
        std = 0.8 * jscale if spec["kind"] == "angle" else 0.01 * jscale
        series_vals[name] = series_vals[name] + rng.normal(0, std, n_frames)

    names = list(cfg["series"].keys())
    mat = np.column_stack([primary_vals] + [series_vals[n] for n in names])
    mat = apply_dropout(mat, athlete["dropout_rate"], rng)
    primary_vals = mat[:, 0]
    for i, n in enumerate(names):
        series_vals[n] = mat[:, i + 1]

    primary_vel = np.gradient(primary_vals) * fps
    primary_acc = np.gradient(primary_vel) * fps

    frames_out = []
    for i in range(n_frames):
        rec = {}
        for n in names:
            rec[n] = round(float(series_vals[n][i]), 3)
        rec["primary"] = round(float(primary_vals[i]), 3)
        rec["primary_vel"] = round(float(primary_vel[i]), 3)
        rec["primary_acc"] = round(float(primary_acc[i]), 3)
        rec["phase"] = "hold"
        frames_out.append(rec)

    labels_final = flip_labels(labels_raw, rng)

    session = {
        "exercise_id": exercise_id,
        "athlete_id": athlete["athlete_id"],
        "experience": athlete["experience"],
        "mode": "hold",
        "fps": fps,
        "true_count": 0,
        "frames": frames_out,
        "labels": labels_final,
    }
    return session
