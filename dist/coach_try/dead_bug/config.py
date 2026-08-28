EXERCISE_CONFIG = {
    "display_name": "Dead Bug",
    "mode": "hold",
    "view": "side",
    "initial_stage": "rest",
    "hold_direction": "above",
    "side_check": "knee",
    "calibrate_seconds": 2.5,
    "setup_hint": "Lie on your back, sideways to the camera",
    "calibrate_hint": "Extend one leg and the opposite arm without arching",
    "not_visible_message": "Lie on your back, camera from the side",
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
        "knee": {
            "type": "max_angle",
            "points": ("hip", "knee", "ankle"),
            "down_threshold": 140,
            "up_threshold": 155,
            "direction": "above",
        },
        "torso_flat": {
            "type": "vertical_angle",
            "points": ("shoulder", "hip"),
            "down_threshold": 55,
            "up_threshold": None,
            "direction": "above",
        },
        "low_back_arch": {
            "type": "signed_line_offset",
            "points": ("shoulder", "hip", "knee"),
            "down_threshold": -0.14,
            "up_threshold": None,
            "direction": "below",
        },
    },
    "primary_check": "knee",
    "depth_checks": ["knee", "torso_flat"],
    "fault_checks": ["low_back_arch"],
    "feedback_rules": [
        {
            "require": {"knee": True, "torso_flat": True, "low_back_arch": False},
            "message": "Ribs down, {side} leg reaching long",
            "counts_as_good": True,
        },
        {
            "require": {"low_back_arch": True},
            "message": "Low back arching - press your ribs toward the floor",
            "counts_as_good": False,
        },
        {
            "require": {"torso_flat": False},
            "message": "Keep your back on the floor - don't sit up",
            "counts_as_good": False,
        },
        {
            "require": {"knee": False},
            "message": "Extend one leg toward the floor, slow and controlled",
            "counts_as_good": False,
        },
    ],
    "default_message": "Extend opposite arm and leg without arching",
}
