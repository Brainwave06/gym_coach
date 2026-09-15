"""
Unit tests for persistent memory, SQLite storage, PRs, and 1RM calculation.
"""

import unittest

from gym_ai.memory.pr_tracker import calculate_epley_1rm, format_pr_summary, is_pr_inquiry, parse_pr_from_text
from gym_ai.memory.storage import (
    build_memory_context_prompt,
    get_all_personal_records,
    get_best_pr,
    get_recent_messages,
    init_db,
    log_personal_record,
    save_chat_message,
)


class TestMemoryAndPRs(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_epley_1rm_calculation(self):
        # 100kg x 10 reps: 100 * (1 + 10/30) = 133.3 kg
        one_rm = calculate_epley_1rm(100.0, 10)
        self.assertEqual(one_rm, 133.3)

        # 1 rep at 150kg should return exactly 150kg
        self.assertEqual(calculate_epley_1rm(150.0, 1), 150.0)

        # 0 or negative
        self.assertEqual(calculate_epley_1rm(0, 5), 0.0)

    def test_pr_parsing_from_text(self):
        # Bench press
        p1 = parse_pr_from_text("I benched 80kg for 5 reps today")
        self.assertIsNotNone(p1)
        self.assertEqual(p1["exercise"], "Bench Press")
        self.assertEqual(p1["weight_kg"], 80.0)
        self.assertEqual(p1["reps"], 5)
        self.assertEqual(p1["estimated_1rm"], 93.3)

        # Squat
        p2 = parse_pr_from_text("New squat PR: 120kg x 3")
        self.assertIsNotNone(p2)
        self.assertEqual(p2["exercise"], "Squat")
        self.assertEqual(p2["weight_kg"], 120.0)
        self.assertEqual(p2["reps"], 3)

        # Deadlift
        p3 = parse_pr_from_text("Deadlift 150 kg for 1 rep")
        self.assertIsNotNone(p3)
        self.assertEqual(p3["exercise"], "Deadlift")
        self.assertEqual(p3["weight_kg"], 150.0)
        self.assertEqual(p3["reps"], 1)

        # Unrelated text
        self.assertIsNone(parse_pr_from_text("What should I eat today?"))

    def test_pr_inquiry_detection(self):
        self.assertTrue(is_pr_inquiry("What is my bench press PR?"))
        self.assertTrue(is_pr_inquiry("Show my personal records"))
        self.assertTrue(is_pr_inquiry("What are my PRs?"))
        self.assertTrue(is_pr_inquiry("Tell me my 1rm"))
        self.assertFalse(is_pr_inquiry("How many calories in an apple?"))

    def test_sqlite_pr_logging_and_retrieval(self):
        test_uid = "test_athlete_123"
        log_personal_record("Bench Press", 85.0, 5, user_id=test_uid)
        log_personal_record("Bench Press", 90.0, 3, user_id=test_uid)
        log_personal_record("Squat", 110.0, 5, user_id=test_uid)

        prs = get_all_personal_records(user_id=test_uid)
        self.assertGreaterEqual(len(prs), 3)

        best_bench = get_best_pr("Bench Press", user_id=test_uid)
        self.assertIsNotNone(best_bench)
        self.assertEqual(best_bench["exercise_name"], "Bench Press")

    def test_conversation_persistence(self):
        import uuid
        cid = f"thread_test_{uuid.uuid4().hex[:8]}"
        save_chat_message("user", "Hello coach, I'm ready to train.", conversation_id=cid)
        save_chat_message("assistant", "Let's do this! What are we hitting today?", conversation_id=cid)

        msgs = get_recent_messages(conversation_id=cid, limit=10)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[1]["role"], "assistant")


if __name__ == "__main__":
    unittest.main()
