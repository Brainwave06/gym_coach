"""
Unit tests for rep cadence, velocity loss, and RIR/RPE calculation.
"""

import unittest

from common.exercise_engine import compute_rep_cadence_and_fatigue, reset_session
from squat.config import EXERCISE_CONFIG as SQUAT_CONFIG


class TestRepCadenceAndFatigue(unittest.TestCase):
    def setUp(self):
        self.session = reset_session(SQUAT_CONFIG)

    def test_baseline_concentric_establishment(self):
        # Reps 1 to 3 with 1.0s concentric
        for i in range(1, 4):
            self.session["counter"] = i
            res = compute_rep_cadence_and_fatigue(self.session, eccentric_duration=1.5, concentric_duration=1.0)
            self.assertEqual(res["velocity_loss_pct"], 0.0)
            self.assertEqual(res["estimated_rpe"], 7.0)
            self.assertEqual(res["estimated_rir"], 4)

        self.assertAlmostEqual(self.session["baseline_concentric"], 1.0, places=2)

    def test_fatigue_velocity_loss_mapping(self):
        # Establish baseline of 1.0s
        for i in range(1, 4):
            self.session["counter"] = i
            compute_rep_cadence_and_fatigue(self.session, 1.5, 1.0)

        # Rep 4: Moderate fatigue (1.20s -> 20% loss)
        self.session["counter"] = 4
        res4 = compute_rep_cadence_and_fatigue(self.session, 1.5, 1.20)
        self.assertEqual(res4["velocity_loss_pct"], 20.0)
        self.assertEqual(res4["estimated_rpe"], 8.0)
        self.assertEqual(res4["estimated_rir"], 3)

        # Rep 5: High fatigue (1.35s -> 35% loss)
        self.session["counter"] = 5
        res5 = compute_rep_cadence_and_fatigue(self.session, 1.5, 1.35)
        self.assertEqual(res5["velocity_loss_pct"], 35.0)
        self.assertEqual(res5["estimated_rpe"], 8.5)
        self.assertEqual(res5["estimated_rir"], 2)

        # Rep 6: Muscular failure proximity (1.50s -> 50% loss)
        self.session["counter"] = 6
        res6 = compute_rep_cadence_and_fatigue(self.session, 1.5, 1.50)
        self.assertEqual(res6["velocity_loss_pct"], 50.0)
        self.assertEqual(res6["estimated_rpe"], 9.0)
        self.assertEqual(res6["estimated_rir"], 1)

        # Rep 7: Exhaustion (1.70s -> 70% loss)
        self.session["counter"] = 7
        res7 = compute_rep_cadence_and_fatigue(self.session, 1.5, 1.70)
        self.assertEqual(res7["velocity_loss_pct"], 70.0)
        self.assertEqual(res7["estimated_rpe"], 9.5)
        self.assertEqual(res7["estimated_rir"], 0)


if __name__ == "__main__":
    unittest.main()
