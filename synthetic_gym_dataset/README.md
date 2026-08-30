# Synthetic gym-exercise biomechanics dataset

**Fully synthetic.** No real videos, no scraped footage, no photoreal faces or
identifiable bodies. Every session is procedurally generated numeric
pose-derived time-series (joint angles / offsets), matching the schema in the
spec. Do not present this as equivalent to real webcam data — it's a bootstrap
for model architecture/pipeline work, not a substitute for real, consented
recordings.

## Files

- `sequences.jsonl` — 2,196 sessions (one JSON object per line) across all 11
  exercises. Reps sessions include `frames` + `rep_spans`; hold sessions
  include `frames` + top-level `labels`. Each session also carries `split`
  (train/val/test, assigned by athlete) and `camera` for convenience.
- `athletes.json` — 100 synthetic athletes with independent height, limb
  proportions, hip/shoulder width, left/right bias, tempo, ROM, experience
  level, and per-athlete fault-severity/jitter/dropout parameters. No
  gender/race/age/BMI/injury fields — only kinematic and experience metadata,
  and none of it is present in `frames`.
- `split.json` — athlete → split assignment (train 62 / val 16 / test 22
  athletes). No frames from a test or val athlete appear in train.
- `manifest.json` — per-exercise session counts, completed/attempted rep
  counts, incomplete rate, fault rate, and per-label true-rate, plus the
  explicit `"dataset_type": "synthetic"` statement.
- `generator/` — the generation code (`config.py`, `athletes.py`,
  `generator.py`, `run_generate.py`) so the set can be regenerated or scaled
  up (same 100 athletes / different session counts / different seed).
- `train_eval.py` — trains simple RandomForest baselines **only on train
  athletes** and evaluates on held-out **test athletes**:
  - a frame-level phase classifier + a phase-transition counting algorithm
    (reports frame-phase accuracy, count MAE, exact-count %)
  - per-fault (and `is_good`/`incomplete`) classifiers from span-level
    summary statistics (reports F1 per label + macro-F1 across faults)
- `eval_report.json` — the full numeric results from that run.

## Headline results (test athletes, held out from training)

| exercise | phase acc | count MAE | exact-count % | fault macro-F1 |
|---|---|---|---|---|
| squat | 0.966 | 0.00 | 100% | 0.837 |
| box_squat | 0.946 | 0.19 | 88.5% | 0.896 |
| pushup | 0.959 | 0.00 | 100% | 0.793 |
| knee_pushup | 0.954 | 0.00 | 100% | 0.979 |
| lunge | 0.949 | 0.38 | 93.1% | 0.942 |
| glute_bridge | 0.901 | 0.10 | 90.0% | 0.947 |
| biceps_curl | 0.966 | 0.03 | 96.5% | 0.987 |
| plank | — | — | — | 1.000 |
| wall_sit | — | — | — | 1.000 |
| bird_dog | — | — | — | 1.000 |
| dead_bug | — | — | — | 1.000 |

Per the spec's own bar: count MAE stays under 0.5 everywhere (counting did
**not** fail on any exercise), and fault macro-F1 clears 0.75 on both squat
and push-up (0.837 and 0.793) — **production-ready by the stated threshold**,
though push-up's `hip_sag`/`head_drop` labels (F1 0.61–0.55) are the weakest
spots and would benefit from more hold-mode-style sessions or finer-grained
severity modeling if you want headroom there.

Rare faults were checked to stay rare (e.g. squat `heel_lift` ≈ 2% of
completed reps, hip/knee asymmetry faults 6–10%) rather than being
artificially balanced to 50/50, per the spec.

The desktop coach trains from this folder with `python -m ml.run_pipeline`
(see `docs/ml-report.md`). Live counting stays rule-based; this set feeds
the error helper. `eval_report.json` counting is a separate heuristic.

## Known simplifications (be aware before treating this as final)

- Kinematics are a stylized progress-curve model (cosine easing + latent
  fault "bumps" peaking at the hard part of the rep), not a physics/IK
  simulation — good for pipeline/model development, not for claims about real
  human movement variability.
- Left/right dominance, tempo, and ROM are athlete-level scalars, not
  full biomechanical chains — they shift timing/depth/asymmetry baselines but
  don't model joint coupling in detail.
- The counting baseline in `train_eval.py` derives predicted count from a
  frame-phase classifier's output, not from `true_count`/labels — but it's a
  simple heuristic (transition-segment detection), not a tuned production
  counter.
