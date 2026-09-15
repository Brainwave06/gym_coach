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

    def test_cors_headers(self):
        res = self.client.options(
            "/profile",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("access-control-allow-origin"), "http://localhost:3000")

    def test_auth_register_and_login_flow(self):
        import uuid
        unique_suffix = uuid.uuid4().hex[:6]
        email = f"athlete_{unique_suffix}@fitpath.ai"
        username = f"athlete_{unique_suffix}"

        # 1. Register
        reg_payload = {
            "email": email,
            "username": username,
            "password": "strongPassword123",
            "full_name": "Test Athlete",
        }
        res_reg = self.client.post("/auth/register", json=reg_payload)
        self.assertEqual(res_reg.status_code, 200)
        data_reg = res_reg.json()
        self.assertEqual(data_reg.get("status"), "success")
        token = data_reg.get("access_token")
        self.assertTrue(len(token) > 20)

        # Duplicate register should fail with 400
        res_dup = self.client.post("/auth/register", json=reg_payload)
        self.assertEqual(res_dup.status_code, 400)

        # 2. Login
        login_payload = {
            "username_or_email": email,
            "password": "strongPassword123",
        }
        res_login = self.client.post("/auth/login", json=login_payload)
        self.assertEqual(res_login.status_code, 200)
        data_login = res_login.json()
        self.assertEqual(data_login.get("status"), "success")
        self.assertEqual(data_login["user"]["username"], username)

        # 3. Auth Me
        res_me = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_me.status_code, 200)
        data_me = res_me.json()
        self.assertEqual(data_me.get("status"), "authenticated")
        self.assertEqual(data_me["user"]["email"], email)

    def test_profile_get_and_put(self):
        # 1. Get profile
        res_get = self.client.get("/profile")
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.json()
        self.assertEqual(data_get.get("status"), "success")
        self.assertIn("biometrics", data_get)
        self.assertIn("bmi", data_get["biometrics"])

        # 2. Update profile
        update_payload = {
            "weight_kg": 73.0,
            "goal": "strength",
            "fitness_level": "advanced",
        }
        res_put = self.client.put("/profile", json=update_payload)
        self.assertEqual(res_put.status_code, 200)
        data_put = res_put.json()
        self.assertEqual(data_put.get("status"), "success")
        self.assertEqual(data_put["profile"]["goal"], "strength")
        self.assertAlmostEqual(data_put["profile"]["weight_kg"], 73.0)
        self.assertIn("bmr_kcal", data_put["biometrics"])

    def test_workout_summary_upload_and_history(self):
        payload = {
            "user_id": "test_athlete_123",
            "exercise_id": "overhead_press",
            "duration_sec": 140,
            "total_reps": 12,
            "form_accuracy_pct": 92.5,
            "avg_cadence_sec": 2.2,
            "fatigue_velocity_loss_pct": 9.0,
            "faults": ["elbow_flare"],
            "weight_kg": 50.0,
            "notes": "Solid overhead session",
        }
        res_post = self.client.post("/workout/summary", json=payload)
        self.assertEqual(res_post.status_code, 200)
        data_post = res_post.json()
        self.assertEqual(data_post.get("status"), "success")
        self.assertTrue(data_post.get("handoff_ready"))
        self.assertEqual(data_post["session"]["exercise_id"], "overhead_press")

        # Verify in workout history
        res_hist = self.client.get("/workout/history?user_id=test_athlete_123&limit=5")
        self.assertEqual(res_hist.status_code, 200)
        data_hist = res_hist.json()
        self.assertEqual(data_hist.get("status"), "success")
        self.assertTrue(len(data_hist.get("history", [])) >= 1)
        self.assertEqual(data_hist["history"][0]["exercise_id"], "overhead_press")


if __name__ == "__main__":
    unittest.main()
