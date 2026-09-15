"""
Gym AI - Intelligent Fitness & Sports Nutrition Coach.
"""

from gym_ai.pipeline import arun_pipeline, run_pipeline
from gym_ai.planner import generate_personalized_plan
from gym_ai.router import extract_portion_grams, route_query

__version__ = "1.0.0"

__all__ = [
    "run_pipeline",
    "arun_pipeline",
    "generate_personalized_plan",
    "route_query",
    "extract_portion_grams",
]
