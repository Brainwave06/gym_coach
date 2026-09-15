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

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FitPath AI Exercise Coach & Gym AI Backend")

# Enable universal CORS for Flutter Mobile, Flutter Web, and Emulators
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: Optional[str] = ""


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    goal: Optional[str] = None
    fitness_level: Optional[str] = None
    dietary_preferences: Optional[str] = None
    injuries: Optional[List[str]] = None


class WorkoutSummaryUploadRequest(BaseModel):
    user_id: Optional[str] = "default"
    exercise_id: str
    duration_sec: int
    total_reps: int
    form_accuracy_pct: Optional[float] = 100.0
    avg_cadence_sec: Optional[float] = 2.0
    fatigue_velocity_loss_pct: Optional[float] = 0.0
    faults: Optional[List[str]] = None
    weight_kg: Optional[float] = 0.0
    notes: Optional[str] = ""


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


# ==========================================
# User Authentication Endpoints
# ==========================================

@app.post("/auth/register")
def register_endpoint(req: RegisterRequest):
    """Register a new user and return JWT access token."""
    import uuid
    from common.auth import create_access_token, hash_password
    from gym_ai.memory.storage import create_user, get_user_by_email_or_username

    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")

    existing = get_user_by_email_or_username(req.email)
    if not existing:
        existing = get_user_by_email_or_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email or username already exists.")

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    hashed, salt = hash_password(req.password)
    user = create_user(
        user_id=user_id,
        email=req.email,
        username=req.username,
        hashed_password=hashed,
        salt=salt,
        full_name=req.full_name or req.username,
    )
    token = create_access_token({"user_id": user_id, "email": user["email"], "username": user["username"]})
    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


@app.post("/auth/login")
def login_endpoint(req: LoginRequest):
    """Authenticate user with username/email and password."""
    from common.auth import create_access_token, verify_password
    from gym_ai.memory.storage import get_user_by_email_or_username

    user = get_user_by_email_or_username(req.username_or_email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")

    if not verify_password(req.password, user["hashed_password"], user["salt"]):
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")

    token = create_access_token({"user_id": user["id"], "email": user["email"], "username": user["username"]})
    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "full_name": user["full_name"],
        },
    }


@app.get("/auth/me")
def get_current_user_endpoint(request: Request):
    """Retrieve profile of the currently authenticated user from Bearer token."""
    from common.auth import get_current_user_from_header
    from gym_ai.memory.storage import get_user_by_id

    auth_header = request.headers.get("Authorization")
    payload = get_current_user_from_header(auth_header)
    if not payload:
        return {
            "status": "guest",
            "user": {"id": "default", "username": "guest", "full_name": "Guest Athlete"},
        }
    user = get_user_by_id(payload["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {
        "status": "authenticated",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "full_name": user["full_name"],
        },
    }


# ==========================================
# Athlete Profile & Biometrics Endpoints
# ==========================================

@app.get("/profile")
def get_profile_endpoint():
    """Retrieve athlete profile merged with real-time computed biometrics."""
    from common.profile import calculate_biometrics, load_profile
    profile = load_profile() or {}
    biometrics = calculate_biometrics(profile)
    return {
        "status": "success",
        "profile": profile,
        "biometrics": biometrics,
    }


@app.put("/profile")
@app.post("/profile")
def update_profile_endpoint(req: ProfileUpdateRequest):
    """Update athlete profile fields, recompute biometrics, and track body weight history."""
    from common.profile import calculate_biometrics, load_profile, save_profile
    from gym_ai.memory.storage import log_weight_entry

    profile = load_profile() or {}
    update_data = req.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if v is not None:
            profile[k] = v

    save_profile(profile)

    if req.weight_kg is not None:
        try:
            log_weight_entry(weight_kg=req.weight_kg, notes="Profile update")
        except Exception:
            pass

    biometrics = calculate_biometrics(profile)
    return {
        "status": "success",
        "profile": profile,
        "biometrics": biometrics,
    }


# ==========================================
# Workout Summary & Session Handoff Endpoints
# ==========================================

@app.post("/workout/summary")
def upload_workout_summary_endpoint(req: WorkoutSummaryUploadRequest):
    """
    Receive completed workout summary from mobile/CV client.
    Persists session to SQLite, updates history.jsonl, and writes coach_handoff.json.
    """
    import uuid
    from datetime import datetime
    from common.history import append_session
    from common.handoff import write_handoff
    from common.profile import load_profile
    from gym_ai.memory.storage import log_workout_session, log_personal_record

    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    logged = log_workout_session(
        session_id=session_id,
        user_id=req.user_id or "default",
        exercise_id=req.exercise_id,
        duration_sec=req.duration_sec,
        total_reps=req.total_reps,
        form_accuracy_pct=req.form_accuracy_pct or 100.0,
        avg_cadence_sec=req.avg_cadence_sec or 2.0,
        fatigue_velocity_loss_pct=req.fatigue_velocity_loss_pct or 0.0,
        faults=req.faults or [],
        notes=req.notes or "",
    )

    history_record = {
        "kind": "workout",
        "exercise": req.exercise_id,
        "reps": req.total_reps,
        "duration_sec": req.duration_sec,
        "accuracy": req.form_accuracy_pct,
        "cadence_sec": req.avg_cadence_sec,
        "fatigue_loss_pct": req.fatigue_velocity_loss_pct,
        "faults": req.faults or [],
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        append_session(history_record)
    except Exception:
        pass

    profile = load_profile() or {}
    try:
        write_handoff(
            profile,
            extra={
                "last_session": history_record,
                "status": "completed",
            },
        )
    except Exception:
        pass

    pr_logged = None
    if req.weight_kg and req.weight_kg > 0 and req.total_reps > 0:
        try:
            pr_logged = log_personal_record(
                exercise_name=req.exercise_id,
                weight_kg=req.weight_kg,
                reps=req.total_reps,
                notes=f"Auto-logged from session {session_id}",
            )
        except Exception:
            pass

    return {
        "status": "success",
        "session": logged,
        "pr": pr_logged,
        "handoff_ready": True,
    }


@app.get("/workout/history")
def get_workout_history_endpoint(user_id: Optional[str] = None, limit: int = 20):
    """Retrieve athlete workout history from SQLite."""
    from gym_ai.memory.storage import get_workout_sessions
    sessions = get_workout_sessions(user_id=user_id, limit=limit)
    return {"status": "success", "history": sessions}


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
