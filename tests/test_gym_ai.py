"""
Automated unit & integration test suite for Gym AI in FitPath.
"""

import asyncio
import os
import unittest

from gym_ai.database.formatters import format_food
from gym_ai.llm import agenerate_answer, generate_answer, strip_thinking_tokens
from gym_ai.pipeline import arun_pipeline, run_pipeline
from gym_ai.planner import generate_personalized_plan
from gym_ai.rag.context_builder import build_context
from gym_ai.router import extract_portion_grams, route_query


class TestGymAI(unittest.TestCase):
    def test_strip_thinking_tokens(self):
        text = "<think>Let me see what the calories are.</think>Chicken breast has 165 calories."
        cleaned = strip_thinking_tokens(text)
        self.assertEqual(cleaned, "Chicken breast has 165 calories.")

    def test_portion_gram_extraction(self):
        self.assertEqual(extract_portion_grams("How much protein in 200g of chicken breast?"), 200.0)
        self.assertEqual(extract_portion_grams("Calories in 150 grams of rice?"), 150.0)
        self.assertEqual(extract_portion_grams("Macros for 0.5kg beef?"), 500.0)
        self.assertIsNone(extract_portion_grams("What muscles does squat work?"))

    def test_gram_based_nutrition_scaling(self):
        mock_food = (101, "Chicken Breast", 165.0, 31.0, 0.0, 3.6)
        # Baseline 100g
        baseline_str = format_food(mock_food)
        self.assertIn("165.0 kcal", baseline_str)
        self.assertIn("31.0 g", baseline_str)

        # Scaled to 200g (should double values)
        scaled_str = format_food(mock_food, grams=200.0)
        self.assertIn("Portion: 200g", scaled_str)
        self.assertIn("330.0 kcal", scaled_str)
        self.assertIn("62.0 g", scaled_str)

    def test_llm_generation(self):
        ans = generate_answer("Reply with the single word: READY", stream=False)
        self.assertTrue("ready" in ans.lower())

    def test_query_routing(self):
        r_gen = route_query("Hello coach, how are you?")
        self.assertEqual(r_gen, "general")

        r_db = route_query("How many calories in an apple?")
        self.assertIn(r_db, ("database", "both", "general"))

        r_rag = route_query("How do I avoid shoulder pain during bench press?")
        self.assertIn(r_rag, ("rag", "both", "general"))

    def test_rag_context_builder(self):
        context = build_context("knee pain recovery and rehabilitation")
        self.assertIsInstance(context, str)
        self.assertTrue(len(context) > 0)

    def test_personalized_plan_generator(self):
        test_profile = {
            "name": "Test Athlete",
            "goal": "fat_loss",
            "experience": "beginner",
            "injuries": ["knees"],
            "equipment": "bodyweight",
            "time_budget_min": 20,
        }
        test_handoff = {
            "weekly": {"workouts": 2, "reps": 40},
            "latest_report": {"fatigue": "moderate"},
        }
        plan = generate_personalized_plan(profile=test_profile, handoff=test_handoff)
        self.assertIn("plan", plan)
        self.assertIn("nutrition_recovery", plan)
        self.assertIn("coach_notes", plan)
        self.assertTrue(len(plan["plan"]) > 0)

    def test_pipeline_personalization(self):
        profile = {"name": "Lina", "goal": "strength", "injuries": ["knees"], "weight_kg": 65, "height_cm": 168}
        answer = run_pipeline(
            "What should I keep in mind for lower body training?",
            stream=False,
            athlete_context={"athlete": profile},
        )
        self.assertIsInstance(answer, str)
        self.assertTrue(len(answer) > 20)

    def test_out_of_scope_restriction(self):
        query = "Write a python script to sort a list using quicksort"
        route = route_query(query)
        self.assertEqual(route, "out_of_scope")

        answer = run_pipeline(query, stream=False)
        self.assertIn("Gym AI", answer)
        self.assertIn("only assist with fitness", answer.lower())

    def test_athlete_self_inquiry_allowed(self):
        # 1. Routing checks: all self-referential queries must be classified as 'general', NOT 'out_of_scope'
        self_queries = [
            "Who am I?",
            "What is my current weight?",
            "How tall am I?",
            "What injuries do I have?",
            "What is my goal?",
            "What is my BMI?",
            "Tell me about myself and my profile",
        ]
        for q in self_queries:
            route = route_query(q)
            self.assertEqual(
                route, "general", f"Query '{q}' should route to 'general', got '{route}'"
            )

        # 2. Pipeline execution check: Verify the coach answers using profile facts and does not refuse
        profile = {
            "name": "Menna Hassanin",
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "goal": "health",
            "injuries": ["back"],
        }
        answer = run_pipeline("Who am I and what is my weight?", stream=False, athlete_context={"athlete": profile})
        self.assertNotIn("only assist with fitness", answer.lower())
        self.assertTrue(
            "menna" in answer.lower() or "70" in answer,
            f"Expected athlete name or weight in answer, got: {answer}",
        )

    def test_biometrics_calculation(self):
        from common.profile import calculate_biometrics
        profile = {
            "weight_kg": 80.0,
            "height_cm": 180.0,
            "age": 28,
            "gender": "male",
            "goal": "strength",
        }
        bio = calculate_biometrics(profile)
        self.assertEqual(bio["bmi"], 24.7)
        self.assertEqual(bio["bmi_category"], "Normal weight")
        self.assertGreater(bio["protein_target_g"], 150)
        self.assertGreater(bio["bmr_kcal"], 1500)

    def test_in_chat_biometrics_parsing(self):
        from gym_ai.router import parse_biometric_updates
        updates = parse_biometric_updates("I weigh 82.5kg and my height is 185 cm")
        self.assertEqual(updates.get("weight_kg"), 82.5)
        self.assertEqual(updates.get("height_cm"), 185.0)

    def test_qwen_embedding_generation(self):
        from gym_ai.rag.embeddings import get_embeddings
        emb = get_embeddings()
        vec = emb.embed_query("Squat technique and depth")
        self.assertEqual(len(vec), 1024)


if __name__ == "__main__":
    unittest.main()
