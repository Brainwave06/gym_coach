import math
import os
import time

import cv2
import numpy as np

from common.models import resolve_model_path
from common.voice import speak, stop_voice

DRILLS = [
    {
        "name": "March in place",
        "seconds": 30,
        "cue": "March in place. Opposite arm and leg. Stay tall.",
        "tips": ["Lift knees, not just the feet", "Swing the opposite arm", "Soft landing"],
        "kind": "march",
    },
    {
        "name": "Arm circles",
        "seconds": 30,
        "cue": "Big arm circles. Slow and controlled.",
        "tips": ["Arms long, circles from the shoulder", "Don't shrug", "Breathe easy"],
        "kind": "circles",
    },
    {
        "name": "Hip openers",
        "seconds": 30,
        "cue": "Open the hips. Knee up, then out to the side.",
        "tips": ["Hold a wall if you need balance", "Chest stays facing forward", "No sharp pain"],
        "kind": "hips",
    },
]

RECOVERY = [
    {
        "name": "Easy march",
        "seconds": 90,
        "cue": "Easy march. This is recovery, not a workout.",
        "tips": ["Soft steps", "Breathe through the nose", "No rushing"],
        "kind": "march",
    },
    {
        "name": "Hip openers",
        "seconds": 90,
        "cue": "Open the hips slowly. Stop before pain.",
        "tips": ["Hold a wall", "Chest forward", "No bouncing"],
        "kind": "hips",
    },
    {
        "name": "Shoulder rolls",
        "seconds": 90,
        "cue": "Slow shoulder rolls. Unclench the jaw.",
        "tips": ["Big circles", "Neck long", "Easy breath"],
        "kind": "circles",
    },
    {
        "name": "Breathe",
        "seconds": 90,
        "cue": "Stand still. Long breath out.",
        "tips": ["Longer exhale", "Shoulders down", "You're recovering"],
        "kind": "breathe",
    },
]

COOLDOWN = [
    {
        "name": "Easy march",
        "seconds": 20,
        "cue": "Walk in place. Slow. Let the heart rate come down.",
        "tips": ["Soft steps", "Shoulders down", "Easy breath"],
        "kind": "march",
    },
    {
        "name": "Shoulder rolls",
        "seconds": 20,
        "cue": "Slow shoulder rolls. Big circles, no shrugging hard.",
        "tips": ["Roll back, then forward", "Neck stays long", "Unclench the jaw"],
        "kind": "circles",
    },
    {
        "name": "Breathe",
        "seconds": 20,
        "cue": "Stand still. In through the nose, out through the mouth.",
        "tips": ["Hands on ribs if you like", "Longer exhale than inhale", "You're done after this"],
        "kind": "breathe",
    },
]


def _rotate(point, origin, degrees, z_offset=0):
    rad = math.radians(degrees)
    px, py = point[0] - origin[0], point[1] - origin[1]
    return (
        int(origin[0] + px * math.cos(rad) - py * math.sin(rad)),
        int(origin[1] + px * math.sin(rad) + py * math.cos(rad)),
        origin[2] + z_offset
    )


def _add(a, b):
    # b is (dx, dy, dz)
    return (int(a[0] + b[0]), int(a[1] + b[1]), int(a[2] + b[2]))


