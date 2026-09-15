import json
import os
# pyrefly: ignore [missing-import]
import cv2
import numpy as np
import mediapipe as mp
import base64
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from common.paths import DATA_ROOT
from common.profile import load_profile
from common.handoff import write_handoff
from common.catalog import get_config
from common.models import resolve_model_path

from gym_ai import arun_pipeline, generate_personalized_plan

app = FastAPI(title="AI Exercise Coach API with Gym AI Chatbot")


class ChatRequest(BaseModel):
    query: str
    chat_history: Optional[List[Dict[str, Any]]] = None
    include_profile: bool = True


class PlanRequest(BaseModel):
    user_id: Optional[str] = None


class VisionMealRequest(BaseModel):
    image_base64: str
    user_notes: Optional[str] = ""


class PRLogRequest(BaseModel):
    exercise_name: str
    weight_kg: float
    reps: int
    notes: Optional[str] = ""

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


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Chat with the Gym AI assistant with optional athlete profile context."""
    athlete_context = None
    if req.include_profile:
        athlete_context = load_profile()
        handoff_path = os.path.join(DATA_ROOT, "data", "coach_handoff.json")
        if os.path.exists(handoff_path):
            try:
                with open(handoff_path, "r", encoding="utf-8") as f:
                    athlete_context = {"athlete": athlete_context, **json.load(f)}
            except Exception:
                pass

    answer = await arun_pipeline(
        query=req.query,
        chat_history=req.chat_history,
        stream=False,
        athlete_context=athlete_context,
    )
    return {"status": "success", "answer": answer}


@app.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """Stream response tokens from Gym AI via Server-Sent Events (SSE)."""
    athlete_context = None
    if req.include_profile:
        athlete_context = load_profile()
        handoff_path = os.path.join(DATA_ROOT, "data", "coach_handoff.json")
        if os.path.exists(handoff_path):
            try:
                with open(handoff_path, "r", encoding="utf-8") as f:
                    athlete_context = {"athlete": athlete_context, **json.load(f)}
            except Exception:
                pass

    async def event_generator():
        stream_gen = await arun_pipeline(
            query=req.query,
            chat_history=req.chat_history,
            stream=True,
            athlete_context=athlete_context,
        )
        async for chunk in stream_gen:
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/chatbot/generate_plan")
def generate_plan_endpoint(req: Optional[PlanRequest] = None):
    """Trigger the LLM to read athlete handoff and generate tomorrow's workout plan."""
    profile = load_profile()
    plan = generate_personalized_plan(profile=profile)
    return {"status": "success", "plan": plan}


@app.get("/chat/debrief")
@app.post("/chat/debrief")
def chat_debrief_endpoint():
    """Get proactive coaching debrief for the most recent workout session."""
    from gym_ai.debrief import generate_post_workout_debrief
    profile = load_profile()
    handoff_path = os.path.join(DATA_ROOT, "data", "coach_handoff.json")
    handoff = {}
    if os.path.exists(handoff_path):
        try:
            with open(handoff_path, "r", encoding="utf-8") as f:
                handoff = json.load(f)
        except Exception:
            pass
    debrief = generate_post_workout_debrief(profile, handoff)
    return {"status": "success", "debrief": debrief}


def _detect_image_mime(header_bytes: bytes, fallback: str = "image/jpeg") -> str:
    if header_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif header_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    elif header_bytes.startswith(b"RIFF") and len(header_bytes) >= 12 and header_bytes[8:12] == b"WEBP":
        return "image/webp"
    elif header_bytes.startswith(b"GIF87a") or header_bytes.startswith(b"GIF89a"):
        return "image/gif"
    return fallback


@app.post("/chat/vision-meal")
async def chat_vision_meal_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(None),
    notes: Optional[str] = Form(None),
    image_base64: Optional[str] = Form(None),
):
    """
    Multimodal plate analyzer using Qwen-VL.
    Accepts:
    - Multipart Form: upload meal image file via `file` field, or pass `image_base64`.
    - JSON: send {"image_base64": "...", "user_notes": "..."}.
    """
    import base64
    from gym_ai.vision.meal_analyzer import aanalyze_meal

    b64_data = ""
    user_notes = ""

    # Check if request came as JSON
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                b64_data = body.get("image_base64") or body.get("image_url") or ""
                user_notes = body.get("user_notes") or body.get("notes") or ""
        except Exception:
            pass

    # Process multipart file upload
    if not b64_data and file and file.filename:
        file_bytes = await file.read()
        if file_bytes:
            mime = _detect_image_mime(file_bytes[:16], fallback=file.content_type or "image/jpeg")
            encoded = base64.b64encode(file_bytes).decode("utf-8")
            b64_data = f"data:{mime};base64,{encoded}"
            user_notes = notes or ""
    elif not b64_data and image_base64:
        b64_data = image_base64.strip()
        user_notes = notes or ""

    if not b64_data:
        raise HTTPException(
            status_code=400,
            detail="No meal image provided. Please upload an image file using the 'file' field or provide 'image_base64'.",
        )

    profile = load_profile()
    try:
        result = await aanalyze_meal(image_b64_or_url=b64_data, user_notes=user_notes, profile=profile)
        return {"status": "success", "meal": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Meal vision analysis failed: {exc}")


@app.post("/chat/vision-meal/json")
async def chat_vision_meal_json_endpoint(req: VisionMealRequest):
    """
    Dedicated JSON endpoint for multimodal plate analysis with Qwen-VL.
    """
    from gym_ai.vision.meal_analyzer import aanalyze_meal

    if not req.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required in JSON body.")

    profile = load_profile()
    try:
        result = await aanalyze_meal(
            image_b64_or_url=req.image_base64,
            user_notes=req.user_notes or "",
            profile=profile,
        )
        return {"status": "success", "meal": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Meal vision analysis failed: {exc}")



@app.get("/prs")
def get_prs_endpoint(exercise: Optional[str] = None):
    """Retrieve athlete personal records and estimated 1RMs."""
    from gym_ai.memory.storage import get_all_personal_records
    prs = get_all_personal_records(exercise_name=exercise)
    return {"status": "success", "prs": prs}


@app.post("/prs")
def log_pr_endpoint(req: PRLogRequest):
    """Log a personal record."""
    from gym_ai.memory.storage import log_personal_record
    record = log_personal_record(
        exercise_name=req.exercise_name,
        weight_kg=req.weight_kg,
        reps=req.reps,
        notes=req.notes or "",
    )
    return {"status": "success", "pr": record}


@app.get("/memory/conversations")
def get_conversations_endpoint(limit: int = 20):
    """Retrieve persistent conversation messages."""
    from gym_ai.memory.storage import get_recent_messages
    messages = get_recent_messages(limit=limit)
    return {"status": "success", "messages": messages}

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
