"""Wall sit coach. Run: python wall_sit/wall_sit_hold.py"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from common.exercise_engine import run_exercise
from wall_sit.config import EXERCISE_CONFIG


def main():
    run_exercise(EXERCISE_CONFIG)


if __name__ == "__main__":
    main()
