import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Ensure root workspace is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gym_ai import arun_pipeline, generate_personalized_plan

app = FastAPI(title="Cloud Backend API - FitPath")


class WorkoutSummary(BaseModel):
    user_id: str
    duration_min: int
    total_reps: int
    overall_quality: float


class ChatRequest(BaseModel):
    query: str
    chat_history: Optional[List[Dict[str, Any]]] = None
    user_id: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "Cloud Backend API is running with Gym AI integrated."}


@app.post("/users/{user_id}/workout_summary")
def upload_summary(user_id: str, summary: WorkoutSummary):
    """
    Endpoint for receiving the summary.json uploaded after a workout.
    """
    return {"status": "success", "received_for": user_id, "summary": summary.model_dump()}


@app.post("/chatbot/generate_plan")
def generate_plan(user_id: str):
    """
    Endpoint to trigger the LLM to read the athlete handoff and generate tomorrow's workout.
    """
    try:
        plan = generate_personalized_plan()
        return {"status": "success", "user_id": user_id, "plan": plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chatbot/chat")
async def chatbot_chat(req: ChatRequest):
    """
    Direct cloud chatbot endpoint.
    """
    try:
        answer = await arun_pipeline(
            query=req.query,
            chat_history=req.chat_history,
            stream=False,
        )
        return {"status": "success", "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
