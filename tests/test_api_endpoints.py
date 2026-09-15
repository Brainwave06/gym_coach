"""
Integration tests for FastAPI endpoints in api.py including Chatbot and Plan endpoints.
"""

import json
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from api import app


class TestAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")

    def test_get_plan(self):
        response = self.client.get("/plan")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue("plan" in data)

    def test_chat_endpoint(self):
        payload = {
            "query": "Hello! What is your name and role?",
            "include_profile": True,
        }
        response = self.client.post("/chat", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(len(data.get("answer", "")) > 10)

    def test_chat_stream_endpoint(self):
        payload = {
            "query": "Say ready",
            "include_profile": False,
        }
        response = self.client.post("/chat/stream", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers.get("content-type", ""))
        self.assertIn("data:", response.text)

    def test_generate_plan_endpoint(self):
        response = self.client.post("/chatbot/generate_plan", json={})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("plan", data)
        self.assertIn("nutrition_recovery", data["plan"])

    def test_chat_debrief_endpoint(self):
        response = self.client.get("/chat/debrief")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(len(data.get("debrief", "")) > 10)

    def test_prs_endpoints(self):
        # 1. Log a PR
        log_payload = {
            "exercise_name": "Deadlift",
            "weight_kg": 140.0,
            "reps": 3,
            "notes": "Fast reps",
        }
        res_post = self.client.post("/prs", json=log_payload)
        self.assertEqual(res_post.status_code, 200)
        data_post = res_post.json()
        self.assertEqual(data_post.get("status"), "success")
        self.assertEqual(data_post["pr"]["exercise"], "Deadlift")
        self.assertAlmostEqual(data_post["pr"]["estimated_1rm"], 154.0, places=1)

        # 2. Get PRs
        res_get = self.client.get("/prs?exercise=Deadlift")
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.json()
        self.assertEqual(data_get.get("status"), "success")
        self.assertTrue(len(data_get.get("prs", [])) >= 1)

    def test_memory_conversations_endpoint(self):
        response = self.client.get("/memory/conversations?limit=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIsInstance(data.get("messages"), list)

    @patch("gym_ai.vision.meal_analyzer.aanalyze_meal", new_callable=AsyncMock)
    def test_vision_meal_multipart_upload(self, mock_aanalyze):
        mock_aanalyze.return_value = {
            "meal_name": "Grilled Chicken Salad",
            "total_calories": 350,
            "total_protein_g": 48.0,
            "items": [{"name": "Grilled Chicken", "protein_g": 45.0}],
            "coach_feedback": "Great meal!",
        }
        res = self.client.post(
            "/chat/vision-meal",
            files={"file": ("plate.jpg", b"\xff\xd8\xff\xe0fake_jpeg", "image/jpeg")},
            data={"notes": "healthy lunch"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data["meal"]["meal_name"], "Grilled Chicken Salad")

    @patch("gym_ai.vision.meal_analyzer.aanalyze_meal", new_callable=AsyncMock)
    def test_vision_meal_json_endpoint(self, mock_aanalyze):
        mock_aanalyze.return_value = {
            "meal_name": "Steak and Rice",
            "total_calories": 600,
            "total_protein_g": 55.0,
        }
        payload = {"image_base64": "fakeb64data", "user_notes": "post workout"}
        res = self.client.post("/chat/vision-meal/json", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data["meal"]["meal_name"], "Steak and Rice")

    def test_vision_meal_missing_image(self):
        res = self.client.post("/chat/vision-meal")
        self.assertEqual(res.status_code, 400)
        self.assertIn("No meal image provided", res.json().get("detail", ""))


if __name__ == "__main__":
    unittest.main()
