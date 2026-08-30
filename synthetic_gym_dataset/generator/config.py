"""
Exercise configuration for synthetic biomechanics dataset generation.
"""

REPS_EXERCISES = [
    "squat", "box_squat", "pushup", "knee_pushup",
    "lunge", "glute_bridge", "biceps_curl",
]
HOLD_EXERCISES = ["plank", "wall_sit", "bird_dog", "dead_bug"]
ALL_EXERCISES = REPS_EXERCISES + HOLD_EXERCISES

CAMERA = {
    "squat": "front", "box_squat": "front",
    "pushup": "side", "knee_pushup": "side", "lunge": "side",
    "glute_bridge": "side", "biceps_curl": "side",
    "plank": "side", "wall_sit": "side", "bird_dog": "side", "dead_bug": "side",
}

# kind: "angle" (degrees) or "ratio" (dimensionless, roughly [-0.4, 0.6])
# For reps exercises: rest_angle = position at rest/top, hard_angle = position at the
# hard part of the rep. rest_phase indicates whether rest corresponds to phase 'up' or 'down'.
EXERCISES = {
    "squat": {
        "mode": "reps", "primary": "knee", "rest_phase": "up",
        "rest_angle": 172.0, "hard_angle": 82.0,
        "series": {
            "hip":              {"kind": "angle", "rest": 175.0, "hard": 70.0},
            "torso_lean":       {"kind": "angle", "rest": 6.0,   "hard": 18.0},
            "knees_past_toes":  {"kind": "ratio", "base": 0.05},
            "knee_valgus":      {"kind": "ratio", "base": 0.05},
            "knee_asymmetry":   {"kind": "ratio", "base": 0.03},
            "hip_asymmetry":    {"kind": "ratio", "base": 0.03},
            "heel_lift":        {"kind": "ratio", "base": 0.02},
        },
        "faults": ["knee_valgus", "heel_lift", "knee_asymmetry",
                   "hip_asymmetry", "torso_lean", "knees_past_toes"],
    },
    "box_squat": {
        "mode": "reps", "primary": "knee", "rest_phase": "up",
        "rest_angle": 172.0, "hard_angle": 95.0, "dwell_at_hard": True,
        "series": {
            "hip":              {"kind": "angle", "rest": 175.0, "hard": 85.0},
            "torso_lean":       {"kind": "angle", "rest": 6.0,   "hard": 16.0},
            "knees_past_toes":  {"kind": "ratio", "base": 0.05},
            "knee_valgus":      {"kind": "ratio", "base": 0.05},
            "knee_asymmetry":   {"kind": "ratio", "base": 0.03},
            "hip_asymmetry":    {"kind": "ratio", "base": 0.03},
            "heel_lift":        {"kind": "ratio", "base": 0.02},
        },
        "faults": ["knee_valgus", "heel_lift", "knee_asymmetry",
                   "hip_asymmetry", "torso_lean", "knees_past_toes"],
    },
    "pushup": {
        "mode": "reps", "primary": "elbow", "rest_phase": "up",
        "rest_angle": 168.0, "hard_angle": 72.0,
        "series": {
            "body_line": {"kind": "ratio", "base": 0.03},
            "hip_sag":   {"kind": "ratio", "base": 0.02},
            "hip_pike":  {"kind": "ratio", "base": 0.02},
            "knee":      {"kind": "angle", "rest": 178.0, "hard": 175.0},
            "elbow_flare": {"kind": "ratio", "base": 0.10},
            "head_drop": {"kind": "ratio", "base": 0.04},
        },
        "faults": ["body_line", "hip_sag", "hip_pike", "knee", "elbow_flare", "head_drop"],
    },
    "knee_pushup": {
        "mode": "reps", "primary": "elbow", "rest_phase": "up",
        "rest_angle": 165.0, "hard_angle": 75.0,
        "series": {
            "body_line": {"kind": "ratio", "base": 0.03},
            "hip_sag":   {"kind": "ratio", "base": 0.02},
            "hip_pike":  {"kind": "ratio", "base": 0.02},
            "elbow_flare": {"kind": "ratio", "base": 0.10},
            "head_drop": {"kind": "ratio", "base": 0.04},
        },
        "faults": ["body_line", "hip_sag", "hip_pike", "elbow_flare", "head_drop"],
    },
    "lunge": {
        "mode": "reps", "primary": "knee", "rest_phase": "up",
        "rest_angle": 173.0, "hard_angle": 92.0,
        "series": {
            "torso_lean":      {"kind": "angle", "rest": 4.0, "hard": 10.0},
            "knees_past_toes": {"kind": "ratio", "base": 0.06},
            "knee_asymmetry":  {"kind": "ratio", "base": 0.03},
        },
        "faults": ["torso_lean", "knees_past_toes"],
    },
    "glute_bridge": {
        "mode": "reps", "primary": "hip", "rest_phase": "down",
        "rest_angle": 148.0, "hard_angle": 178.0,
        "series": {
            "lockout":       {"kind": "ratio", "base": 0.35},
            "knee":          {"kind": "angle", "rest": 95.0, "hard": 95.0},
            "hip_asymmetry": {"kind": "ratio", "base": 0.03},
        },
        "faults": ["knee", "hip_asymmetry"],
    },
    "biceps_curl": {
        "mode": "reps", "primary": "elbow", "rest_phase": "up",
        "rest_angle": 168.0, "hard_angle": 42.0,
        "series": {
            "torso_lean":     {"kind": "angle", "rest": 3.0, "hard": 7.0},
            "shoulder_swing": {"kind": "ratio", "base": 0.05},
        },
        "faults": ["torso_lean", "shoulder_swing"],
    },
    "plank": {
        "mode": "hold", "primary": "body_line",
        "series": {
            "hip_sag":       {"kind": "ratio", "base": 0.03},
            "hip_pike":      {"kind": "ratio", "base": 0.03},
            "knee":          {"kind": "angle", "rest": 178.0, "hard": 178.0},
            "shoulder_stack": {"kind": "ratio", "base": 0.05},
        },
        "faults": ["hip_sag", "hip_pike", "knee", "shoulder_stack"],
        "primary_kind": "ratio", "primary_base": 0.03,
    },
    "wall_sit": {
        "mode": "hold", "primary": "knee",
        "series": {
            "torso_lean":     {"kind": "angle", "rest": 4.0, "hard": 4.0},
            "knee_asymmetry": {"kind": "ratio", "base": 0.03},
        },
        "faults": ["torso_lean", "knee_asymmetry"],
        "primary_kind": "angle", "primary_rest": 92.0,
    },
    "bird_dog": {
        "mode": "hold", "primary": "knee",
        "series": {
            "elbow":    {"kind": "angle", "rest": 172.0, "hard": 172.0},
            "hip_sag":  {"kind": "ratio", "base": 0.03},
            "hip_twist": {"kind": "ratio", "base": 0.04},
        },
        "faults": ["hip_sag"],
        "primary_kind": "angle", "primary_rest": 175.0,
    },
    "dead_bug": {
        "mode": "hold", "primary": "knee",
        "series": {
            "torso_flat":     {"kind": "ratio", "base": 0.04},
            "low_back_arch":  {"kind": "ratio", "base": 0.03},
        },
        "faults": ["low_back_arch"],
        "primary_kind": "angle", "primary_rest": 95.0,
    },
}
