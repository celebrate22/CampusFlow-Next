import copy
import os
import tempfile
import unittest

from campusflow.storage import TicketStorage
from campusflow.workflow import WorkflowEngine


def make_engine(folder):
    return WorkflowEngine(TicketStorage(os.path.join(folder, "tickets.json")))


def new_ticket(engine, title="Printer down", category="Hardware", urgency="low", users=1):
    return engine.create_and_store_ticket(
        {"title": title, "category": category, "urgency": urgency, "affected_users": users}
    )


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.engine = make_engine(self._tmp.name)

    def test_unassigned_ticket_cannot_enter_in_progress_and_data_unchanged(self):
        tid = new_ticket(self.engine)
        before = copy.deepcopy(self.engine.tickets)
        with self.assertRaises(ValueError):
            self.engine.transition_ticket_status(tid, "in_progress")
        self.assertEqual(self.engine.tickets, before)

    def test_resolved_ticket_assignment_rejected_and_unchanged(self):
        tid = new_ticket(self.engine)
        self.engine.assign_ticket_to_staff(tid, "Ada")
        self.engine.transition_ticket_status(tid, "in_progress")
        self.engine.transition_ticket_status(tid, "resolved")
        before = copy.deepcopy(self.engine.tickets)
        with self.assertRaises(ValueError):
            self.engine.assign_ticket_to_staff(tid, "Grace")
        self.assertEqual(self.engine.tickets, before)

    def test_full_lifecycle_and_reopen(self):
        tid = new_ticket(self.engine)
        self.engine.assign_ticket_to_staff(tid, "Ada")
        for status in ("in_progress", "resolved", "open"):
            self.engine.transition_ticket_status(tid, status)
        self.assertEqual(self.engine.get_single_ticket_by_id(tid)["status"], "open")

    def test_illegal_jump_open_to_resolved_rejected(self):
        tid = new_ticket(self.engine)
        with self.assertRaises(ValueError):
            self.engine.transition_ticket_status(tid, "resolved")

    def test_unknown_ticket_id_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.engine.assign_ticket_to_staff("T999", "Ada")

    def test_invalid_create_changes_nothing_and_consumes_no_id(self):
        before = copy.deepcopy(self.engine.tickets)
        with self.assertRaises(ValueError):
            new_ticket(self.engine, users=0)
        self.assertEqual(self.engine.tickets, before)
        self.assertEqual(new_ticket(self.engine), "T001")

    def test_work_queue_is_open_only_sorted_with_numeric_tie_break(self):
        ids = [new_ticket(self.engine, urgency="low", users=1) for _ in range(10)]  # T001..T010
        crit = new_ticket(self.engine, urgency="high", users=12)                     # T011 critical
        self.engine.assign_ticket_to_staff(ids[0], "Ada")
        self.engine.transition_ticket_status(ids[0], "in_progress")                  # leaves queue
        queue_ids = [t["id"] for t in self.engine.get_sorted_work_queue()]
        self.assertEqual(queue_ids[0], crit)
        self.assertNotIn(ids[0], queue_ids)
        self.assertEqual(queue_ids[1:], ids[1:])           # T002 ... T010, numeric order

    def test_returned_copies_cannot_corrupt_stored_notes(self):
        tid = new_ticket(self.engine)
        self.engine.add_note(tid, "Mentor A", "first note here")
        copy_of_ticket = self.engine.get_single_ticket_by_id(tid)
        copy_of_ticket["notes"].clear()
        self.assertEqual(len(self.engine.get_ticket_notes(tid)), 1)