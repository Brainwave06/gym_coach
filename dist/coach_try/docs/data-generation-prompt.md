# Prompt: generate exercise form time-series (no people needed)

Copy everything under **PROMPT (paste this)** into another AI, a graphics/sim person, or a student who will write a generator. It matches this repo’s coach (`common/catalog.py` + `ml/generate.py` schema).

---

## PROMPT (paste this)

You are generating a **synthetic biomechanics dataset** for a webcam exercise coach. There are **no videos of real people**. Output is **numeric pose time-series only** (joint angles / offsets), not rendered faces, not photos.

### Goal

For each of these exercises, produce sequences a model can use to:

1. **Count reps** (or score a hold), and  
2. **Classify form errors** (multi-label: a rep can have 0, 1, or 2 faults).

Exercises (IDs must match exactly):

`squat`, `box_squat`, `plank`, `pushup`, `knee_pushup`, `lunge`, `glute_bridge`, `wall_sit`, `bird_dog`, `dead_bug`, `biceps_curl`.

Modes:

- Reps: squat, box_squat, pushup, knee_pushup, lunge, glute_bridge, biceps_curl  
- Hold: plank, wall_sit, bird_dog, dead_bug  

Camera convention: squat / box_squat = **front**; all others = **side**.

### Output format (JSONL)

One JSON object per **session** (a set or a hold clip).

**Reps session:**

```json
{
  "exercise_id": "squat",
  "athlete_id": "ath_000",
  "experience": "beginner",
  "mode": "reps",
  "fps": 20,
  "true_count": 7,
  "frames": [
    {
      "knee": 168.2,
      "hip": 172.0,
      "torso_lean": 12.1,
      "knees_past_toes": 0.04,
      "knee_valgus": 0.82,
      "knee_asymmetry": 4.0,
      "hip_asymmetry": 3.1,
      "heel_lift": 0.08,
      "primary": 168.2,
      "primary_vel": -2.4,
      "primary_acc": 0.1,
      "phase": "up"
    }
  ],
  "rep_spans": [
    {
      "start": 12,
      "end": 40,
      "true_rep": 1,
      "labels": {
        "knee_valgus": false,
        "heel_lift": false,
        "knee_asymmetry": false,
        "hip_asymmetry": false,
        "torso_lean": true,
        "knees_past_toes": false,
        "is_good": false,
        "incomplete": false
      }
    }
  ]
}
```

**Hold session:** same `frames`, no `rep_spans`, `true_count` = 0, `labels` at top level (`is_good` + that exercise’s faults).

`phase` for reps: only `"up"` | `"down"` | `"transition"`. For holds: `"hold"`.

`primary` = the main joint for that move (see features). `primary_vel` / `primary_acc` = first/second discrete derivative of `primary`.

### Features required per exercise

Use **degrees** for angles. Use **dimensionless ratios/offsets** in roughly `[-0.4, 0.6]` for sag/pike/forward offset (not 0/1 classification).

| exercise_id | primary | other series to include | error labels (true/false) |
|-------------|---------|-------------------------|---------------------------|
| squat, box_squat | knee (hip–knee–ankle) | hip, torso_lean, knees_past_toes, knee_valgus, knee_asymmetry, hip_asymmetry, heel_lift | those 6 faults + is_good + incomplete |
| pushup | elbow | body_line, hip_sag, hip_pike, knee, elbow_flare, head_drop | those 6 + is_good + incomplete |
| knee_pushup | elbow | body_line, hip_sag, hip_pike, elbow_flare, head_drop (no knee-drop fault) | those 5 + is_good + incomplete |
| lunge | knee | torso_lean, knees_past_toes, knee_asymmetry | torso_lean, knees_past_toes + is_good + incomplete |
| glute_bridge | hip | lockout, knee, hip_asymmetry | knee, hip_asymmetry + is_good + incomplete |
| biceps_curl | elbow | torso_lean, shoulder_swing | those 2 + is_good + incomplete |
| plank | body_line | hip_sag, hip_pike, knee, shoulder_stack | those 4 + is_good |
| wall_sit | knee | torso_lean, knee_asymmetry | those 2 + is_good |
| bird_dog | knee | elbow, hip_sag, hip_twist | hip_sag + is_good |
| dead_bug | knee | torso_flat, low_back_arch | low_back_arch + is_good |

