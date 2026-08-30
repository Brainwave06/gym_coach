# ML form models — stage report

**Verdict: error helper improved on the new gym set; counting is still not the live source of truth.**

Live coaching still **counts with pose rules**. ML can override the *error message* when confidence is high. Do not present these scores as real-webcam performance.

## What we trained on

The teammate dump in `synthetic_gym_dataset/` (not the older `data/ml/` generator):

| Piece | Location |
|-------|----------|
| Sessions | `synthetic_gym_dataset/sequences.jsonl` — **2,196** sessions, **100** athletes |
| Split | `synthetic_gym_dataset/split.json` — **62 / 16 / 22** athletes (train / val / test) |
| Manifest | `synthetic_gym_dataset/manifest.json` (`dataset_type: synthetic`) |
| Their baseline eval | `synthetic_gym_dataset/eval_report.json` |
| Our models | `models/form/*_phase.joblib`, `*_errors.joblib`, `metrics.json` |
| Live hook | `common/exercise_engine.py` |
| Retrain | `python -m ml.run_pipeline` (uses the gym folder if present) |

Frames are joint angles / offsets only. Sex, injury, and experience are **not** model inputs. The generator omitted the named primary joint on some moves (`knee` / `elbow`) and stored it as `primary`; training copies `primary` into that catalog key so live MediaPipe frames still match.

## Counting (our phase → rep heuristic, held-out athletes)

Frame-phase accuracy is high (~0.95–0.97). That does **not** mean counting works. Our live-style counter (`down` then return to `up`) on **test athletes**:

| Exercise | Count MAE | Exact match |
|----------|-----------|-------------|
| squat | **4.05** | **0%** |
| box_squat | 0.96 | 46% |
| pushup | 0.54 | 63% |
| knee_pushup | 0.59 | 68% |
| lunge | 1.66 | 31% |
| glute_bridge | 3.30 | 23% |
| biceps_curl | 0.79 | 59% |

**Failed** as a drop-in counter (spec: MAE ≥ 0.5 on a move → counting failed). Squat/bridge fail hardest because this generator marks a long `transition` at the hard part of the rep; their `eval_report.json` used a different “transition segment” counter and reported near-zero MAE. That number is **not** what the coach uses.

## Error classification (test, our models)

Macro-F1 includes `is_good` plus each catalog fault (not `incomplete`).

| Exercise | Macro-F1 | Subset acc. | Notes |
|----------|----------|-------------|--------|
| dead_bug | 0.995 | 0.99 | Tiny label set |
| bird_dog | 0.981 | 0.97 | Sag + is_good |
| plank | 0.960 | 0.86 | Holds; rare sag/pike still few positives |
| biceps_curl | 0.953 | 0.92 | Lean / swing |
| glute_bridge | 0.944 | 0.91 | |
| wall_sit | 0.938 | 0.96 | |
| lunge | 0.932 | 0.88 | |
| knee_pushup | 0.884 | 0.85 | |
| squat | 0.822 | 0.82 | Heel lift / torso lean weaker |
| box_squat | 0.785 | 0.65 | Valgus F1 ~0.52 |
| pushup | 0.667 | 0.84 | `hip_pike` F1 0; sag/head_drop ~0.5 |

Spec bar was **0.75 macro-F1 on squat and push-up**. Squat clears it; **push-up does not**. Rare faults stay rare (e.g. squat heel-lift ~6% of test spans) — do not treat 1.0 F1 on a hold with 5 positives as production-ready.

Their `eval_report.json` used span-summary features similar to ours and reported squat/push-up fault macros 0.84 / 0.79. Close on squat; our push-up run is weaker on pike/sag.

## Label caveats in the dump

Some completed-rep rows have **faults true and `is_good` true** (annotator-noise / generator bug). The model can learn that inconsistency. Still fully **synthetic** — high F1 can mean “learned this generator.”

## Live product behavior

1. If `models/form/<exercise>_errors.joblib` exists, the session sets `use_ml`.
2. After a counted rep (and periodically on holds), ML proposes faults.
3. If mean confidence ≥ 0.52, that message can replace the rule message.
4. **Rep counting stays rule-based.**

## What would make it trustworthy

1. Label **real** clips: many people, each error class.
2. Train on MediaPipe landmarks from those videos, same feature schema.
3. Keep this set only as augmentation.
4. Ship ML counting only after exact-match on real sets is high (e.g. ≥ 90%) and MAE ≪ 0.3.

## Retrain

```text
python -m ml.run_pipeline
```

Uses `synthetic_gym_dataset/` when `sequences.jsonl` is there. To rebuild the old `data/ml/` set instead: `python -m ml.run_pipeline --legacy`.

Needs `scikit-learn` and `joblib` (`requirements.txt`). Writes `models/form/` using catalog check names plus `primary`. The numbers in `synthetic_gym_dataset/eval_report.json` use a different counting heuristic than the live coach.
