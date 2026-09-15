"""
Unit tests for expanded exercise catalog (RDL, Overhead Press, Lateral Raise).
"""

import unittest

from common.catalog import BASE, MENU, get_config
from lateral_raise.config import EXERCISE_CONFIG as LATERAL_CONFIG
from overhead_press.config import EXERCISE_CONFIG as OHP_CONFIG
from rdl.config import EXERCISE_CONFIG as RDL_CONFIG


class TestNewExercises(unittest.TestCase):
    def test_rdl_config(self):
        self.assertEqual(RDL_CONFIG["display_name"], "Romanian Deadlift")
        self.assertEqual(RDL_CONFIG["primary_check"], "hip_hinge")
        self.assertIn("hip_hinge", RDL_CONFIG["checks"])
        self.assertIn("excessive_knee_bend", RDL_CONFIG["checks"])
        self.assertIn("left", RDL_CONFIG["landmarks"])
        self.assertIn("right", RDL_CONFIG["landmarks"])
        self.assertTrue(len(RDL_CONFIG["feedback_rules"]) >= 3)

    def test_overhead_press_config(self):
        self.assertEqual(OHP_CONFIG["display_name"], "Overhead Press")
        self.assertEqual(OHP_CONFIG["primary_check"], "arm_extension")
        self.assertIn("arm_extension", OHP_CONFIG["checks"])
        self.assertIn("torso_arch", OHP_CONFIG["checks"])
        self.assertEqual(OHP_CONFIG["initial_stage"], "down")
        self.assertEqual(OHP_CONFIG["count_on"], "reach_up")

    def test_lateral_raise_config(self):
        self.assertEqual(LATERAL_CONFIG["display_name"], "Lateral Raise")
        self.assertEqual(LATERAL_CONFIG["primary_check"], "arm_elevation")
        self.assertIn("arm_elevation", LATERAL_CONFIG["checks"])
        self.assertIn("torso_swing", LATERAL_CONFIG["checks"])
        self.assertEqual(LATERAL_CONFIG["view"], "front")

    def test_catalog_registration(self):
        self.assertIn("rdl", BASE)
        self.assertIn("overhead_press", BASE)
        self.assertIn("lateral_raise", BASE)

        cfg_rdl = get_config("rdl")
        self.assertEqual(cfg_rdl["id"], "rdl")
        self.assertTrue(len(cfg_rdl.get("teach", "")) > 10)

        cfg_ohp = get_config("overhead_press")
        self.assertEqual(cfg_ohp["id"], "overhead_press")

        cfg_lat = get_config("lateral_raise")
        self.assertEqual(cfg_lat["id"], "lateral_raise")

        menu_ids = [item[1] for item in MENU]
        self.assertIn("rdl", menu_ids)
        self.assertIn("overhead_press", menu_ids)
        self.assertIn("lateral_raise", menu_ids)


if __name__ == "__main__":
    unittest.main()
