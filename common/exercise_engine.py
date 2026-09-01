"""
Shared exercise engine (checks + camera loop + HUD).
Each exercise only provides a config dict; squat is reps, plank is a hold.
"""

import copy
import os
import time
from collections import deque
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from common.history import append_session
from common.models import resolve_model_path
from common.voice import configure_voice, speak, spoken_from_message, stop_voice
from common.voice import configure_voice, speak, spoken_from_message, stop_voice

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VISIBILITY_THRESHOLD = 0.5
UNCERTAIN_THRESHOLD = 0.55
DRAW_CONFIDENCE_THRESHOLD = 0.35
SMOOTHING_WINDOW = 5
POSE_SMOOTH_ALPHA = 0.4
SIDE_DOMINANCE_GAP = 0.15

# Skip the dense face mesh; keep a light head cue (ears + nose).
FACE_CONNECTIONS = [(7, 0), (0, 8)]
TORSO_CONNECTIONS = [(11, 12), (11, 23), (12, 24), (23, 24)]
LEFT_ARM_CONNECTIONS = [(11, 13), (13, 15)]
RIGHT_ARM_CONNECTIONS = [(12, 14), (14, 16)]
LEFT_LEG_CONNECTIONS = [(23, 25), (25, 27), (27, 29), (27, 31)]
RIGHT_LEG_CONNECTIONS = [(24, 26), (26, 28), (28, 30), (28, 32)]

POSE_CONNECTION_COLORS = [
    (FACE_CONNECTIONS, (170, 170, 170), 1),
    (TORSO_CONNECTIONS, (80, 200, 255), 3),
    (LEFT_ARM_CONNECTIONS, (80, 220, 80), 3),
    (RIGHT_ARM_CONNECTIONS, (80, 180, 255), 3),
    (LEFT_LEG_CONNECTIONS, (180, 80, 255), 3),
    (RIGHT_LEG_CONNECTIONS, (255, 80, 180), 3),
]

POSE_CONNECTIONS = (
    FACE_CONNECTIONS
    + TORSO_CONNECTIONS
    + LEFT_ARM_CONNECTIONS
    + RIGHT_ARM_CONNECTIONS
    + LEFT_LEG_CONNECTIONS
    + RIGHT_LEG_CONNECTIONS
)


class _SmoothedLandmark:
    __slots__ = ("x", "y", "z", "visibility", "presence")

    def __init__(self, x, y, z, visibility, presence):
        self.x = x
        self.y = y
        self.z = z
        self.visibility = visibility
        self.presence = presence


def landmark_confidence(lm):
    scores = []
    if getattr(lm, "visibility", None) is not None:
        scores.append(lm.visibility)
    if getattr(lm, "presence", None) is not None:
        scores.append(lm.presence)
    return min(scores) if scores else 1.0


def smooth_pose_landmarks(landmarks, ema_state, alpha=POSE_SMOOTH_ALPHA):
    pts = ema_state.setdefault("xy", None)
    if pts is None or len(pts) != len(landmarks):
        ema_state["xy"] = [[lm.x, lm.y] for lm in landmarks]
    else:
        for i, lm in enumerate(landmarks):
            pts[i][0] = alpha * lm.x + (1.0 - alpha) * pts[i][0]
            pts[i][1] = alpha * lm.y + (1.0 - alpha) * pts[i][1]

    smoothed = []
    for i, lm in enumerate(landmarks):
        x, y = ema_state["xy"][i]
        smoothed.append(_SmoothedLandmark(x, y, lm.z, lm.visibility, lm.presence))
    return smoothed


def calculate_angle(a, b, c):
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    c = np.array(c, dtype=float)

    if a.size >= 3:
        ba = a[:3] - b[:3]
        bc = c[:3] - b[:3]
        denom = np.linalg.norm(ba) * np.linalg.norm(bc)
        if denom == 0:
            return None
        cosang = float(np.clip(np.dot(ba, bc) / denom, -1.0, 1.0))
        return float(np.degrees(np.arccos(cosang)))

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle


def get_landmark_xy(landmarks, idx, w, h):
    lm = landmarks[idx]
    conf = landmark_confidence(lm)
    if w is None or h is None:
        z = lm.z if lm.z is not None else 0.0
        return (lm.x, lm.y, z), conf
    return (lm.x * w, lm.y * h), conf


def _pixel_point(lm, w, h):
    return (int(lm.x * w), int(lm.y * h))


def exercise_joint_indices(exercise_config):
    indices = set()
    if not exercise_config:
        return indices
    important = exercise_config.get("important_joints")
    for side_map in exercise_config.get("landmarks", {}).values():
        for name, idx in side_map.items():
            if not important or name in important:
                indices.add(idx)
    return indices


def draw_landmarks(frame, landmarks, exercise_config=None):
    h, w, _ = frame.shape
    confidences = [landmark_confidence(lm) for lm in landmarks]
    points = [_pixel_point(lm, w, h) for lm in landmarks]
    highlight = exercise_joint_indices(exercise_config) if exercise_config else set()
    important_only = bool(exercise_config and exercise_config.get("important_joints"))

    for connections, color, default_thickness in POSE_CONNECTION_COLORS:
        for start_idx, end_idx in connections:
            if start_idx >= len(points) or end_idx >= len(points):
                continue
            if important_only and (start_idx not in highlight or end_idx not in highlight):
                continue
            if (confidences[start_idx] < DRAW_CONFIDENCE_THRESHOLD
                    or confidences[end_idx] < DRAW_CONFIDENCE_THRESHOLD):
                continue
            
            z_start = landmarks[start_idx].z if landmarks[start_idx].z is not None else 0
            z_end = landmarks[end_idx].z if landmarks[end_idx].z is not None else 0
            avg_z = (z_start + z_end) / 2.0
            thickness = max(1, int(default_thickness - avg_z * 5))
            
            cv2.line(frame, points[start_idx], points[end_idx], color, thickness, cv2.LINE_AA)

    for idx, point in enumerate(points):
        if confidences[idx] < DRAW_CONFIDENCE_THRESHOLD:
            continue
        if important_only and idx not in highlight:
            continue
            
        z = landmarks[idx].z if landmarks[idx].z is not None else 0
        base_radius = 6 if idx in highlight else 4
        radius = max(2, int(base_radius - z * 10))
        
        fill = (0, 255, 255) if idx in highlight else (0, 255, 0)
        cv2.circle(frame, point, radius + 1, (20, 20, 20), 2, cv2.LINE_AA)
        cv2.circle(frame, point, radius, fill, -1, cv2.LINE_AA)


