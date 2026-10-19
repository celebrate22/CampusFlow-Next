import unittest

from campusflow.question_bank import QUESTION_BANK
from campusflow.understanding_check import normalize_choice, run_understanding_check, score_answers


def scripted(replies):
    it = iter(replies)
    return lambda prompt="": next(it)


class TestUnderstandingCheck(unittest.TestCase):
    def test_bank_has_six_well_formed_questions(self):
        self.assertEqual(len(QUESTION_BANK), 6)
        for q in QUESTION_BANK:
            self.assertEqual(set(q["options"]), {"A", "B", "C", "D"})
            self.assertIn(q["correct"], q["options"])

    def test_normalize_choice(self):
        self.assertEqual(normalize_choice(" b "), "B")
        for bad in ("", "E", "AB", "1"):
            self.assertIsNone(normalize_choice(bad))

    def test_scoring_is_separate_from_the_menu_and_uses_any_bank(self):
        fake_bank = [{"id": "X1", "correct": "A"}, {"id": "X2", "correct": "D"}]
        self.assertEqual(score_answers({"X1": "A", "X2": "B"}, fake_bank), 1)
        self.assertEqual(score_answers({}, fake_bank), 0)

    def test_invalid_answer_is_retried_and_perfect_run_scores_six(self):
        replies = []
        for q in QUESTION_BANK:
            if q["id"] == "Q1":
                replies += ["Z", "", "9"]            # three invalid inputs first
            replies.append(q["correct"].lower())
            if q["id"] in ("Q1", "Q5"):
                replies += ["short", "a proper explanation from my code"]   # too short, then ok
        out = []
        result = run_understanding_check(scripted(replies), out.append)
        self.assertEqual(result["score"], 6)
        self.assertEqual(sum("[INVALID] Please type A" in line for line in out), 3)
        self.assertEqual(set(result["explanations"]), {"Q1", "Q5"})

    def test_score_reflects_actual_submitted_answers(self):
        wrong = {"A": "B", "B": "A", "C": "A", "D": "A"}
        replies = []
        for q in QUESTION_BANK:
            replies.append(wrong[q["correct"]] if q["id"] in ("Q2", "Q3") else q["correct"])
            if q["id"] in ("Q1", "Q5"):
                replies.append("an explanation long enough")
        result = run_understanding_check(scripted(replies), lambda *_: None)
        self.assertEqual(result["score"], 4)