Biomechanics meaning of faults (label from **intent of the movement**, not from copying a magic threshold):

- squat `knee_valgus`: knees collapse inward at the bottom  
- squat `heel_lift`: heels leave the floor  
- squat `torso_lean`: chest collapses / excessive forward lean  
- squat `knees_past_toes`: knees shoot far forward, hips don’t sit back  
- squat `*_asymmetry`: one side does more work  
- pushup `hip_sag` / `hip_pike`: hips below / above a straight line  
- pushup `elbow_flare`: elbows wing out  
- pushup `head_drop`: head hangs  
- curl `shoulder_swing` / `torso_lean`: cheating the weight  
- plank same sag/pike/bent knees/shoulders not stacked  
- incomplete: motion starts a rep and never finishes (must **not** increment `true_count`)

### Athletes (diversity, anti-bias)

Create **at least 80 athletes** (`ath_000` …). Vary independently:

- height, limb proportions, hip/shoulder width  
- left vs right dominance (small kinematic bias, **not** a feature named “gender” or “race”)  
- tempo (slow/fast), ROM (stiff vs mobile)  
- MediaPipe-like **jitter** and occasional missing frames (repeat last valid values; do not invent a second person)  
- experience mix: ~40% beginner, ~35% intermediate, ~25% advanced  

**Do not** put `experience`, sex, age, BMI, injury, or skin tone into the **frame features**. Those may exist only as athlete metadata for analysis.

### Class mix (do not make this 50/50)

Of **completed** reps:

- beginner: ~42% have ≥1 fault  
- intermediate: ~27%  
- advanced: ~14%  

Given a fault, ~8–28% also have a **second** fault (higher for beginners).  
~6% of attempted reps are **incomplete**.  
~5–8% of labels may be flipped (human annotator noise).  
Most remaining reps are **good**. Rare faults must stay rare.

### Counting ground truth

- You **know** how many complete cycles you simulated. That is `true_count`.  
- Phase labels come from the **kinematic cycle** (bottom vs top), not from “crossed 100 degrees.”  
- Rest frames between reps: low velocity, phase `up` (or `down` if the move starts at the bottom, e.g. glute bridge).  
- 4–10 completed reps per reps-session plus incomplete attempts mixed in.  
- Holds: 2–5 seconds of frames at 15–25 FPS.

### Split

Assign athletes to train / val / test **by athlete_id** (e.g. 62% / 16% / 22%). **Never** put frames from a test athlete into train.

### What you MUST do

- Smooth series slightly (moving average 3–7 frames) then add jitter.  
- Couple faults to the **hard part** of the rep (bottom of squat, bottom of push-up, top of curl).  
- Keep left/right series consistent with `left_bias`.  
- Write valid JSONL, UTF-8, one object per line.  
- Include a `manifest.json`: athlete counts, per-exercise sequence counts, fault rates, split ids.

### What you MUST NOT do

- Do **not** scrape or copy YouTube/Instagram/TikTok gym videos or screenshots.  
- Do **not** generate photoreal faces or identifiable bodies.  
- Do **not** label errors by `if angle < 100: fault` using this app’s thresholds — that just clones the old rules. Use a **latent severity** plus athlete-specific tolerance, then emit continuous angles.  
- Do **not** balance classes by oversampling rare faults until they are 50%.  
- Do **not** use the same sine wave for every athlete.  
- Do **not** leak `true_count` or labels into `frames` except `phase`.  
- Do **not** train on test athletes.  
- Do **not** claim this equals real webcam data. State **synthetic** in the manifest.

### Amount

Minimum useful set: **≥2000 sessions** across all exercises, **≥80 athletes**. Prefer more holds if those classes stay tiny.

### After generating

Save `sequences.jsonl`, `split.json`, `athletes.json`. Then a separate training script should fit models **only on train athletes** and report **count MAE**, **exact-count %**, and **per-fault F1 on test athletes**. If frame-phase accuracy is ~100% but count MAE ≥ 0.5, say counting **failed**. If error macro-F1 < 0.75 on squat/push-up, say those errors are **not production-ready**.

---

## Notes for you (not part of the paste)

Public web data exists but usually **does not** give your error tags, and some licenses are **research-only**. The teammate dump lives in `synthetic_gym_dataset/`. Retrain with `python -m ml.run_pipeline`. Honest scores: [ml-report.md](ml-report.md).
