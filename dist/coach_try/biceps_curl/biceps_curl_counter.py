"""Biceps curl coach. Run: python biceps_curl/biceps_curl_counter.py"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from biceps_curl.config import EXERCISE_CONFIG
from common.exercise_engine import run_exercise


def main():
    run_exercise(EXERCISE_CONFIG)


if __name__ == "__main__":
    main()