def draw_exercise_guides(frame, landmarks, exercise_config, w, h):
    """Draw the primary body line (e.g. shoulder-hip-ankle) on the clearer side."""
    primary_name = exercise_config.get("primary_check")
    if not primary_name:
        return
    check_def = exercise_config["checks"].get(primary_name, {})
    if check_def.get("type") not in ("angle", "min_angle", "max_angle", "signed_line_offset"):
        return
    names = check_def.get("points")
    if not names or len(names) != 3:
        return

    left_points = get_side_points(landmarks, exercise_config["landmarks"]["left"], w, h)
    right_points = get_side_points(landmarks, exercise_config["landmarks"]["right"], w, h)
    left_conf = side_min_confidence(left_points, names)
    right_conf = side_min_confidence(right_points, names)
    side = left_points if left_conf >= right_conf else right_points
    if side_min_confidence(side, names) < VISIBILITY_THRESHOLD:
        return

    pts = [tuple(int(v) for v in side[name][0][:2]) for name in names]
    cv2.line(frame, pts[0], pts[2], (255, 255, 255), 2, cv2.LINE_AA)
    cv2.line(frame, pts[0], pts[1], (0, 220, 255), 3, cv2.LINE_AA)
    cv2.line(frame, pts[1], pts[2], (0, 220, 255), 3, cv2.LINE_AA)
    for pt in pts:
        cv2.circle(frame, pt, 7, (0, 220, 255), 2, cv2.LINE_AA)


def get_side_points(landmarks, side_landmark_map, w, h):
    return {
        joint_name: get_landmark_xy(landmarks, idx, w, h)
        for joint_name, idx in side_landmark_map.items()
    }


def side_min_confidence(side_points, names):
    scores = [side_points[n][1] for n in names if n in side_points]
    return min(scores) if len(scores) == len(names) else 0.0


def blend_side_values(left_val, right_val, left_points, right_points, names):
    """Prefer the camera-facing side; don't average in a ghost far-side limb."""
    left_conf = side_min_confidence(left_points, names)
    right_conf = side_min_confidence(right_points, names)

    if left_val is None:
        return right_val
    if right_val is None:
        return left_val
    if left_conf >= right_conf + SIDE_DOMINANCE_GAP:
        return left_val
    if right_conf >= left_conf + SIDE_DOMINANCE_GAP:
        return right_val
    total = left_conf + right_conf
    if total <= 0:
        return (left_val + right_val) / 2.0
    return (left_val * left_conf + right_val * right_conf) / total


def compute_side_angle(angle_def, side_points):
    p1_name, p2_name, p3_name = angle_def["points"]
    required_names = (p1_name, p2_name, p3_name)

    if not all(n in side_points and side_points[n][1] > VISIBILITY_THRESHOLD for n in required_names):
        return None

    p1 = side_points[p1_name][0]
    p2 = side_points[p2_name][0]
    p3 = side_points[p3_name][0]
    return calculate_angle(p1, p2, p3)


def compute_angle_asymmetry(check_def, left_points, right_points):
    left_angle = compute_side_angle(check_def, left_points)
    right_angle = compute_side_angle(check_def, right_points)

    if left_angle is None or right_angle is None:
        return None

    return abs(left_angle - right_angle)


def compute_horizontal_ratio(check_def, left_points, right_points):
    num_joint = check_def["numerator_joint"]
    den_joint = check_def["denominator_joint"]

    if not all(n in left_points and left_points[n][1] > VISIBILITY_THRESHOLD for n in (num_joint, den_joint)):
        return None
    if not all(n in right_points and right_points[n][1] > VISIBILITY_THRESHOLD for n in (num_joint, den_joint)):
        return None

    numerator_distance = abs(left_points[num_joint][0][0] - right_points[num_joint][0][0])
    denominator_distance = abs(left_points[den_joint][0][0] - right_points[den_joint][0][0])
    if denominator_distance == 0:
        return None

    return numerator_distance / denominator_distance


def compute_vertical_ratio(check_def, left_points, right_points):
    num_j1, num_j2 = check_def["numerator_joints"]
    den_j1, den_j2 = check_def["denominator_joints"]

    def side_ratio(side_points):
        required_names = (num_j1, num_j2, den_j1, den_j2)
        if not all(n in side_points and side_points[n][1] > VISIBILITY_THRESHOLD for n in required_names):
            return None

        denominator = abs(side_points[den_j1][0][1] - side_points[den_j2][0][1])
        if denominator == 0:
            return None

        numerator = abs(side_points[num_j1][0][1] - side_points[num_j2][0][1])
        return numerator / denominator

    return blend_side_values(
        side_ratio(left_points),
        side_ratio(right_points),
        left_points,
        right_points,
        (num_j1, num_j2, den_j1, den_j2),
    )


