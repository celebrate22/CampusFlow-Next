import unittest

from campusflow.tickets import (
    calculate_priority, ticket_number, validate_affected_users, validate_note_message,
)


class TestPriorityEngine(unittest.TestCase):
    def test_rule_precedence_and_boundaries(self):
        cases = [
            ("high", 12, "critical"), ("high", 10, "critical"), ("high", 9, "high"),
            ("high", 2, "high"), ("low", 10, "high"), ("medium", 9, "medium"),
            ("low", 4, "medium"), ("low", 3, "medium"), ("low", 2, "low"), ("low", 1, "low"),
        ]
        for urgency, users, expected in cases:
            with self.subTest(urgency=urgency, users=users):
                self.assertEqual(calculate_priority(urgency, users), expected)


class TestValidators(unittest.TestCase):
    def test_invalid_affected_users_rejected(self):
        for bad in (0, -3, 5.5, 5.0, True, False, "abc", "5.5", "", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate_affected_users(bad)

    def test_valid_affected_users_accepted(self):
        self.assertEqual(validate_affected_users(12), 12)
        self.assertEqual(validate_affected_users(" 12 "), 12)

    def test_note_message_length_is_measured_after_trimming(self):
        self.assertEqual(validate_note_message("  hello  "), "hello")
        with self.assertRaises(ValueError):
            validate_note_message("   hi   ")          # 2 chars after trim
        with self.assertRaises(ValueError):
            validate_note_message("x" * 301)
        self.assertEqual(len(validate_note_message("x" * 300)), 300)

    def test_numeric_id_ordering_helper(self):
        self.assertLess(ticket_number("T2"), ticket_number("T10"))