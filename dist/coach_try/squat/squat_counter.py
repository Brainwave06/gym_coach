"""
Squat coach — pose tracking, rep counting, and form feedback.

Run from the project root:
    python main.py
    python squat/squat_counter.py

Press 'q' to close the camera, or 'r' to reset the counters.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from common.exercise_engine import run_exercise
from squat.config import EXERCISE_CONFIG


def main():
    run_exercise(EXERCISE_CONFIG)


if __name__ == "__main__":
    main()
