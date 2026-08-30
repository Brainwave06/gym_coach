import json
import numpy as np
from collections import defaultdict
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, accuracy_score

from config import REPS_EXERCISES, HOLD_EXERCISES, EXERCISES

DATA_PATH = "../sequences.jsonl"

PHASE_CLASSES = ["up", "down", "transition"]


def load_sessions():
    sessions = []
    with open(DATA_PATH, encoding="utf-8") as f:
        for line in f:
            sessions.append(json.loads(line))
    return sessions


# ---------------------------------------------------------------------------
# Frame-level phase classification (features are NOT allowed to include the
# literal 'phase' string label itself -- only kinematic signals).
# ---------------------------------------------------------------------------

def frame_features_for_phase(frame, series_names):
    feats = [frame["primary"], frame["primary_vel"], frame["primary_acc"]]
    for n in series_names:
        feats.append(frame[n])
    return feats


def run_phase_and_counting(sessions):
    results = {}
    for ex in REPS_EXERCISES:
        cfg = EXERCISES[ex]
        series_names = list(cfg["series"].keys())
        ex_sessions = [s for s in sessions if s["exercise_id"] == ex]

        X_train, y_train = [], []
        X_test, y_test = [], []
        test_sessions = []
        for s in ex_sessions:
            X = [frame_features_for_phase(f, series_names) for f in s["frames"]]
            y = [f["phase"] for f in s["frames"]]
            if s["split"] == "train":
                X_train.extend(X)
                y_train.extend(y)
            elif s["split"] == "test":
                X_test.extend(X)
                y_test.extend(y)
                test_sessions.append(s)

        if not X_train or not X_test:
            continue

        clf = RandomForestClassifier(n_estimators=150, max_depth=10, random_state=0, n_jobs=-1)
        clf.fit(np.array(X_train), y_train)

        # frame-level phase accuracy on test
        y_pred_flat = clf.predict(np.array(X_test))
        phase_acc = accuracy_score(y_test, y_pred_flat)

        # per-session counting from predicted phase sequence:
        # a completed rep = a 'transition' segment bounded by down-phase before
        # and up-phase after (mirrors how the data was generated).
        abs_errors = []
        exact = 0
        cursor = 0
        for s in test_sessions:
            n = len(s["frames"])
            X_s = np.array([frame_features_for_phase(f, series_names) for f in s["frames"]])
            pred_phases = clf.predict(X_s)
            # direction-agnostic: a completed rep = a 'transition' segment that is
            # entered from one direction (up or down) and exited via the *other*
            # direction (mirrors reaching the hard part and coming back out).
            count = 0
            in_transition = False
            entry_phase = None
            for p in pred_phases:
                if p in ("up", "down") and not in_transition:
                    entry_phase = p
                if p == "transition" and not in_transition and entry_phase is not None:
                    in_transition = True
                if p != "transition" and in_transition:
                    if p in ("up", "down") and p != entry_phase:
                        count += 1
                    in_transition = False
                    entry_phase = p if p in ("up", "down") else None
            true_count = s["true_count"]
            abs_errors.append(abs(count - true_count))
            if count == true_count:
                exact += 1

        results[ex] = {
            "phase_frame_accuracy": round(float(phase_acc), 4),
            "count_mae": round(float(np.mean(abs_errors)), 4),
            "count_exact_pct": round(100.0 * exact / len(test_sessions), 2),
            "n_test_sessions": len(test_sessions),
        }
    return results


# ---------------------------------------------------------------------------
# Fault / is_good / incomplete classification (rep-level for reps exercises,
# session-level for hold exercises), using summary statistics of the frame
# series over the relevant span -- never the labels themselves.
# ---------------------------------------------------------------------------

def summarize_span(frames, series_names):
    arr = {n: np.array([f[n] for f in frames]) for n in series_names + ["primary", "primary_vel", "primary_acc"]}
    feats = []
    for n, v in arr.items():
        feats.extend([v.max(), v.min(), v.mean(), v.std(), v[-1] - v[0]])
    feats.append(len(frames))
    return feats


