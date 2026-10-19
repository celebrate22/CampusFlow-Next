import os
import tempfile
import unittest

from campusflow.reports import build_summary
from campusflow.storage import TicketStorage
from campusflow.workflow import WorkflowEngine


class TestReports(unittest.TestCase):
    def test_empty_dataset_reports_zero_percent_without_error(self):
        s = build_summary([])
        self.assertEqual((s["total"], s["resolved"], s["unresolved"]), (0, 0, 0))
        self.assertEqual(s["resolution_percentage"], 0.0)
        self.assertEqual(sum(s["category"].values()), 0)

    def test_counts_match_fixture_after_resolve_and_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            e = WorkflowEngine(TicketStorage(os.path.join(folder, "t.json")))
            mk = lambda title, cat, urg, n: e.create_and_store_ticket(
                {"title": title, "category": cat, "urgency": urg, "affected_users": n})
            a = mk("a", "Network", "high", 12)      # critical
            b = mk("b", "Hardware", "low", 1)       # low
            c = mk("c", "Software", "medium", 1)    # medium
            d = mk("d", "Network", "low", 4)        # medium
            for tid in (a, b):
                e.assign_ticket_to_staff(tid, "Ada")
                e.transition_ticket_status(tid, "in_progress")
            e.transition_ticket_status(a, "resolved")
            e.transition_ticket_status(a, "open")        # reopened: counts as OPEN now
            e.transition_ticket_status(b, "resolved")    # resolved
            s = build_summary(e.get_all_tickets_list())
            self.assertEqual(s["total"], 4)
            self.assertEqual(s["status"], {"open": 3, "in_progress": 0, "resolved": 1})
            self.assertEqual(s["priority"], {"critical": 1, "high": 0, "medium": 2, "low": 1})
            self.assertEqual(s["category"], {"Network": 2, "Hardware": 1, "Software": 1, "Other": 0})
            self.assertEqual((s["unresolved"], s["resolved"]), (3, 1))
            self.assertEqual(s["resolution_percentage"], 25.0)
            self.assertEqual(sum(s["status"].values()), s["total"])   # nothing double-counted

    def test_in_progress_counts_as_unresolved(self):
        s = build_summary([{"status": "in_progress", "priority": "low", "category": "Other"}])
        self.assertEqual(s["unresolved"], 1)
        self.assertEqual(s["resolution_percentage"], 0.0)