def _stick_pose(cx, cy, kind, t):
    neck = (cx, cy - 70, 0)
    head = (cx, cy - 108, 0)
    l_sh, r_sh = (cx - 42, cy - 58, 0), (cx + 42, cy - 58, 0)
    mid_hip = (cx, cy + 28, 0)
    l_hip, r_hip = (cx - 22, cy + 32, 0), (cx + 22, cy + 32, 0)

    if kind == "march":
        swing = math.sin(t * 7.0)
        l_kn = _add(l_hip, (8 * swing, 62 - 28 * max(swing, 0), -40 * max(swing, 0)))
        r_kn = _add(r_hip, (-8 * swing, 62 - 28 * max(-swing, 0), -40 * max(-swing, 0)))
        l_ank = _add(l_kn, (6 * swing, 58 + 10 * min(swing, 0), 15 * swing))
        r_ank = _add(r_kn, (-6 * swing, 58 + 10 * min(-swing, 0), -15 * swing))
        l_el = _add(l_sh, (10, 48 + 22 * -swing, -30 * -swing))
        r_el = _add(r_sh, (-10, 48 + 22 * swing, -30 * swing))
        l_wr = _add(l_el, (8, 44 + 18 * -swing, -25 * -swing))
        r_wr = _add(r_el, (-8, 44 + 18 * swing, -25 * swing))
    elif kind == "circles":
        ang = (t * 140) % 360
        l_el = _rotate((l_sh[0], l_sh[1] + 55), l_sh, ang, -20 * math.cos(math.radians(ang)))
        l_wr = _rotate((l_sh[0], l_sh[1] + 105), l_sh, ang, -40 * math.cos(math.radians(ang)))
        r_el = _rotate((r_sh[0], r_sh[1] + 55), r_sh, ang + 180, -20 * math.cos(math.radians(ang + 180)))
        r_wr = _rotate((r_sh[0], r_sh[1] + 105), r_sh, ang + 180, -40 * math.cos(math.radians(ang + 180)))
        l_kn, r_kn = _add(l_hip, (0, 70, 0)), _add(r_hip, (0, 70, 0))
        l_ank, r_ank = _add(l_kn, (0, 62, 0)), _add(r_kn, (0, 62, 0))
    elif kind == "breathe":
        lift = 6 * math.sin(t * 1.4)
        neck = (cx, cy - 70 + int(lift * 0.3), 0)
        head = (cx, cy - 108 + int(lift * 0.3), 0)
        l_sh, r_sh = (cx - 42, cy - 58 + int(lift), 0), (cx + 42, cy - 58 + int(lift), 0)
        l_el, r_el = _add(l_sh, (-6, 70, 0)), _add(r_sh, (6, 70, 0))
        l_wr, r_wr = _add(l_el, (8, 8, 0)), _add(r_el, (0, 8, 0))
        l_kn, r_kn = _add(l_hip, (0, 70, 0)), _add(r_hip, (0, 70, 0))
        l_ank, r_ank = _add(l_kn, (0, 62, 0)), _add(r_kn, (0, 62, 0))
    else:
        phase = (math.sin(t * 2.2) + 1) / 2
        side = 1 if int(t * 0.35) % 2 == 0 else -1
        planted_hip = r_hip if side > 0 else l_hip
        lift_hip = l_hip if side > 0 else r_hip
        planted_kn = _add(planted_hip, (0, 70, 0))
        planted_ank = _add(planted_kn, (0, 62, 0))
        lift_kn = _add(lift_hip, (side * 18 * phase, 70 - 50 * phase, -40 * phase))
        lift_ank = _add(lift_kn, (side * 8, 40 * (1 - phase), 20 * phase))
        if side > 0:
            l_kn, l_ank, r_kn, r_ank = lift_kn, lift_ank, planted_kn, planted_ank
        else:
            r_kn, r_ank, l_kn, l_ank = lift_kn, lift_ank, planted_kn, planted_ank
        l_el, r_el = _add(l_sh, (-8, 70, 0)), _add(r_sh, (8, 70, 0))
        l_wr, r_wr = _add(l_el, (0, 8, 0)), _add(r_el, (0, 8, 0))

    return {
        "head": head, "neck": neck, "l_sh": l_sh, "r_sh": r_sh,
        "l_el": l_el, "r_el": r_el, "l_wr": l_wr, "r_wr": r_wr,
        "mid": mid_hip, "l_hip": l_hip, "r_hip": r_hip,
        "l_kn": l_kn, "r_kn": r_kn, "l_ank": l_ank, "r_ank": r_ank,
    }


def _draw_stick(frame, pose):
    bones = [
        ("head", "neck"), ("neck", "l_sh"), ("neck", "r_sh"),
        ("l_sh", "l_el"), ("l_el", "l_wr"), ("r_sh", "r_el"), ("r_el", "r_wr"),
        ("neck", "mid"), ("mid", "l_hip"), ("mid", "r_hip"),
        ("l_hip", "l_kn"), ("l_kn", "l_ank"), ("r_hip", "r_kn"), ("r_kn", "r_ank"),
    ]
    
    # Sort bones by average Z depth so closer bones are drawn on top
    bones_with_depth = []
    for a, b in bones:
        avg_z = (pose[a][2] + pose[b][2]) / 2.0
        bones_with_depth.append((avg_z, a, b))
    
    bones_with_depth.sort(key=lambda item: item[0], reverse=True) # Further away (positive z) drawn first
    
    for z, a, b in bones_with_depth:
        # Scale thickness and brightness by z
        scale = max(0.5, min(1.8, 1.0 - (z / 100.0)))
        thickness = max(2, int(6 * scale))
        shade = max(80, min(255, int(200 * scale)))
        color = (30, shade, shade + 35) # Cyan-ish 3D color
        cv2.line(frame, pose[a][:2], pose[b][:2], color, thickness, cv2.LINE_AA)
        
    # Draw head
    head_z = pose["head"][2]
    head_scale = max(0.5, min(1.8, 1.0 - (head_z / 100.0)))
    head_shade = max(80, min(255, int(200 * head_scale)))
    cv2.circle(frame, pose["head"][:2], int(18 * head_scale), (30, head_shade, head_shade + 35), int(3 * head_scale) or 1, cv2.LINE_AA)
    
    # Draw key joints
    for key in ("l_wr", "r_wr", "l_ank", "r_ank", "mid", "l_kn", "r_kn"):
        z = pose[key][2]
        scale = max(0.5, min(1.8, 1.0 - (z / 100.0)))
        shade = max(80, min(255, int(255 * scale)))
        cv2.circle(frame, pose[key][:2], int(8 * scale), (0, shade, int(shade * 0.7)), -1, cv2.LINE_AA)


