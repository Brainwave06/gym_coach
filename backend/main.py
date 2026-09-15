"""
Cloud Backend API Entrypoint - FitPath.
Unifies all Gym AI, computer vision streaming, authentication, athlete profiles,
and multimodal vision capabilities into a single production server.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from pydantic import BaseModel

# Ensure root workspace is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import full production FastAPI application
from api import app, WorkoutSummaryUploadRequest, upload_workout_summary_endpoint

# Expose backward-compatible aliases for cloud deployment
class CloudWorkoutSummary(BaseModel):
    duration_min: Optional[int] = 10
    total_reps: Optional[int] = 20
    overall_quality: Optional[float] = 90.0
    exercise_id: Optional[str] = "squat"
    notes: Optional[str] = ""


@app.post("/users/{user_id}/workout_summary", tags=["cloud_legacy"])
def upload_legacy_summary(user_id: str, summary: CloudWorkoutSummary):
    """
    Legacy cloud summary route forwarding into unified workout session storage.
    """
    req = WorkoutSummaryUploadRequest(
        user_id=user_id,
        exercise_id=summary.exercise_id or "general_workout",
        duration_sec=(summary.duration_min or 10) * 60,
        total_reps=summary.total_reps or 0,
        form_accuracy_pct=summary.overall_quality or 90.0,
        notes=summary.notes or "Legacy cloud summary upload",
    )
    return upload_workout_summary_endpoint(req)


@app.post("/chatbot/chat", tags=["cloud_legacy"])
async def chatbot_chat_legacy(req: Dict[str, Any]):
    """
    Legacy cloud chatbot route forwarding to pipeline.
    """
    from gym_ai import arun_pipeline
    query = req.get("query", "")
    history = req.get("chat_history")
    try:
        answer = await arun_pipeline(query=query, chat_history=history, stream=False)
        return {"status": "success", "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
