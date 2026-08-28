EXERCISE_CONFIG = {
    "display_name": "Bird Dog",
    "mode": "hold",
    "view": "side",
    "initial_stage": "rest",
    "hold_direction": "above",
    "side_check": "knee",
    "calibrate_seconds": 2.5,
    "setup_hint": "On all fours, sideways to the camera",
    "calibrate_hint": "Reach one arm forward and the opposite leg back",
    "not_visible_message": "Get on all fours sideways so arm and leg are visible",
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
            "down_threshold": 145,
            "up_threshold": 160,
            "direction": "above",
        },
        "elbow": {
            "type": "max_angle",
            "points": ("shoulder", "elbow", "wrist"),
            "down_threshold": 145,
            "up_threshold": None,
            "direction": "above",
        },
        "hip_sag": {
            "type": "signed_line_offset",
            "points": ("shoulder", "hip", "ankle"),
            "down_threshold": 0.12,
            "up_threshold": None,
            "direction": "above",
        },
        "hip_twist": {
            "type": "angle_asymmetry",
            "points": ("shoulder", "hip", "knee"),
            "down_threshold": 55,
            "up_threshold": None,
            "direction": "below",
        },
    },
    "primary_check": "knee",
    "depth_checks": ["knee", "elbow"],
    "fault_checks": ["hip_sag"],
    "feedback_rules": [
        {
            "require": {"knee": True, "elbow": True, "hip_sag": False},
            "message": "Reach long - square hips, {side} leg extended",
            "counts_as_good": True,
        },
        {
            "require": {"hip_sag": True},
            "message": "Hips sagging - brace your core, don't dump the low back",
            "counts_as_good": False,
        },
        {
            "require": {"elbow": False},
            "message": "Reach the opposite arm forward",
            "counts_as_good": False,
        },
        {
            "require": {"knee": False},
            "message": "Extend the opposite leg behind you",
            "counts_as_good": False,
        },
    ],
    "default_message": "Reach opposite arm and leg, keep hips level",
}
