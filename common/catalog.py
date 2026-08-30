import copy

from biceps_curl.config import EXERCISE_CONFIG as BICEPS_CONFIG
from bird_dog.config import EXERCISE_CONFIG as BIRD_DOG_CONFIG
from dead_bug.config import EXERCISE_CONFIG as DEAD_BUG_CONFIG
from glute_bridge.config import EXERCISE_CONFIG as GLUTE_CONFIG
from lunge.config import EXERCISE_CONFIG as LUNGE_CONFIG
from plank.config import EXERCISE_CONFIG as PLANK_CONFIG
from pushup.config import EXERCISE_CONFIG as PUSHUP_CONFIG
from squat.config import EXERCISE_CONFIG as SQUAT_CONFIG
from wall_sit.config import EXERCISE_CONFIG as WALL_SIT_CONFIG


def _knee_pushup():
    cfg = copy.deepcopy(PUSHUP_CONFIG)
    cfg["display_name"] = "Knee Push-up"
    cfg["id"] = "knee_pushup"
    cfg["setup_hint"] = "Knees down - body in one line from head to knees"
    cfg["calibrate_hint"] = "High plank on knees, arms straight"
    cfg["fault_checks"] = [name for name in cfg["fault_checks"] if name != "knee"]
    for rule in cfg["feedback_rules"]:
        rule["require"].pop("knee", None)
    cfg["feedback_rules"] = [
        rule for rule in cfg["feedback_rules"]
        if "knee" not in rule.get("require", {})
    ]
    return cfg


def _box_squat():
    cfg = copy.deepcopy(SQUAT_CONFIG)
    cfg["display_name"] = "Box Squat"
    cfg["id"] = "box_squat"
    cfg["setup_hint"] = "Sit back as if to a chair — stop above parallel is OK."
    cfg["calibrate_hint"] = "Stand tall. Imagine sitting to a box behind you."
    cfg["checks"]["knee"]["down_threshold"] = 115
    cfg["checks"]["hip"]["down_threshold"] = 125
    return cfg


BASE = {
    "squat": SQUAT_CONFIG,
    "box_squat": _box_squat(),
    "plank": PLANK_CONFIG,
    "pushup": PUSHUP_CONFIG,
    "knee_pushup": _knee_pushup(),
    "lunge": LUNGE_CONFIG,
    "glute_bridge": GLUTE_CONFIG,
    "wall_sit": WALL_SIT_CONFIG,
    "bird_dog": BIRD_DOG_CONFIG,
    "dead_bug": DEAD_BUG_CONFIG,
    "biceps_curl": BICEPS_CONFIG,
}

for key, cfg in BASE.items():
    cfg.setdefault("id", key)

TEACH = {
    "squat": "Feet under shoulders. Sit the hips back. Chest tall. Heels stay down.",
    "box_squat": "Sit back toward an imaginary box. Stop when thighs are above parallel, then stand.",
    "plank": "Straight line head to heels. Squeeze glutes. Don't let hips sag.",
    "pushup": "Hands under shoulders. Lower the chest, body rigid, press up.",
    "knee_pushup": "Knees on the floor. Same rigid body as a push-up. Lower chest, press up.",
    "lunge": "Step forward. Drop the back knee. Front knee tracks over the mid-foot. Stand up.",
    "glute_bridge": "Lie on your back. Drive through heels. Squeeze glutes at the top, then lower.",
    "wall_sit": "Back against the wall. Slide down until thighs are near parallel. Hold still.",
    "bird_dog": "All fours. Reach one arm forward and the opposite leg back. Hips stay square.",
    "dead_bug": "On your back. Ribs down. Extend opposite arm and leg without arching.",
    "biceps_curl": "Elbow pinned to your side. Curl without swinging or leaning back.",
}

MENU = [
    ("1", "squat", "Squat         ANY"),
    ("2", "plank", "Plank         ANY"),
    ("3", "pushup", "Push-up       ANY"),
    ("4", "lunge", "Lunge         ANY"),
    ("5", "glute_bridge", "Glute bridge  ANY"),
    ("6", "wall_sit", "Wall sit      ANY"),
    ("7", "bird_dog", "Bird dog      ANY"),
    ("8", "dead_bug", "Dead bug      ANY"),
    ("9", "biceps_curl", "Biceps curl   ANY"),
]


def get_config(exercise_id):
    if exercise_id not in BASE:
        raise KeyError(exercise_id)
    cfg = copy.deepcopy(BASE[exercise_id])
    cfg["id"] = exercise_id
    cfg["teach"] = TEACH.get(exercise_id, cfg.get("setup_hint", ""))
    return cfg
