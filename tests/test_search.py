import copy
import unittest

from campusflow.search import normalize_filter, search_tickets, sort_by_priority_then_id


def t(tid, title, category, status, priority):
    return {"id": tid, "title": title, "category": category, "status": status,
            "priority": priority, "assigned_to": None, "notes": []}


FIXTURE = [
    t("T001", "Campus WiFi down", "Network", "open", "critical"),
    t("T002", "wifi slow in library", "Network", "resolved", "low"),
    t("T003", "WIFI printer offline", "Hardware", "open", "high"),
    t("T010", "Projector broken", "Hardware", "open", "high"),
    t("T004", "Projector lamp", "Hardware", "open", "critical"),
]


class TestSearch(unittest.TestCase):
    def ids(self, results):
        return [r["id"] for r in results]

    def test_title_search_ignores_case_and_matches_substring(self):
        self.assertEqual(self.ids(search_tickets(FIXTURE, "WIFI")), ["T001", "T002", "T003"])
        self.assertEqual(self.ids(search_tickets(FIXTURE, "wi")), ["T001", "T002", "T003"])
        a = [t("T001", "WI-FI out", "Network", "open", "low")]
        self.assertEqual(self.ids(search_tickets(a, "wi-fi")), ["T001"])

    def test_filters_combine_with_and(self):
        self.assertEqual(self.ids(search_tickets(FIXTURE, "wifi", "Network", "open")), ["T001"])
        self.assertEqual(self.ids(search_tickets(FIXTURE, "", "hardware", "open", "high")), ["T003", "T010"])

    def test_empty_filters_mean_no_filtering(self):
        self.assertEqual(len(search_tickets(FIXTURE)), len(FIXTURE))
        self.assertEqual(search_tickets(FIXTURE, "no such title"), [])

    def test_search_is_read_only(self):
        before = copy.deepcopy(FIXTURE)
        results = search_tickets(FIXTURE, "wifi")
        results[0]["title"] = "mutated"
        results[0]["notes"].append("x")
        self.assertEqual(FIXTURE, before)

    def test_priority_sort_view_uses_numeric_id_tie_break(self):
        ordered = self.ids(sort_by_priority_then_id(FIXTURE))
        self.assertEqual(ordered, ["T001", "T004", "T003", "T010", "T002"])  # T3 before T10

    def test_normalize_filter(self):
        self.assertEqual(normalize_filter("category", " network "), "Network")
        self.assertEqual(normalize_filter("status", ""), "")
        with self.assertRaises(ValueError):
            normalize_filter("priority", "urgent")