import json
import os
import cv2
import numpy as np
import mediapipe as mp
import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from common.paths import DATA_ROOT
from common.profile import load_profile
from common.history import load_history
from common.handoff import write_handoff
from common.exercise_engine import run_exercise, _SmoothedLandmark, smooth_pose_landmarks
from common.catalog import get_config
from common.models import resolve_model_path

app = FastAPI(title="AI Exercise Coach API")

# Setup MediaPipe once for the API (if we are doing stateful tracking)
BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

@app.get("/")
def read_root():
    return {"status": "ok", "message": "AI Exercise Coach API is running."}

@app.get("/plan")
def get_plan():
    """Retrieve the current workout plan (from Chatbot)"""
    plan_path = os.path.join(DATA_ROOT, "data", "workout_plan.json")
    if os.path.exists(plan_path):
        with open(plan_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Fallback to a default if chatbot hasn't written one
    return {
        "status": "default",
        "plan": [
            {"exercise_id": "squat", "sets": 2, "reps": 10},
            {"exercise_id": "pushup", "sets": 2, "reps": 8}
        ]
    }

@app.post("/report")
def post_report(report: dict):
    """Save the final workout report and trigger handoff back to Chatbot."""
    # Write summary for chatbot
    os.makedirs(os.path.join(DATA_ROOT, "data"), exist_ok=True)
    summary_path = os.path.join(DATA_ROOT, "data", "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    profile = load_profile() or {"name": "Athlete"}
    write_handoff(profile, extra={"latest_report": report})
    
    return {"status": "success", "message": "Handoff generated."}

@app.websocket("/stream/{exercise_id}")
async def websocket_endpoint(websocket: WebSocket, exercise_id: str):
    """
    WebSocket to stream base64 video frames from Flutter, process them, 
    and return JSON rep counts and form errors.
    """
    await websocket.accept()
    
    cfg = get_config(exercise_id)
    if not cfg:
        await websocket.send_json({"error": f"Unknown exercise {exercise_id}"})
        await websocket.close()
        return

    model_path = resolve_model_path("pose_landmarker_lite.task")
    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.VIDEO,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    
    # Session state for the exercise
    session = {
        "stage": cfg.get("initial_stage", "down"),
        "counter": 0,
        "faults": [],
        "min_in_rep": {},
        "max_in_rep": {},
        "pose_ema": {},
        "baselines": {},
        "ready_frames": 0,
    }

    try:
        with PoseLandmarker.create_from_options(options) as landmarker:
            frame_idx = 0
            while True:
                data = await websocket.receive_text()
                # Assuming data is base64 encoded JPEG
                img_data = base64.b64decode(data)
                np_arr = np.frombuffer(img_data, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    continue

                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
                timestamp_ms = int(frame_idx * 1000 / 30) # simulate 30fps
                result = landmarker.detect_for_video(mp_image, timestamp_ms)
                frame_idx += 1
                
                response = {
                    "rep": session["counter"],
                    "stage": session["stage"],
                    "faults": session["faults"],
                    "landmarks_detected": bool(result.pose_landmarks)
                }
                
                await websocket.send_json(response)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS Error: {e}")
        await websocket.close()
