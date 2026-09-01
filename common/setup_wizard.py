"""One-time camera check: light, distance, front vs side. Saved on the profile."""

import time

import cv2
import numpy as np

from common.models import resolve_model_path
from common.profile import save_profile
from common.voice import speak, stop_voice
import os


def _brightness(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def _pose_metrics(landmarks, w, h):
    if not landmarks or len(landmarks) < 29:
        return None
    pts = []
    for idx in (0, 11, 12, 23, 24, 27, 28):
        lm = landmarks[idx]
        vis = getattr(lm, "visibility", 1.0) or 0
        if vis < 0.35:
            continue
        pts.append((lm.x * w, lm.y * h, vis))
    if len(pts) < 4:
        return None
    ys = [p[1] for p in pts]
    fill = (max(ys) - min(ys)) / max(h, 1)
    ls = landmarks[11]
    rs = landmarks[12]
    shoulder_span = abs(ls.x - rs.x)
    view = "front" if shoulder_span > 0.18 else "side"
    return {"fill": fill, "view": view, "shoulder_span": round(shoulder_span, 3)}


def run_camera_setup(profile):
    """Returns True if saved. q quits without saving."""
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from common.exercise_engine import draw_landmarks

    model_path = resolve_model_path(prefer_full=True)
    if not os.path.exists(model_path):
        print("Pose model missing. Put a .task file in models/ first.")
        return False

    landmarker = mp_vision.PoseLandmarker.create_from_options(
        mp_vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
        )
    )
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    if not cap.isOpened():
        print("Could not open the camera.")
        landmarker.close()
        return False

    speak("Step back until I can see your whole body. Face me first, then turn sideways.", force=True)
    start = time.time()
    ok_since = None
    last = {}
    try:
        while True:
            success, frame = cap.read()
            if not success:
                break
            now = time.time()
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = landmarker.detect_for_video(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
                int((now - start) * 1000),
            )
            landmarks = result.pose_landmarks[0] if result.pose_landmarks else None
            if landmarks:
                draw_landmarks(frame, landmarks)

            bright = _brightness(frame)
            pose = _pose_metrics(landmarks, w, h)
            light_ok = 55 <= bright <= 200
            dist_ok = pose is not None and 0.45 <= pose["fill"] <= 0.92
            body_ok = pose is not None
            all_ok = light_ok and dist_ok and body_ok
            if all_ok:
                ok_since = ok_since or now
            else:
                ok_since = None

            last = {
                "brightness": round(bright, 1),
                "fill_ratio": round(pose["fill"], 3) if pose else None,
                "detected_view": pose["view"] if pose else None,
                "light_ok": light_ok,
                "distance_ok": dist_ok,
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }

            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, 160), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
            cv2.putText(frame, "Camera setup", (16, 36),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            lines = [
                f"Light: {'OK' if light_ok else 'fix'}  ({int(bright)})",
                f"Distance: {'OK' if dist_ok else 'step back / closer'}",
                f"View now: {pose['view'] if pose else 'not seen'}",
            ]
            y = 70
            for line in lines:
                cv2.putText(frame, line, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 230, 230), 1)
                y += 28
            hint = "Hold this. Press s to save." if all_ok else "q quit   s save anyway"
            if ok_since and now - ok_since > 1.2:
                hint = "Looks good. Press s to remember this setup."
            cv2.putText(frame, hint, (16, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 255, 180), 1)
            cv2.imshow("Coach", frame)
            key = cv2.waitKey(16) & 0xFF
            if key == ord("q"):
                stop_voice()
                return False
            if key == ord("s"):
                profile["camera_setup"] = last
                save_profile(profile)
                speak("Setup saved.", force=True)
                print("Camera setup saved.")
                return True
    finally:
        landmarker.close()
        cap.release()
        cv2.destroyAllWindows()
    return False
