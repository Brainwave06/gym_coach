from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Cloud Backend API - FitPath")

class WorkoutSummary(BaseModel):
    user_id: str
    duration_min: int
    total_reps: int
    overall_quality: float

@app.get("/")
def read_root():
    return {"message": "Cloud Backend API is running."}

@app.post("/users/{user_id}/workout_summary")
def upload_summary(user_id: str, summary: WorkoutSummary):
    """
    Endpoint for receiving the summary.json uploaded after a workout.
    TODO: Save this to PostgreSQL / MongoDB.
    """
    return {"status": "success", "received_for": user_id}

@app.post("/chatbot/generate_plan")
def generate_plan(user_id: str):
    """
    Endpoint to trigger the LLM to read the latest handoff and generate tomorrow's workout.
    TODO: Integrate OpenAI/Claude here.
    """
    return {"status": "success", "message": "Chatbot plan generated."}