def _progress_bar(frame, x, y, w, h, frac, color):
    cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 50), -1)
    fill = max(0, min(w, int(w * frac)))
    cv2.rectangle(frame, (x, y), (x + fill, y + h), color, -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (180, 180, 180), 1)


def _xy(landmarks, idx):
    if not landmarks or idx >= len(landmarks):
        return None
    lm = landmarks[idx]
    vis = getattr(lm, "visibility", 1.0)
    if vis is not None and vis < 0.35:
        return None
    return (lm.x, lm.y)


def _warmup_feedback(kind, landmarks, motion):
    if not landmarks:
        return "I can't see you. Step back. Full body in the frame."
    lk, rk = _xy(landmarks, 25), _xy(landmarks, 26)
    lh, rh = _xy(landmarks, 23), _xy(landmarks, 24)
    lw, rw = _xy(landmarks, 15), _xy(landmarks, 16)
    ls, rs = _xy(landmarks, 11), _xy(landmarks, 12)

    if kind == "march":
        if lk and rk:
            lift = abs(lk[1] - rk[1])
            if lift > 0.06:
                return "Good march. Keep the opposite arm swinging."
            if motion.get("knee", 0) < 0.01:
                return "Lift the knees. March, don't just shuffle."
            return "Higher knees. I want a clear left-right lift."
        return "Show me both knees. Step back a little."

    if kind == "circles":
        if motion.get("wrist", 0) > 0.04:
            return "Nice circles. Slow them down if they get sloppy."
        if lw and rw and ls and rs:
            return "Make bigger circles from the shoulder. Wrists should travel."
        return "I need both arms in view."

    if kind == "hips":
        if lk and rk and lh and rh:
            mid_x = ((lh[0] + rh[0]) / 2)
            knee_spread = max(abs(lk[0] - mid_x), abs(rk[0] - mid_x))
            lift = abs(lk[1] - rk[1])
            if lift > 0.05 and knee_spread > 0.08:
                return "That's the opener. Chest facing forward."
            if lift > 0.05:
                return "Now open the lifted knee out to the side."
            return "Knee up, then out. Hold a wall if you need it."
        return "Show hips and knees. Face the camera."

    if kind == "breathe":
        if motion.get("wrist", 0) + motion.get("knee", 0) < 0.02:
            return "Stay still. Long breath out."
        return "Slow down. This is the cool-down, not another set."

    return "Follow the figure on the right."


def _update_motion(motion, landmarks):
    prev = motion.get("prev")
    if not landmarks:
        motion["wrist"] = 0.0
        motion["knee"] = 0.0
        motion["prev"] = None
        return
    lw, rw = _xy(landmarks, 15), _xy(landmarks, 16)
    lk, rk = _xy(landmarks, 25), _xy(landmarks, 26)
    wrist = 0.0
    knee = 0.0
    if prev:
        if lw and prev.get("lw"):
            wrist += math.hypot(lw[0] - prev["lw"][0], lw[1] - prev["lw"][1])
        if rw and prev.get("rw"):
            wrist += math.hypot(rw[0] - prev["rw"][0], rw[1] - prev["rw"][1])
        if lk and prev.get("lk"):
            knee += math.hypot(lk[0] - prev["lk"][0], lk[1] - prev["lk"][1])
        if rk and prev.get("rk"):
            knee += math.hypot(rk[0] - prev["rk"][0], rk[1] - prev["rk"][1])
    motion["wrist"] = 0.7 * motion.get("wrist", 0) + 0.3 * wrist
    motion["knee"] = 0.7 * motion.get("knee", 0) + 0.3 * knee
    motion["prev"] = {"lw": lw, "rw": rw, "lk": lk, "rk": rk}


def _make_landmarker():
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        from common.exercise_engine import draw_landmarks
    except ImportError:
        return None, None, None

    model_path = resolve_model_path(prefer_full=True)
    if not os.path.exists(model_path):
        return None, None, None
    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    mp_options = mp_vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_poses=1,
    )
    landmarker = mp_vision.PoseLandmarker.create_from_options(mp_options)
    return landmarker, mp, draw_landmarks


