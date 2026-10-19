import copy
import os
import tempfile
import unittest
from unittest import mock

from campusflow.storage import TicketStorage
from campusflow.workflow import WorkflowEngine


class TestNotes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.engine = WorkflowEngine(TicketStorage(os.path.join(self._tmp.name, "t.json")))
        self.tid = self.engine.create_and_store_ticket(
            {"title": "Wi-Fi down", "category": "Network", "urgency": "high", "affected_users": 15}
        )

    def _resolve(self):
        self.engine.assign_ticket_to_staff(self.tid, "Ada")
        self.engine.transition_ticket_status(self.tid, "in_progress")
        self.engine.transition_ticket_status(self.tid, "resolved")

    def test_valid_notes_get_sequential_ids_in_order(self):
        self.assertEqual(self.engine.add_note(self.tid, "Mentor A", "Wi-Fi router reboot attempted"), "N001")
        self.assertEqual(self.engine.add_note(self.tid, "Mentor B", "Investigating switch ports"), "N002")
        notes = self.engine.get_ticket_notes(self.tid)
        self.assertEqual([n["note_id"] for n in notes], ["N001", "N002"])
        self.assertEqual(notes[0]["author"], "Mentor A")

    def test_rejected_notes_change_nothing_and_do_not_consume_an_id(self):
        before = copy.deepcopy(self.engine.tickets)
        for author, message in (("Mentor A", "   hi  "), ("Mentor A", "x" * 301), ("   ", "valid message"), (None, "valid message")):
            with self.subTest(author=author, message=message[:6]):
                with self.assertRaises(ValueError):
                    self.engine.add_note(self.tid, author, message)
        self.assertEqual(self.engine.tickets, before)
        self.assertEqual(self.engine.add_note(self.tid, "Mentor A", "a valid message"), "N001")

    def test_resolved_ticket_rejects_note_then_reopen_allows_n003_and_keeps_old_notes(self):
        self.engine.add_note(self.tid, "Mentor A", "Wi-Fi router reboot attempted")
        self.engine.add_note(self.tid, "Mentor B", "Investigating switch ports")
        self._resolve()
        before = copy.deepcopy(self.engine.tickets)
        with self.assertRaises(ValueError):
            self.engine.add_note(self.tid, "Mentor A", "this must be refused")
        self.assertEqual(self.engine.tickets, before)
        self.assertEqual(len(self.engine.get_ticket_notes(self.tid)), 2)   # readable while resolved
        self.engine.transition_ticket_status(self.tid, "open")
        self.assertEqual(self.engine.add_note(self.tid, "Mentor A", "reopened, trying again"), "N003")

    def test_note_on_unknown_ticket_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.engine.add_note("T404", "Mentor A", "no such ticket")

    def test_failed_save_rolls_back_note_and_id(self):
        before = copy.deepcopy(self.engine.tickets)
        with mock.patch.object(self.engine.storage, "save_tickets_to_json", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.engine.add_note(self.tid, "Mentor A", "this save will fail")
        self.assertEqual(self.engine.tickets, before)
        self.assertEqual(self.engine.add_note(self.tid, "Mentor A", "this save works"), "N001")