def run_fault_classification(sessions):
    results = {}
    for ex in REPS_EXERCISES + HOLD_EXERCISES:
        cfg = EXERCISES[ex]
        series_names = list(cfg["series"].keys())
        ex_sessions = [s for s in sessions if s["exercise_id"] == ex]

        train_X, train_Y = [], defaultdict(list)
        test_X, test_Y = [], defaultdict(list)

        if ex in REPS_EXERCISES:
            label_keys = cfg["faults"] + ["is_good", "incomplete"]
            for s in ex_sessions:
                for rs in s["rep_spans"]:
                    frames = s["frames"][rs["start"]: rs["end"] + 1]
                    feats = summarize_span(frames, series_names)
                    target = "train_X" if s["split"] == "train" else ("test_X" if s["split"] == "test" else None)
                    if target == "train_X":
                        train_X.append(feats)
                        for k in label_keys:
                            train_Y[k].append(int(rs["labels"][k]))
                    elif target == "test_X":
                        test_X.append(feats)
                        for k in label_keys:
                            test_Y[k].append(int(rs["labels"][k]))
        else:
            label_keys = cfg["faults"] + ["is_good"]
            for s in ex_sessions:
                feats = summarize_span(s["frames"], series_names)
                target = "train_X" if s["split"] == "train" else ("test_X" if s["split"] == "test" else None)
                if target == "train_X":
                    train_X.append(feats)
                    for k in label_keys:
                        train_Y[k].append(int(s["labels"][k]))
                elif target == "test_X":
                    test_X.append(feats)
                    for k in label_keys:
                        test_Y[k].append(int(s["labels"][k]))

        if not train_X or not test_X:
            continue
        train_X = np.array(train_X)
        test_X = np.array(test_X)

        ex_result = {}
        for k in label_keys:
            y_tr = np.array(train_Y[k])
            y_te = np.array(test_Y[k])
            if len(set(y_tr)) < 2:
                continue  # degenerate, skip
            clf = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=0,
                                          class_weight="balanced_subsample", n_jobs=-1)
            clf.fit(train_X, y_tr)
            y_pred = clf.predict(test_X)
            f1 = f1_score(y_te, y_pred, zero_division=0)
            ex_result[k] = {"f1": round(float(f1), 4), "support_pos_test": int(y_te.sum()), "n_test": int(len(y_te))}
        results[ex] = ex_result
    return results


def macro_f1(fault_dict):
    vals = [v["f1"] for k, v in fault_dict.items() if k not in ("is_good", "incomplete")]
    return float(np.mean(vals)) if vals else None


def main():
    sessions = load_sessions()

    print("=" * 70)
    print("PHASE ACCURACY + COUNTING (test athletes only)")
    print("=" * 70)
    phase_results = run_phase_and_counting(sessions)
    for ex, r in phase_results.items():
        verdict = "OK" if r["count_mae"] < 0.5 else "COUNTING FAILED (phase acc high but count MAE >= 0.5)"
        print(f"{ex:14s} phase_acc={r['phase_frame_accuracy']:.4f}  count_MAE={r['count_mae']:.4f}  "
              f"exact%={r['count_exact_pct']:.1f}  n={r['n_test_sessions']:4d}  -> {verdict}")

    print()
    print("=" * 70)
    print("PER-FAULT F1 (test athletes only)")
    print("=" * 70)
    fault_results = run_fault_classification(sessions)
    for ex, res in fault_results.items():
        print(f"\n{ex}:")
        for k, v in res.items():
            print(f"  {k:20s} F1={v['f1']:.3f}  (pos={v['support_pos_test']}/{v['n_test']})")
        mf1 = macro_f1(res)
        if mf1 is not None:
            tag = ""
            if ex in ("squat", "pushup"):
                tag = "  -> NOT PRODUCTION-READY (macro-F1 < 0.75)" if mf1 < 0.75 else "  -> production-ready threshold met"
            print(f"  MACRO-F1 (faults only) = {mf1:.3f}{tag}")

    out = {
        "phase_and_counting": phase_results,
        "fault_classification": {ex: res for ex, res in fault_results.items()},
        "macro_f1_faults": {ex: macro_f1(res) for ex, res in fault_results.items()},
    }
    with open("../eval_report.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
