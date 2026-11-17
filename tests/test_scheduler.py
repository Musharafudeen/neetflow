import unittest
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neetflow import scheduler, test_engine, database

class TestNEETFlow(unittest.TestCase):
    def setUp(self):
        database.init_db()

    def test_daily_hour_calculation(self):
        guide = scheduler.calculate_daily_hour_guidelines(10.0)
        self.assertEqual(guide["total_hours"], 10.0)
        self.assertGreater(guide["biology_total_hours"], 0)
        self.assertGreater(guide["physics_hours"], 0)
        self.assertGreater(guide["chemistry_hours"], 0)
        self.assertGreater(guide["revision_hours"], 0)
        self.assertAlmostEqual(guide["weekly_hours"], 70.0)

    def test_roadmap_generation(self):
        roadmap = scheduler.generate_roadmap(timeline_id=999, total_days=180, daily_hours=10.0)
        self.assertEqual(roadmap["total_days"], 180)
        self.assertGreater(len(roadmap["tasks"]), 0)

        # Check subject coverage
        subjects = set(t["subject"] for t in roadmap["tasks"])
        self.assertTrue("Botany" in subjects or "All 4 Subjects" in subjects)
        self.assertTrue("Physics" in subjects or "All 4 Subjects" in subjects)

    def test_grading_engine(self):
        questions = database.get_all_questions()
        if not questions:
            self.skipTest("No questions seeded")

        q = questions[0]
        # Test correct attempt (+4)
        result = test_engine.grade_submission("TEST", q["subject"], [
            {"question_id": q["id"], "user_answer": q["correct_answer"]}
        ])
        self.assertEqual(result["score"], 4)
        self.assertEqual(result["correct_count"], 1)

        # Test incorrect attempt (-1)
        result_wrong = test_engine.grade_submission("TEST", q["subject"], [
            {"question_id": q["id"], "user_answer": "DEFINITELY_WRONG_ANSWER_XYZ"}
        ])
        self.assertEqual(result_wrong["score"], -1)
        self.assertEqual(result_wrong["incorrect_count"], 1)

    def test_botany_zoology_high_weightage_priority(self):
        """Verifies that Botany and Zoology are recommended from Day 1 starting with High Weightage chapters."""
        roadmap = scheduler.generate_roadmap(timeline_id=888, total_days=180, daily_hours=10.0)
        day_1_tasks = [t for t in roadmap["tasks"] if t["day_number"] == 1]

        botany_d1 = next((t for t in day_1_tasks if t["subject"] == "Botany"), None)
        zoology_d1 = next((t for t in day_1_tasks if t["subject"] == "Zoology"), None)

        self.assertIsNotNone(botany_d1, "Botany should be present on Day 1")
        self.assertIsNotNone(zoology_d1, "Zoology should be present on Day 1")

        # Botany highest weightage is Molecular Basis of Inheritance (6 questions)
        self.assertEqual(botany_d1["weightage"], "High")
        self.assertIn("Molecular Basis of Inheritance", botany_d1["chapter_name"])
        self.assertEqual(botany_d1["avg_questions"], 6)

        # Zoology highest weightage is Animal Kingdom (4 questions)
        self.assertEqual(zoology_d1["weightage"], "High")
        self.assertEqual(zoology_d1["avg_questions"], 4)

    def test_customizable_n_days_timeline(self):
        """Verifies that arbitrary user-edited n days (e.g. 45, 75, 120, 365) are fully supported without overrun."""
        for custom_n in [30, 45, 75, 100, 150, 240, 365]:
            roadmap = scheduler.generate_roadmap(timeline_id=777, total_days=custom_n, daily_hours=10.0)
            self.assertEqual(roadmap["total_days"], custom_n)
            self.assertGreater(len(roadmap["tasks"]), 0)
            # All scheduled task day numbers must be <= custom_n
            max_day = max(t["day_number"] for t in roadmap["tasks"])
            self.assertLessEqual(max_day, custom_n, f"Task day {max_day} exceeds custom n={custom_n}")

if __name__ == "__main__":
    unittest.main()
