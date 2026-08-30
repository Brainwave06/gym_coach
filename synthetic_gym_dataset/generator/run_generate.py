import json
import numpy as np
from collections import defaultdict

from config import REPS_EXERCISES, HOLD_EXERCISES, ALL_EXERCISES, CAMERA
from athletes import make_athletes, make_split, N_ATHLETES, RNG_SEED
from generator import gen_reps_session, gen_hold_session

OUT_DIR = "/home/claude/gymgen/out"
import os
os.makedirs(OUT_DIR, exist_ok=True)

def main():
    athletes = make_athletes()
    split, split_lists = make_split(athletes)
    athlete_by_id = {a["athlete_id"]: a for a in athletes}

    master_rng = np.random.default_rng(RNG_SEED + 777)

    sequences = []
    session_id = 0

    fault_counts = defaultdict(lambda: defaultdict(int))
    session_counts = defaultdict(int)
    completed_rep_counts = defaultdict(int)
    fault_rep_counts = defaultdict(int)
    two_fault_rep_counts = defaultdict(int)
    incomplete_counts = defaultdict(int)
    attempted_rep_counts = defaultdict(int)

    for athlete in athletes:
        # derive a per-athlete independent rng stream for reproducibility
        a_seed = int.from_bytes(athlete["athlete_id"].encode(), "little") % (2**32) + RNG_SEED
        a_rng = np.random.default_rng(a_seed)

        for ex in REPS_EXERCISES:
            n_sessions = int(a_rng.integers(1, 3))  # 1-2
            for s in range(n_sessions):
                sess = gen_reps_session(athlete, ex, s, a_rng)
                sess["session_id"] = f"sess_{session_id:05d}"
                session_id += 1
                sequences.append(sess)
                session_counts[ex] += 1
                completed_rep_counts[ex] += sess["true_count"]
                for rs in sess["rep_spans"]:
                    attempted_rep_counts[ex] += 1
                    if rs["labels"].get("incomplete"):
                        incomplete_counts[ex] += 1
                        continue
                    n_active = sum(
                        1 for k, v in rs["labels"].items()
                        if v and k not in ("is_good", "incomplete")
                    )
                    if n_active >= 1:
                        fault_rep_counts[ex] += 1
                    if n_active >= 2:
                        two_fault_rep_counts[ex] += 1
                    for k, v in rs["labels"].items():
                        if v:
                            fault_counts[ex][k] += 1

        for ex in HOLD_EXERCISES:
            n_sessions = int(a_rng.integers(2, 5))  # 2-4
            for s in range(n_sessions):
                sess = gen_hold_session(athlete, ex, s, a_rng)
                sess["session_id"] = f"sess_{session_id:05d}"
                session_id += 1
                sequences.append(sess)
                session_counts[ex] += 1
                for k, v in sess["labels"].items():
                    if v:
                        fault_counts[ex][k] += 1

    # write sequences.jsonl
    seq_path = os.path.join(OUT_DIR, "sequences.jsonl")
    with open(seq_path, "w", encoding="utf-8") as f:
        for sess in sequences:
            # attach split + camera for convenience at top level (not a label leak into frames)
            sess_out = dict(sess)
            sess_out["split"] = split[sess["athlete_id"]]
            sess_out["camera"] = CAMERA[sess["exercise_id"]]
            f.write(json.dumps(sess_out, ensure_ascii=False) + "\n")

    # athletes.json
    with open(os.path.join(OUT_DIR, "athletes.json"), "w", encoding="utf-8") as f:
        json.dump(athletes, f, ensure_ascii=False, indent=2)

    # split.json
    with open(os.path.join(OUT_DIR, "split.json"), "w", encoding="utf-8") as f:
        json.dump({
            "method": "by_athlete_id",
            "ratios": {"train": 0.62, "val": 0.16, "test": 0.22},
            "assignment": split,
            "ids": split_lists,
        }, f, ensure_ascii=False, indent=2)

    # manifest.json
    manifest = {
        "dataset_type": "synthetic",
        "note": "Fully synthetic pose-derived time series. No real video, no real people, "
                "no scraped footage. Not equivalent to real webcam data.",
        "n_athletes": len(athletes),
        "n_sessions_total": len(sequences),
        "exercises": ALL_EXERCISES,
        "camera_convention": CAMERA,
        "split_ratios": {"train": 0.62, "val": 0.16, "test": 0.22},
        "split_athlete_counts": {k: len(v) for k, v in split_lists.items()},
        "per_exercise": {},
    }
    for ex in ALL_EXERCISES:
        entry = {
            "sessions": session_counts[ex],
            "mode": "reps" if ex in REPS_EXERCISES else "hold",
        }
        if ex in REPS_EXERCISES:
            attempted = attempted_rep_counts[ex]
            completed = completed_rep_counts[ex]
            entry["completed_reps"] = completed
            entry["attempted_reps"] = attempted
            entry["incomplete_rate"] = round(incomplete_counts[ex] / attempted, 4) if attempted else 0
            entry["fault_rate_of_completed"] = round(fault_rep_counts[ex] / completed, 4) if completed else 0
            entry["two_fault_rate_given_fault"] = round(
                two_fault_rep_counts[ex] / fault_rep_counts[ex], 4
            ) if fault_rep_counts[ex] else 0
        entry["fault_label_true_rate"] = {
            k: round(v / (session_counts[ex] if ex in HOLD_EXERCISES else completed_rep_counts[ex]), 4)
            for k, v in fault_counts[ex].items()
        } if (session_counts[ex] if ex in HOLD_EXERCISES else completed_rep_counts[ex]) else {}
        manifest["per_exercise"][ex] = entry

    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(sequences)} sessions to {seq_path}")
    print(f"Athletes: {len(athletes)}  Train/Val/Test: "
          f"{len(split_lists['train'])}/{len(split_lists['val'])}/{len(split_lists['test'])}")


if __name__ == "__main__":
    main()
