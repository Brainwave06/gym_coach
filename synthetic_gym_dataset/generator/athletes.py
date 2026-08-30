import numpy as np

N_ATHLETES = 100
RNG_SEED = 20260830

def make_athletes(n=N_ATHLETES, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    athletes = []
    exp_choices = rng.choice(
        ["beginner", "intermediate", "advanced"], size=n, p=[0.40, 0.35, 0.25]
    )
    for i in range(n):
        aid = f"ath_{i:03d}"
        height = float(np.clip(rng.normal(170, 9), 148, 202))
        limb_ratio = float(np.clip(rng.normal(1.0, 0.06), 0.85, 1.15))
        hip_width = float(np.clip(rng.normal(1.0, 0.08), 0.8, 1.25))
        shoulder_width = float(np.clip(rng.normal(1.0, 0.08), 0.8, 1.25))
        left_bias = float(np.clip(rng.normal(0.0, 0.03), -0.09, 0.09))
        tempo = str(rng.choice(["slow", "normal", "fast"], p=[0.25, 0.5, 0.25]))
        rom = str(rng.choice(["stiff", "normal", "mobile"], p=[0.25, 0.5, 0.25]))
        # per-athlete fault-severity scaling ("tolerance") -- independent of experience
        severity_scale = float(np.clip(rng.normal(1.0, 0.25), 0.5, 1.8))
        jitter_scale = float(np.clip(rng.normal(1.0, 0.3), 0.5, 2.0))
        dropout_rate = float(np.clip(rng.normal(0.03, 0.015), 0.0, 0.08))
        athletes.append({
            "athlete_id": aid,
            "height_cm": round(height, 1),
            "limb_ratio": round(limb_ratio, 3),
            "hip_width": round(hip_width, 3),
            "shoulder_width": round(shoulder_width, 3),
            "left_bias": round(left_bias, 4),
            "tempo": tempo,
            "rom": rom,
            "experience": str(exp_choices[i]),
            "severity_scale": round(severity_scale, 3),
            "jitter_scale": round(jitter_scale, 3),
            "dropout_rate": round(dropout_rate, 4),
        })
    return athletes


def make_split(athletes, seed=RNG_SEED + 1, train=0.62, val=0.16):
    rng = np.random.default_rng(seed)
    ids = [a["athlete_id"] for a in athletes]
    idx = np.arange(len(ids))
    rng.shuffle(idx)
    n = len(ids)
    n_train = int(round(n * train))
    n_val = int(round(n * val))
    train_ids = [ids[i] for i in idx[:n_train]]
    val_ids = [ids[i] for i in idx[n_train:n_train + n_val]]
    test_ids = [ids[i] for i in idx[n_train + n_val:]]
    split = {}
    for aid in train_ids:
        split[aid] = "train"
    for aid in val_ids:
        split[aid] = "val"
    for aid in test_ids:
        split[aid] = "test"
    return split, {"train": train_ids, "val": val_ids, "test": test_ids}