def _run_follow_along(drills, title, total_hint):
    """Follow-along with camera watch when possible. False if the user quits."""
    start = time.time()
    drill_index = 0
    drill_started = start
    last_announced = -1
    last_live_cue = 0
    space_held = False
    w, h = 960, 540
    motion = {}

    landmarker, mp, draw_landmarks = _make_landmarker()
    cap = cv2.VideoCapture(0) if landmarker else None
    if cap is not None and not cap.isOpened():
        cap.release()
        cap = None
        if landmarker:
            landmarker.close()
            landmarker = None

    try:
        while drill_index < len(drills):
            drill = drills[drill_index]
            now = time.time()
            elapsed = now - drill_started
            remaining = drill["seconds"] - elapsed
            if remaining <= 0:
                drill_index += 1
                drill_started = now
                motion = {}
                continue

            if last_announced != drill_index:
                speak(drill["cue"], force=True)
                last_announced = drill_index

            cam_frame = None
            landmarks = None
            if cap is not None:
                ok, cam_frame = cap.read()
                if ok:
                    cam_frame = cv2.flip(cam_frame, 1)
                    rgb = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    ts = int((now - start) * 1000)
                    result = landmarker.detect_for_video(mp_image, ts)
                    if result.pose_landmarks:
                        landmarks = result.pose_landmarks[0]
                        draw_landmarks(cam_frame, landmarks, {"important_joints": ["shoulder", "elbow", "wrist", "hip", "knee", "ankle"]})

            _update_motion(motion, landmarks)
            live = _warmup_feedback(drill["kind"], landmarks, motion)

            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:] = (18, 18, 22)
            cv2.putText(frame, title, (36, 42),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
            cv2.putText(frame, f"{drill_index + 1}/{len(drills)}  {drill['name']}", (36, 88),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)

            chip_x = 36
            for i, item in enumerate(drills):
                on = i == drill_index
                color = (0, 200, 255) if on else (70, 70, 80)
                label = item["name"]
                (tw, _th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                cv2.rectangle(frame, (chip_x, 100), (chip_x + tw + 16, 124), color, -1)
                cv2.putText(frame, label, (chip_x + 8, 118),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (20, 20, 20) if on else (200, 200, 200), 1)
                chip_x += tw + 24

            if cam_frame is not None:
                thumb = cv2.resize(cam_frame, (420, 236))
                frame[140:376, 24:444] = thumb
                pose = _stick_pose(700, 280, drill["kind"], now)
                cv2.line(frame, (580, 400), (820, 400), (70, 70, 80), 3, cv2.LINE_AA)
                _draw_stick(frame, pose)
                cv2.putText(frame, "You", (24, 132), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
                cv2.putText(frame, "Follow this", (600, 132), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
            else:
                pose = _stick_pose(330, 280, drill["kind"], now)
                cv2.line(frame, (210, 430), (460, 430), (70, 70, 80), 3, cv2.LINE_AA)
                _draw_stick(frame, pose)
                tip_x = 560
                cv2.putText(frame, "Do this now", (tip_x, 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                y = 190
                for tip in drill["tips"]:
                    cv2.putText(frame, f"- {tip}", (tip_x, y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 230, 230), 1)
                    y += 36

            cv2.putText(frame, live[:70], (24, 410),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
            if now - last_live_cue > 8 and landmarks is not None:
                speak(live)
                last_live_cue = now

            drill_frac = 1.0 - remaining / drill["seconds"]
            total_done = sum(d["seconds"] for d in drills[:drill_index]) + elapsed
            total = sum(d["seconds"] for d in drills)
            _progress_bar(frame, 36, 450, 500, 16, drill_frac, (0, 200, 255))
            _progress_bar(frame, 36, 478, 500, 10, total_done / total, (0, 180, 80))
            cv2.putText(frame, f"{remaining:.0f}s this drill   {max(0, total - total_done):.0f}s total",
                        (36, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
            cv2.putText(frame, total_hint, (560, 500),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 160, 160), 1)

            cv2.imshow("Coach", frame)
            key = cv2.waitKey(16) & 0xFF
            space = key == ord(" ")
            if space and not space_held:
                stop_voice()
                drill_index += 1
                drill_started = time.time()
                last_announced = -1
                motion = {}
            elif key == ord("q"):
                stop_voice()
                return False
            space_held = space
    finally:
        if cap is not None:
            cap.release()
        if landmarker is not None:
            landmarker.close()
        cv2.destroyAllWindows()

    stop_voice()
    return True


def run_warmup(total_hint="space skip drill    q quit", scale=1.0):
    drills = [{**d, "seconds": max(12, int(d["seconds"] * scale))} for d in DRILLS]
    return _run_follow_along(drills, "WARM-UP  camera + follow the figure", total_hint)


def run_cooldown(total_hint="space skip drill    q quit"):
    return _run_follow_along(COOLDOWN, "COOLDOWN  slow down with me", total_hint)


def run_recovery(total_hint="space skip drill    q quit"):
    return _run_follow_along(RECOVERY, "RECOVERY  easy mobility", total_hint)
