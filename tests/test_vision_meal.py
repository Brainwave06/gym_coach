"""
Unit tests for visual meal analysis and nutritional calculations.
"""

import unittest
from unittest.mock import patch

from gym_ai.vision.meal_analyzer import analyze_meal


class TestVisionMeal(unittest.TestCase):
    @patch("gym_ai.vision.meal_analyzer.generate_vision_analysis")
    def test_meal_analysis_and_target_comparison(self, mock_vision):
        mock_output = """
        {
          "meal_name": "Chicken Breast and Jasmine Rice with Broccoli",
          "items": [
            {"name": "Grilled Chicken Breast", "portion_g": 200, "calories": 330, "protein_g": 62.0, "carbs_g": 0.0, "fat_g": 7.0},
            {"name": "White Jasmine Rice", "portion_g": 180, "calories": 234, "protein_g": 4.5, "carbs_g": 50.4, "fat_g": 0.5},
            {"name": "Steamed Broccoli", "portion_g": 100, "calories": 35, "protein_g": 2.4, "carbs_g": 7.0, "fat_g": 0.4}
          ],
          "total_calories": 599,
          "total_protein_g": 68.9,
          "total_carbs_g": 57.4,
          "total_fat_g": 7.9,
          "coach_feedback": "Excellent high-protein recovery meal!",
          "suggestions": ["Drink 500ml water"]
        }
        """
        mock_vision.return_value = mock_output

        test_profile = {
            "name": "Menna",
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "goal": "strength",
        }

        # Fake base64 image
        fake_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        result = analyze_meal(image_b64_or_url=fake_b64, profile=test_profile)

        self.assertEqual(result["meal_name"], "Chicken Breast and Jasmine Rice with Broccoli")
        self.assertEqual(len(result["items"]), 3)
        self.assertAlmostEqual(result["total_protein_g"], 68.9, places=1)
        self.assertIn("target_comparison", result)
        self.assertGreater(result["target_comparison"]["meal_protein_coverage_pct"], 35.0)


if __name__ == "__main__":
    unittest.main()