def compute_signed_line_offset(check_def, left_points, right_points):
    """
    Offset of the middle joint from the line of the other two, divided by
    that line's length. Positive means the joint is lower on the image
    (hip sag in a side-on plank), independent of which way the person faces.
    """
    a_name, b_name, c_name = check_def["points"]

    def side_offset(side_points):
        required_names = (a_name, b_name, c_name)
        if not all(n in side_points and side_points[n][1] > VISIBILITY_THRESHOLD for n in required_names):
            return None

        # Use Z and Y (body's sagittal plane)
        az, ay = side_points[a_name][0][2], side_points[a_name][0][1]
        bz, by = side_points[b_name][0][2], side_points[b_name][0][1]
        cz, cy = side_points[c_name][0][2], side_points[c_name][0][1]
        dz, dy = cz - az, cy - ay
        length_sq = dz * dz + dy * dy
        if length_sq == 0:
            return None

        t = ((bz - az) * dz + (by - ay) * dy) / length_sq
        proj_y = ay + t * dy
        length = length_sq ** 0.5
        return (by - proj_y) / length

    return blend_side_values(
        side_offset(left_points),
        side_offset(right_points),
        left_points,
        right_points,
        (a_name, b_name, c_name),
    )


def compute_extreme_side_angle(check_def, left_points, right_points, extreme="min"):
    left_angle = compute_side_angle(check_def, left_points)
    right_angle = compute_side_angle(check_def, right_points)
    values = [v for v in (left_angle, right_angle) if v is not None]
    if not values:
        return None
    return min(values) if extreme == "min" else max(values)


def compute_vertical_angle(check_def, left_points, right_points):
    """Degrees from gravity-vertical (0 = pointing straight down)."""
    a_name, b_name = check_def["points"]

    def side_angle(side_points):
        if not all(n in side_points and side_points[n][1] > VISIBILITY_THRESHOLD for n in (a_name, b_name)):
            return None
        ax, ay, az = side_points[a_name][0][:3]
        bx, by, bz = side_points[b_name][0][:3]
        vx, vy, vz = ax - bx, ay - by, az - bz
        length = (vx * vx + vy * vy + vz * vz) ** 0.5
        if length == 0:
            return None
        cosang = float(np.clip(-vy / length, -1.0, 1.0))
        return float(np.degrees(np.arccos(cosang)))

    return blend_side_values(
        side_angle(left_points),
        side_angle(right_points),
        left_points,
        right_points,
        (a_name, b_name),
    )


def compute_forward_offset(check_def, left_points, right_points):
    """How far `front` is ahead of `ref` along the hip-to-ref facing direction."""
    hip_name, front_name, ref_name = check_def["points"]

    def side_offset(side_points):
        names = (hip_name, front_name, ref_name)
        if not all(n in side_points and side_points[n][1] > VISIBILITY_THRESHOLD for n in names):
            return None
        hx, hy, hz = side_points[hip_name][0][:3]
        fx, fy, fz = side_points[front_name][0][:3]
        rx, ry, rz = side_points[ref_name][0][:3]
        
        scale = ((rx - hx) ** 2 + (ry - hy) ** 2 + (rz - hz) ** 2) ** 0.5
        if scale == 0:
            return None
        return (rz - fz) / scale

    return blend_side_values(
        side_offset(left_points),
        side_offset(right_points),
        left_points,
        right_points,
        (hip_name, front_name, ref_name),
    )


