"""
Plank coach — pose tracking, hold timer, and form feedback.

Stand sideways to the camera. Hold time only counts while you stay in plank;
good-form time only counts when hips, knees, and alignment look clean.

Run from the project root:
    python main.py
    python plank/plank_hold.py

Press 'q' to close the camera, or 'r' to reset the timer.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from common.exercise_engine import run_exercise
from plank.config import EXERCISE_CONFIG


def main():
    run_exercise(EXERCISE_CONFIG)


if __name__ == "__main__":
    main()
