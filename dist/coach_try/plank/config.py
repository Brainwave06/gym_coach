EXERCISE_CONFIG = {
    "display_name": "Plank",
    "mode": "hold",
    "view": "side",
    "initial_stage": "rest",
    "hold_direction": "above",
    "calibrate_seconds": 2.5,
    "setup_hint": "Turn sideways. For best 3D measurement, angle slightly (45-deg).",
    "important_joints": ["shoulder", "elbow", "hip"],
    "calibrate_hint": "Get into a strong plank and hold still",
    "not_visible_message": "Body not clearly visible - turn sideways to the camera",
    "landmarks": {
        "left": {
            "shoulder": 11, "elbow": 13, "wrist": 15,
            "hip": 23, "knee": 25, "ankle": 27,
        },
        "right": {
            "shoulder": 12, "elbow": 14, "wrist": 16,
            "hip": 24, "knee": 26, "ankle": 28,
        },
    },
    "checks": {
        "body_line": {
            "type": "angle",
            "points": ("shoulder", "hip", "ankle"),
            "down_threshold": 155,
            "up_threshold": 165,
            "direction": "above",
        },
        "hip_sag": {
            "type": "signed_line_offset",
            "points": ("shoulder", "hip", "ankle"),
            "down_threshold": 0.08,
            "up_threshold": None,
            "direction": "above",
        },
        "hip_pike": {
            "type": "signed_line_offset",
            "points": ("shoulder", "hip", "ankle"),
            "down_threshold": -0.08,
            "up_threshold": None,
            "direction": "below",
        },
        "knee": {
            "type": "angle",
            "points": ("hip", "knee", "ankle"),
            "down_threshold": 150,
            "up_threshold": None,
            "direction": "below",
        },
        "shoulder_stack": {
            "type": "segment_align",
            "points": ("shoulder", "elbow"),
            "down_threshold": 0.45,
            "up_threshold": None,
            "direction": "above",
        },
    },
    "primary_check": "body_line",
    "depth_checks": ["body_line"],
    "fault_checks": ["hip_sag", "hip_pike", "knee", "shoulder_stack"],
    "feedback_rules": [
        {
            "require": {
                "body_line": True,
                "hip_sag": False, "hip_pike": False,
                "knee": False, "shoulder_stack": False,
            },
            "message": "Strong plank - keep a straight line",
            "counts_as_good": True,
        },
        {
            "require": {"hip_sag": True},
            "message": "Hips sagging - squeeze glutes and brace core",
            "counts_as_good": False,
        },
        {
            "require": {"hip_pike": True},
            "message": "Hips too high - lower them into a straight line",
            "counts_as_good": False,
        },
        {
            "require": {"shoulder_stack": True},
            "message": "Stack shoulders over elbows / wrists",
            "counts_as_good": False,
        },
        {
            "require": {"knee": True},
            "message": "Knees bending - straighten your legs",
            "counts_as_good": False,
        },
        {
            "require": {"body_line": False},
            "message": "Get into plank - straight line from shoulders to heels",
            "counts_as_good": False,
        },
    ],
    "default_message": "Hold a straight line from head to heels",
}