def compute_segment_align(check_def, left_points, right_points):
    """|dx| / segment length. 0 means the two joints are stacked in x (shoulder over elbow)."""
    a_name, b_name = check_def["points"]

    def side_align(side_points):
        if not all(n in side_points and side_points[n][1] > VISIBILITY_THRESHOLD for n in (a_name, b_name)):
            return None
        ax, ay, az = side_points[a_name][0][:3]
        bx, by, bz = side_points[b_name][0][:3]
        
        length = ((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2) ** 0.5
        if length == 0:
            return None
            
        drift = ((ax - bx) ** 2 + (az - bz) ** 2) ** 0.5
        return drift / length

    return blend_side_values(
        side_align(left_points),
        side_align(right_points),
        left_points,
        right_points,
        (a_name, b_name),
    )


CHECK_COMPUTERS = {
    "angle": lambda check_def, landmarks, left_points, right_points, exercise_config, w, h: (
        blend_side_values(
            compute_side_angle(check_def, left_points),
            compute_side_angle(check_def, right_points),
            left_points,
            right_points,
            check_def["points"],
        )
    ),
    "min_angle": lambda check_def, landmarks, left_points, right_points, exercise_config, w, h: (
        compute_extreme_side_angle(check_def, left_points, right_points, "min")
    ),
    "max_angle": lambda check_def, landmarks, left_points, right_points, exercise_config, w, h: (
        compute_extreme_side_angle(check_def, left_points, right_points, "max")
    ),
    "horizontal_ratio": lambda check_def, landmarks, left_points, right_points, exercise_config, w, h: (
        compute_horizontal_ratio(check_def, left_points, right_points)
    ),
    "vertical_ratio": lambda check_def, landmarks, left_points, right_points, exercise_config, w, h: (
        compute_vertical_ratio(check_def, left_points, right_points)
    ),
    "angle_asymmetry": lambda check_def, landmarks, left_points, right_points, exercise_config, w, h: (
        compute_angle_asymmetry(check_def, left_points, right_points)
    ),
    "signed_line_offset": lambda check_def, landmarks, left_points, right_points, exercise_config, w, h: (
        compute_signed_line_offset(check_def, left_points, right_points)
    ),
    "vertical_angle": lambda check_def, landmarks, left_points, right_points, exercise_config, w, h: (
        compute_vertical_angle(check_def, left_points, right_points)
    ),
    "forward_offset": lambda check_def, landmarks, left_points, right_points, exercise_config, w, h: (
        compute_forward_offset(check_def, left_points, right_points)
    ),
    "segment_align": lambda check_def, landmarks, left_points, right_points, exercise_config, w, h: (
        compute_segment_align(check_def, left_points, right_points)
    ),
}


def _average_of_sides(left_val, right_val):
    values = [v for v in (left_val, right_val) if v is not None]
    return sum(values) / len(values) if values else None


def compute_all_checks(landmarks, exercise_config, w, h, world_landmarks=None):
    if world_landmarks is not None:
        left_world = get_side_points(
            world_landmarks, exercise_config["landmarks"]["left"], None, None
        )
        right_world = get_side_points(
            world_landmarks, exercise_config["landmarks"]["right"], None, None
        )
    else:
        left_world = get_side_points(landmarks, exercise_config["landmarks"]["left"], w, h)
        right_world = get_side_points(landmarks, exercise_config["landmarks"]["right"], w, h)

    raw_checks = {}
    for check_name, check_def in exercise_config["checks"].items():
        check_type = check_def["type"]
        computer = CHECK_COMPUTERS[check_type]
        raw_checks[check_name] = computer(
            check_def, landmarks, left_world, right_world, exercise_config, w, h
        )
        if check_type in ("angle", "min_angle", "max_angle") and "points" in check_def:
            raw_checks[f"{check_name}_left"] = compute_side_angle(check_def, left_world)
            raw_checks[f"{check_name}_right"] = compute_side_angle(check_def, right_world)

    return raw_checks


def smooth_checks(raw_checks, check_history):
    smoothed = {}
    for check_name, raw_value in raw_checks.items():
        history = check_history.setdefault(check_name, [])
        if raw_value is None:
            smoothed[check_name] = None
            continue

        history.append(raw_value)
        if len(history) > SMOOTHING_WINDOW:
            history.pop(0)
        smoothed[check_name] = sum(history) / len(history)

    return smoothed


def status_from_values(exercise_config, values):
    checked_names = exercise_config["depth_checks"] + exercise_config.get("fault_checks", [])
    status = {}
    for check_name in checked_names:
        check_def = exercise_config["checks"][check_name]
        threshold = check_def["down_threshold"]
        direction = check_def.get("direction", "below")
        value = values.get(check_name)

        if direction == "above":
            status[check_name] = value is not None and value > threshold
        else:
            status[check_name] = value is not None and value < threshold

    return status


def evaluate_feedback(exercise_config, min_in_rep, max_in_rep, counter):
    values = {}
    checked_names = exercise_config["depth_checks"] + exercise_config.get("fault_checks", [])
    for check_name in checked_names:
        direction = exercise_config["checks"][check_name].get("direction", "below")
        values[check_name] = (
            max_in_rep.get(check_name) if direction == "above" else min_in_rep.get(check_name)
        )

    status = status_from_values(exercise_config, values)
    side = working_side_label(min_in_rep, exercise_config.get("side_check", "knee"))
    for rule in exercise_config["feedback_rules"]:
        if all(status.get(k) == v for k, v in rule["require"].items()):
            return rule["message"].format(count=counter, side=side), rule["counts_as_good"]

    return exercise_config["default_message"].format(count=counter, side=side), False


def evaluate_live_feedback(exercise_config, checks):
    status = status_from_values(exercise_config, checks)
    side = working_side_label(checks, exercise_config.get("side_check", "knee"))
    for rule in exercise_config["feedback_rules"]:
        if all(status.get(k) == v for k, v in rule["require"].items()):
            return rule["message"].format(count=0, side=side), rule["counts_as_good"]

    return exercise_config["default_message"].format(count=0, side=side), False


def working_side_label(values, check_name):
    left = values.get(f"{check_name}_left")
    right = values.get(f"{check_name}_right")
    if left is None or right is None:
        return "both sides"
    if left < right - 8:
        return "left"
    if right < left - 8:
        return "right"
    return "both sides"


def format_check_value(check_name, value, exercise_config):
    check_type = exercise_config["checks"][check_name]["type"]
    if check_type in ("angle", "angle_asymmetry", "min_angle", "max_angle", "vertical_angle"):
        return f"{name_label(check_name)}: {int(value)}"
    return f"{name_label(check_name)}: {value:.2f}"


def name_label(check_name):
    return check_name.replace("_", " ").capitalize()


def play_tone(kind):
    try:
        import winsound
        freq = {"good": 880, "fault": 420, "rest": 660, "ready": 740}.get(kind, 600)
        duration = 90 if kind == "good" else 140
        winsound.Beep(freq, duration)
    except Exception:
        pass


def apply_baselines(checks, baselines, exercise_config):
    if not baselines:
        return checks
    adjusted = dict(checks)
    for name, value in checks.items():
        check_def = exercise_config["checks"].get(name)
        if value is None or not check_def:
            continue
        if check_def["type"] in ("signed_line_offset", "vertical_angle", "forward_offset"):
            base = baselines.get(name)
            if base is not None:
                adjusted[name] = value - base
    return adjusted


def primary_visible(landmarks, exercise_config, w, h):
    primary = exercise_config["checks"][exercise_config["primary_check"]]
    names = primary.get("points") or tuple(exercise_config["landmarks"]["left"])
    left = get_side_points(landmarks, exercise_config["landmarks"]["left"], w, h)
    right = get_side_points(landmarks, exercise_config["landmarks"]["right"], w, h)
    return (
        side_min_confidence(left, names) > VISIBILITY_THRESHOLD
        or side_min_confidence(right, names) > VISIBILITY_THRESHOLD
    )


def pose_confidence(landmarks, exercise_config):
    names = exercise_config["checks"][exercise_config["primary_check"]].get("points")
    if not names:
        names = tuple(exercise_config["landmarks"]["left"])
    left_map = exercise_config["landmarks"]["left"]
    right_map = exercise_config["landmarks"]["right"]
    scores = []
    for name in names:
        for side_map in (left_map, right_map):
            idx = side_map.get(name)
            if idx is None or idx >= len(landmarks):
                continue
            scores.append(landmark_confidence(landmarks[idx]))
    return sum(scores) / len(scores) if scores else 0.0


def note_cue(session, message, is_good, voice=True):
    if not message:
        return
    key = message.split(":")[-1].strip() if ":" in message else message
    session["cue_counts"][key] = session["cue_counts"].get(key, 0) + 1
    if is_good:
        play_tone("good")
    else:
        play_tone("fault")
    if voice:
        speak(spoken_from_message(message))


def maybe_start_rest(session, exercise_config, now):
    set_size = exercise_config.get("set_size") or 0
    rest_seconds = exercise_config.get("rest_seconds") or 0
    if set_size <= 0 or rest_seconds <= 0:
        return
    if session["counter"] > 0 and session["counter"] % set_size == 0:
        session["phase"] = "rest"
        session["rest_until"] = now + rest_seconds
        play_tone("rest")


def finish_rep(session, exercise_config, now):
    session["counter"] += 1
    if session.get("down_t0"):
        eccentric = now - session["down_t0"]
        session["eccentric_times"].append(eccentric)
        session["down_t0"] = None
        if eccentric < 0.45 and now - session.get("last_tempo_cue", 0) > 8:
            session["last_tempo_cue"] = now
            speak("Slower on the way down")
            session["feedback_msg"] = "Slow the lowering — control the eccentric"
            session["feedback_until"] = now + 2.0

    feedback_msg, is_good = evaluate_feedback(
        exercise_config, session["min_in_rep"], session["max_in_rep"], session["counter"]
    )
    if is_good:
        session["good_counter"] += 1
    else:
        session["worst_cue"] = feedback_msg
    side = working_side_label(
        session.get("min_in_rep") or {}, exercise_config.get("side_check", "knee")
    )
    stats = session.setdefault(
        "side_stats", {"left": {"reps": 0, "good": 0}, "right": {"reps": 0, "good": 0}}
    )
    if side in ("left", "right"):
        stats[side]["reps"] += 1
        if is_good:
            stats[side]["good"] += 1
    session["recent_quality"].append(is_good)
    session["recent_quality"] = session["recent_quality"][-6:]
    session["feedback_msg"] = feedback_msg
    session["feedback_until"] = now + 2.5
    note_cue(session, feedback_msg, is_good, voice=session.get("voice", True))
    session["min_in_rep"] = {}
    session["max_in_rep"] = {}

    if (
        len(session["recent_quality"]) >= 4
        and session["counter"] >= 4
        and sum(1 for q in session["recent_quality"][-4:] if q) <= 1
    ):
        session["ended_reason"] = "form_fade"
        session["phase"] = "done"
        speak("Stop the set. Form is fading. That's enough for today on this move.")
        return

    target = session.get("target_reps") or 0
    if target and session["counter"] >= target:
        session["ended_reason"] = "target"
        session["phase"] = "done"
        speak("Set complete. Nice work.")
        return

    maybe_start_rest(session, exercise_config, now)


def accumulate_extrema(session, checks):
    for name, val in checks.items():
        if val is None:
            continue
        if name not in session["min_in_rep"] or val < session["min_in_rep"][name]:
            session["min_in_rep"][name] = val
        if name not in session["max_in_rep"] or val > session["max_in_rep"][name]:
            session["max_in_rep"][name] = val


def update_rep_session(session, checks, exercise_config, now):
    primary_check_name = exercise_config["primary_check"]
    primary_def = exercise_config["checks"][primary_check_name]
    primary_value = checks.get(primary_check_name)
    if primary_value is None:
        return

    count_on = exercise_config.get("count_on", "return_to_up")
    stage = session["stage"]

    candidate = stage
    if stage == "down" and primary_value > primary_def["up_threshold"]:
        candidate = "up"
    elif stage == "up" and primary_value < primary_def["down_threshold"]:
        candidate = "down"

    if candidate != stage:
        if session.get("stage_candidate") == candidate:
            session["stage_candidate_count"] = session.get("stage_candidate_count", 0) + 1
        else:
            session["stage_candidate"] = candidate
            session["stage_candidate_count"] = 1
    else:
        session["stage_candidate"] = None
        session["stage_candidate_count"] = 0

    if session.get("stage_candidate_count", 0) >= 3:
        new_stage = session["stage_candidate"]
        session["stage_candidate"] = None
        session["stage_candidate_count"] = 0

        if count_on == "reach_up":
            if stage == "down" and new_stage == "up":
                session["stage"] = "up"
                finish_rep(session, exercise_config, now)
            elif stage == "up" and new_stage == "down":
                session["stage"] = "down"
                session["down_t0"] = now
                session["min_in_rep"] = {n: v for n, v in checks.items() if v is not None}
                session["max_in_rep"] = dict(session["min_in_rep"])
        else:
            if stage == "up" and new_stage == "down":
                session["stage"] = "down"
                session["down_t0"] = now
                session["min_in_rep"] = {n: v for n, v in checks.items() if v is not None}
                session["max_in_rep"] = dict(session["min_in_rep"])
            elif stage == "down" and new_stage == "up":
                session["stage"] = "up"
                finish_rep(session, exercise_config, now)

    if session["stage"] == "down":
        accumulate_extrema(session, checks)


def update_hold_session(session, checks, exercise_config, dt):
    primary_check_name = exercise_config["primary_check"]
    primary_def = exercise_config["checks"][primary_check_name]
    primary_value = checks.get(primary_check_name)
    if primary_value is None:
        session["stage"] = "rest"
        session["feedback_msg"] = exercise_config.get(
            "not_visible_message", "Body not clearly visible"
        )
        return

    hold_direction = exercise_config.get("hold_direction", "above")
    prev_stage = session["stage"]
    candidate = prev_stage
    
    if hold_direction == "below":
        if prev_stage == "rest" and primary_value < primary_def["down_threshold"]:
            candidate = "hold"
        elif prev_stage == "hold" and primary_value > primary_def["up_threshold"]:
            candidate = "rest"
    else:
        if prev_stage == "rest" and primary_value > primary_def["up_threshold"]:
            candidate = "hold"
        elif prev_stage == "hold" and primary_value < primary_def["down_threshold"]:
            candidate = "rest"

    if candidate != prev_stage:
        if session.get("stage_candidate") == candidate:
            session["stage_candidate_count"] = session.get("stage_candidate_count", 0) + 1
        else:
            session["stage_candidate"] = candidate
            session["stage_candidate_count"] = 1
    else:
        session["stage_candidate"] = None
        session["stage_candidate_count"] = 0

    if session.get("stage_candidate_count", 0) >= 3:
        session["stage"] = session["stage_candidate"]
        session["stage_candidate"] = None
        session["stage_candidate_count"] = 0

    feedback_msg, is_good = evaluate_live_feedback(exercise_config, checks)
    if feedback_msg != session.get("last_hold_msg"):
        if session["stage"] == "hold" and session.get("last_hold_good") is True and not is_good:
            note_cue(session, feedback_msg, False, voice=session.get("voice", True))
        elif session["stage"] == "hold" and is_good and session.get("last_hold_good") is False:
            play_tone("good")
        session["last_hold_msg"] = feedback_msg
        session["last_hold_good"] = is_good
        if not is_good:
            session["cue_counts"][feedback_msg] = session["cue_counts"].get(feedback_msg, 0) + 1
            session["worst_cue"] = feedback_msg

    session["feedback_msg"] = feedback_msg
    session["feedback_until"] = time.time() + 0.3

    if session["stage"] == "hold":
        session["hold_time"] += dt
        if is_good:
            session["good_time"] += dt
        target_hold = session.get("target_hold") or 0
        if target_hold and session["good_time"] >= target_hold:
            session["ended_reason"] = "target"
            session["phase"] = "done"
            speak("Hold complete. Come out slowly.")


def draw_hud(frame, session, checks, feedback_msg, exercise_config):
    mode = exercise_config.get("mode", "reps")
    phase = session.get("phase", "active")
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 145), (0, 0, 0), -1)

    if mode == "hold":
        cv2.putText(frame, "HOLD", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(frame, f"{session['hold_time']:.1f}s", (15, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 2)
        cv2.putText(frame, "GOOD FORM", (160, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, f"{session['good_time']:.1f}s", (160, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 200, 255), 2)
    else:
        cv2.putText(frame, "REPS", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(frame, str(session["counter"]), (15, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)
        cv2.putText(frame, "GOOD", (110, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, str(session["good_counter"]), (110, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 200, 255), 2)
        set_size = exercise_config.get("set_size") or 0
        if set_size:
            in_set = session["counter"] % set_size
            if in_set == 0 and session["counter"]:
                in_set = set_size
            cv2.putText(frame, f"SET {session['counter'] // set_size + (0 if in_set == set_size and session['counter'] else 1)}  {in_set}/{set_size}",
                        (175, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)

    cv2.putText(frame, phase.upper(), (frame.shape[1] - 160, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
    cv2.putText(frame, session["stage"].upper(), (frame.shape[1] - 160, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    side_check = exercise_config.get("side_check")
    if side_check:
        left = checks.get(f"{side_check}_left")
        right = checks.get(f"{side_check}_right")
        if left is not None or right is not None:
            left_txt = "--" if left is None else str(int(left))
            right_txt = "--" if right is None else str(int(right))
            cv2.putText(frame, f"L {side_check} {left_txt}   R {side_check} {right_txt}",
                        (15, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 255, 180), 1)

    check_parts = [
        format_check_value(name, value, exercise_config)
        for name, value in checks.items()
        if name in exercise_config["checks"] and value is not None
    ]
    if check_parts:
        cv2.putText(frame, "  ".join(check_parts[:5]), (15, 112),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

    if feedback_msg:
        cv2.putText(frame, feedback_msg, (15, 136),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

    if session.get("uncertain"):
        overlay = frame.copy()
        y0, y1 = 145, 248
        cv2.rectangle(overlay, (0, y0), (frame.shape[1], y1), (20, 20, 90), -1)
        cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)
        cv2.putText(frame, "I'm not sure — I will not count this",
                    (15, 182), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 80, 255), 2)
        cv2.putText(frame, "Step back. Full body in the frame. Better light.",
                    (15, 218), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (230, 230, 255), 1)

    ecc = session.get("eccentric_times") or []
    if ecc:
        cv2.putText(frame, f"Last lower: {ecc[-1]:.1f}s",
                    (frame.shape[1] - 220, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    view = exercise_config.get("view", "")
    if view:
        hint = "SIDEWAYS to camera" if view == "side" else "FACE the camera"
        cv2.putText(frame, f"View: {hint}   q=quit  r=reset  space=skip rest",
                    (15, frame.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (230, 230, 230), 1)


def draw_banner(frame, title, subtitle=""):
    overlay = frame.copy()
    cv2.rectangle(overlay, (40, 160), (frame.shape[1] - 40, 320), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    cv2.putText(frame, title, (60, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 255), 2)
    if subtitle:
        cv2.putText(frame, subtitle, (60, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)


def session_record(session, exercise_config):
    cues = sorted(session.get("cue_counts", {}).items(), key=lambda item: item[1], reverse=True)
    return {
        "exercise": exercise_config.get("display_name"),
        "exercise_id": exercise_config.get("id"),
        "mode": exercise_config.get("mode", "reps"),
        "reps": session["counter"],
        "good_reps": session["good_counter"],
        "hold_time": round(session["hold_time"], 1),
        "good_time": round(session["good_time"], 1),
        "avg_eccentric": round(
            sum(session["eccentric_times"]) / len(session["eccentric_times"]), 2
        ) if session.get("eccentric_times") else None,
        "ended_reason": session.get("ended_reason"),
        "top_cues": [{"cue": cue, "count": count} for cue, count in cues[:5]],
        "worst_cue": session.get("worst_cue") or "",
        "side_stats": session.get("side_stats") or {},
    }


def draw_summary(frame, session, exercise_config):
    record = session_record(session, exercise_config)
    overlay = frame.copy()
    cv2.rectangle(overlay, (30, 80), (frame.shape[1] - 30, frame.shape[0] - 40), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    y = 130
    cv2.putText(frame, f"{record['exercise']} session", (50, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
    y += 45
    if record["mode"] == "hold":
        lines = [
            f"Hold time: {record['hold_time']}s",
            f"Good form: {record['good_time']}s",
        ]
    else:
        lines = [
            f"Reps: {record['reps']}",
            f"Good reps: {record['good_reps']}",
        ]
    if record["top_cues"]:
        lines.append("Top cues:")
        for item in record["top_cues"][:4]:
            lines.append(f"  {item['count']}x  {item['cue']}")
    lines.append("Saved to data/history.jsonl   press any key")
    for line in lines:
        cv2.putText(frame, line, (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        y += 32


def print_summary(record):
    print()
    print(f"=== {record['exercise']} ===")
    if record["mode"] == "hold":
        print(f"Hold: {record['hold_time']}s   good form: {record['good_time']}s")
    else:
        print(f"Reps: {record['reps']}   good: {record['good_reps']}")
    if record["top_cues"]:
        print("Top cues:")
        for item in record["top_cues"]:
            print(f"  {item['count']}x {item['cue']}")
    if record.get("worst_cue"):
        print(f"Rough-rep cue: {record['worst_cue']}")
    print()


def reset_session(exercise_config):
    return {
        "counter": 0,
        "good_counter": 0,
        "hold_time": 0.0,
        "good_time": 0.0,
        "stage": exercise_config.get("initial_stage", "up"),
        "phase": "setup",
        "check_history": {},
        "min_in_rep": {},
        "max_in_rep": {},
        "feedback_msg": "",
        "feedback_until": 0,
        "pose_ema": {},
        "cue_counts": {},
        "baselines": {},
        "calibrate_samples": [],
        "visible_since": None,
        "calibrate_started": None,
        "rest_until": 0,
        "last_hold_msg": "",
        "last_hold_good": None,
        "voice": True,
        "recent_quality": [],
        "eccentric_times": [],
        "down_t0": None,
        "last_tempo_cue": 0,
        "ended_reason": None,
        "target_reps": 0,
        "target_hold": 0,
        "uncertain": False,
        "worst_cue": "",
        "side_stats": {"left": {"reps": 0, "good": 0}, "right": {"reps": 0, "good": 0}},
    }


def apply_calibration(cfg, baselines):
    primary = cfg["primary_check"]
    primary_def = cfg["checks"][primary]
    base = baselines.get(primary)
    if base is None:
        return
    mode = cfg.get("mode", "reps")
    if mode == "hold" and cfg.get("hold_direction", "above") == "above":
        primary_def["up_threshold"] = max(base - 10, primary_def.get("up_threshold") or 0)
        primary_def["down_threshold"] = max(base - 20, (primary_def.get("down_threshold") or 0) - 5)
    elif mode == "hold":
        primary_def["down_threshold"] = min(base + 8, primary_def.get("down_threshold") or base)
        primary_def["up_threshold"] = max(base + 25, primary_def.get("up_threshold") or base)
    elif cfg.get("count_on") == "reach_up":
        primary_def["down_threshold"] = min(primary_def["down_threshold"], base + 15)
        primary_def["up_threshold"] = max(primary_def.get("up_threshold") or 0, base + 40)
    else:
        primary_def["up_threshold"] = min(primary_def.get("up_threshold") or base, max(base - 12, 140))


def run_exercise(exercise_config, options=None):
    options = options or {}
    cfg = copy.deepcopy(exercise_config)
    if options.get("set_size"):
        cfg["set_size"] = options["set_size"]
    if options.get("rest_seconds") is not None:
        cfg["rest_seconds"] = options["rest_seconds"]

    prefer_full = options.get("prefer_full", True)
    model_path = resolve_model_path(prefer_full=prefer_full)
    if not os.path.exists(model_path):
        print(f"Model file not found: {model_path}")
        print("Need pose_landmarker_full.task or pose_landmarker_lite.task in models/.")
        return None

    print(f"Pose model: {os.path.basename(model_path)}")
    mode = cfg.get("mode", "reps")
    calibrate_seconds = cfg.get("calibrate_seconds", 2.5)
    teach_text = options.get("teach") or cfg.get("teach") or cfg.get("setup_hint", "")
    teach_seconds = options.get("teach_seconds", 6)
    voice = options.get("voice", True)
    configure_voice(
        options.get("voice_mode") or "full",
        options.get("cue_gap_seconds") or 4.0,
        options.get("voice_gender") or "Female",
    )
    auto_finish = options.get("auto_finish", False)
    wait_summary = options.get("wait_summary", True)
    save_history = options.get("save_history", True)

    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    mp_options = mp_vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_poses=1,
    )
    landmarker = mp_vision.PoseLandmarker.create_from_options(mp_options)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        print("Could not open the camera.")
        landmarker.close()
        return None

    start_time = time.time()
    last_frame_time = start_time
    session = reset_session(cfg)
    session["voice"] = voice
    session["target_reps"] = options.get("target_reps") or 0
    session["target_hold"] = options.get("target_hold") or 0
    
    demo_cap = None
    video_path = os.path.join(PROJECT_ROOT, "videos", f"{cfg.get('id', '')}.mp4")
    if os.path.exists(video_path):
        demo_cap = cv2.VideoCapture(video_path)

    if teach_text:
        session["phase"] = "teach"
        session["teach_until"] = start_time + teach_seconds
        if voice:
            speak(teach_text)
    window_name = f"{cfg['display_name']} Coach"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    last_frame = None
    record = None
    # Clip preview removed for privacy

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            now = time.time()
            dt = max(0.0, now - last_frame_time)
            last_frame_time = now

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            last_frame = frame

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            timestamp_ms = int((now - start_time) * 1000)

            result = landmarker.detect_for_video(mp_image, timestamp_ms)
            checks = {name: None for name in cfg["checks"]}
            body_ok = False
            session["uncertain"] = False

            if result.pose_landmarks:
                landmarks = smooth_pose_landmarks(result.pose_landmarks[0], session["pose_ema"])
                world_landmarks = (
                    result.pose_world_landmarks[0] if result.pose_world_landmarks else None
                )
                draw_landmarks(frame, landmarks, cfg)
                draw_exercise_guides(frame, landmarks, cfg, w, h)
                body_ok = primary_visible(landmarks, cfg, w, h)
                confidence = pose_confidence(landmarks, cfg)
                session["uncertain"] = confidence < UNCERTAIN_THRESHOLD
                raw_checks = compute_all_checks(landmarks, cfg, w, h, world_landmarks)
                checks = apply_baselines(
                    smooth_checks(raw_checks, session["check_history"]),
                    session["baselines"],
                    cfg,
                )
            else:
                session["visible_since"] = None
                session["uncertain"] = True
                if mode == "hold" and session["phase"] == "active":
                    session["stage"] = "rest"
                cv2.putText(frame, "Body not detected", (20, 170),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            if session["phase"] == "teach":
                video_finished = False
                if demo_cap is not None and demo_cap.isOpened():
                    ret, demo_frame = demo_cap.read()
                    if not ret:
                        video_finished = True
                    else:
                        demo_frame = cv2.resize(demo_frame, (w, h))
                        frame = demo_frame
                        
                draw_banner(frame, cfg["display_name"], teach_text[:70] + " (SPACE to skip)")
                
                if demo_cap is not None and demo_cap.isOpened():
                    if video_finished:
                        session["phase"] = "setup"
                else:
                    if now >= session.get("teach_until", 0):
                        session["phase"] = "setup"

            elif session["phase"] == "setup":
                view = cfg.get("view", "side")
                title = "Face the CAMERA" if view == "front" else "Turn SIDEWAYS"
                draw_banner(
                    frame,
                    title,
                    cfg.get("setup_hint") or "Full body in frame, good lighting",
                )
                if body_ok and not session["uncertain"]:
                    if session["visible_since"] is None:
                        session["visible_since"] = now
                    elif now - session["visible_since"] >= 0.8:
                        session["phase"] = "calibrate"
                        session["calibrate_started"] = now
                        session["calibrate_samples"] = []
                        play_tone("ready")
                        if voice:
                            speak("Hold still. Calibrating.")
                else:
                    session["visible_since"] = None

            elif session["phase"] == "calibrate":
                remaining = calibrate_seconds - (now - (session["calibrate_started"] or now))
                draw_banner(
                    frame,
                    f"Hold still  {max(0, remaining):.1f}s",
                    cfg.get("calibrate_hint") or "Stay in the start pose",
                )
                if body_ok:
                    session["calibrate_samples"].append(
                        {k: v for k, v in checks.items() if k in cfg["checks"] and v is not None}
                    )
                if remaining <= 0:
                    samples = session["calibrate_samples"]
                    baselines = {}
                    if samples:
                        keys = set().union(*[s.keys() for s in samples])
                        for key in keys:
                            vals = [s[key] for s in samples if key in s]
                            if vals:
                                baselines[key] = sum(vals) / len(vals)
                    session["baselines"] = baselines
                    apply_calibration(cfg, baselines)
                    session["phase"] = "active"
                    session["stage"] = cfg.get("initial_stage", "up")
                    play_tone("good")
                    if voice:
                        speak("Go.")

            elif session["phase"] == "rest":
                left = max(0.0, session["rest_until"] - now)
                draw_banner(frame, f"Rest  {left:.0f}s", "Breathe. Press space to skip.")
                if left <= 0:
                    session["phase"] = "active"
                    play_tone("ready")
                    if voice:
                        speak("Next set.")

            elif session["phase"] == "active" and body_ok and not session["uncertain"]:
                if mode == "hold":
                    update_hold_session(session, checks, cfg, dt)
                else:
                    update_rep_session(session, checks, cfg, now)
            elif session["phase"] == "active" and session["uncertain"]:
                session["feedback_msg"] = "Not sure — I won't count this"

            elif session["phase"] == "done":
                if auto_finish:
                    break

            active_feedback = session["feedback_msg"] if now < session["feedback_until"] else ""
            if mode == "hold" and session["phase"] == "active" and session["feedback_msg"]:
                if not session["uncertain"]:
                    active_feedback = session["feedback_msg"]

            draw_hud(frame, session, checks, active_feedback, cfg)
            cv2.imshow(window_name, frame)

            key = cv2.waitKey(5) & 0xFF
            if key == ord("q"):
                session["ended_reason"] = session.get("ended_reason") or "quit"
                stop_voice()
                break
            if key == ord("r"):
                cfg = copy.deepcopy(exercise_config)
                session = reset_session(cfg)
                session["voice"] = voice
                session["target_reps"] = options.get("target_reps") or 0
                session["target_hold"] = options.get("target_hold") or 0
            if key == ord(" "):
                if session["phase"] == "rest":
                    session["phase"] = "active"
                elif session["phase"] == "teach":
                    session["phase"] = "setup"
            if key == ord("c") and session["phase"] in ("setup", "calibrate", "teach"):
                session["phase"] = "active"
                session["stage"] = cfg.get("initial_stage", "up")

        record = session_record(session, cfg)
        record["worst_cue"] = session.get("worst_cue") or ""
        print_summary(record)
        if save_history:
            try:
                path = append_session(record)
                print(f"Saved {path}")
            except OSError as exc:
                print(f"Could not save history: {exc}")

        if wait_summary and last_frame is not None:
            draw_summary(last_frame, session, cfg)
            cv2.imshow(window_name, last_frame)
            cv2.waitKey(0)

    finally:
        if demo_cap is not None:
            demo_cap.release()
        if session.get("ended_reason") == "quit":
            stop_voice()
        landmarker.close()
        cap.release()
        cv2.destroyAllWindows()

    return record
