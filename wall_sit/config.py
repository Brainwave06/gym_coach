EXERCISE_CONFIG = {
    "display_name": "Wall Sit",
    "mode": "hold",
    "view": "side",
    "initial_stage": "rest",
    "hold_direction": "below",
    "calibrate_seconds": 2.5,
    "setup_hint": "Turn sideways, back against a wall",
    "calibrate_hint": "Slide down until thighs are close to parallel",
    "not_visible_message": "Stand sideways so hips and knees are visible",
    "landmarks": {
        "left": {"shoulder": 11, "hip": 23, "knee": 25, "ankle": 27},
        "right": {"shoulder": 12, "hip": 24, "knee": 26, "ankle": 28},
    },
    "checks": {
        "knee": {
            "type": "angle",
            "points": ("hip", "knee", "ankle"),
            "down_threshold": 115,
            "up_threshold": 145,
            "direction": "below",
        },
        "torso_lean": {
            "type": "vertical_angle",
            "points": ("shoulder", "hip"),
            "down_threshold": 28,
            "up_threshold": None,
            "direction": "above",
        },
        "knee_asymmetry": {
            "type": "angle_asymmetry",
            "points": ("hip", "knee", "ankle"),
            "down_threshold": 12,
            "up_threshold": None,
            "direction": "above",
        },
    },
    "primary_check": "knee",
    "depth_checks": ["knee"],
    "fault_checks": ["torso_lean", "knee_asymmetry"],
    "feedback_rules": [
        {
            "require": {"knee": True, "torso_lean": False, "knee_asymmetry": False},
            "message": "Strong wall sit - thighs near parallel",
            "counts_as_good": True,
        },
        {
            "require": {"torso_lean": True},
            "message": "Torso leaning - press your back into the wall",
            "counts_as_good": False,
        },
        {
            "require": {"knee_asymmetry": True},
            "message": "Uneven - {side} leg is taking more load",
            "counts_as_good": False,
        },
        {
            "require": {"knee": False},
            "message": "Sit lower until knees are near 90 degrees",
            "counts_as_good": False,
        },
    ],
    "default_message": "Sit lower until knees are near 90 degrees",
}
