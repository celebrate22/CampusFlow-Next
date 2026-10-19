import copy
import json
import os
import tempfile
import unittest

from campusflow.storage import TicketStorage
from campusflow.workflow import WorkflowEngine

GOOD = {
    "id": "T001", "title": "Wi-Fi down", "category": "Network", "urgency": "high",
    "affected_users": 15, "priority": "critical", "status": "open", "assigned_to": None, "notes": [],
}


class TestStorage(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "tickets.json")

    def _write_text(self, text):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(text)

    def _engine(self):
        return WorkflowEngine(TicketStorage(self.path))

    def test_save_and_reload_preserve_tickets_notes_and_next_ids(self):
        e1 = self._engine()
        t1 = e1.create_and_store_ticket({"title": "Wi-Fi down", "category": "network", "urgency": "high", "affected_users": "15"})
        e1.add_note(t1, "Mentor A", "first note here")
        e1.add_note(t1, "Mentor B", "second note here")
        e2 = self._engine()                                    # simulated restart
        self.assertEqual(e2.tickets, e1.tickets)
        self.assertEqual(e2.add_note(t1, "Mentor A", "third note here"), "N003")
        self.assertEqual(e2.create_and_store_ticket({"title": "Laptop", "category": "Hardware", "urgency": "low", "affected_users": 1}), "T002")

    def test_missing_file_starts_fresh(self):
        self.assertEqual(self._engine().tickets, {})

    def test_corrupt_json_rejected_at_startup(self):
        self._write_text("{ not valid json")
        with self.assertRaises(ValueError):
            self._engine()

    def test_duplicate_ticket_id_in_file_rejected(self):
        one = json.dumps(GOOD)
        self._write_text('{"T001": %s, "T001": %s}' % (one, one))
        with self.assertRaises(ValueError) as ctx:
            self._engine()
        self.assertIn("duplicate", str(ctx.exception).lower())

    def test_invalid_reload_keeps_memory_and_id_counter_unchanged(self):
        engine = self._engine()
        engine.create_and_store_ticket({"title": "Wi-Fi down", "category": "Network", "urgency": "high", "affected_users": 15})
        before = copy.deepcopy(engine.tickets)
        bad = dict(GOOD, id="T002", status="resolved", priority="low")     # priority contradicts rules
        self._write_text(json.dumps({"T001": GOOD, "T002": bad}))
        with self.assertRaises(ValueError):
            engine.reload_from_storage()
        self.assertEqual(engine.tickets, before)
        self.assertEqual(engine.storage.generate_next_sequential_id(), "T002")   # counter intact

    def test_each_kind_of_bad_record_is_rejected(self):
        bad_records = {
            "missing key": {k: v for k, v in GOOD.items() if k != "status"},
            "bad status": dict(GOOD, status="done"),
            "bad category": dict(GOOD, category="Plumbing"),
            "zero users": dict(GOOD, affected_users=0),
            "bool users": dict(GOOD, affected_users=True),
            "in_progress unassigned": dict(GOOD, status="in_progress"),
            "id/key mismatch": dict(GOOD, id="T009"),
            "duplicate note ids": dict(GOOD, notes=[{"note_id": "N001", "author": "A", "message": "hello there"}] * 2),
            "short note": dict(GOOD, notes=[{"note_id": "N001", "author": "A", "message": "hi"}]),
            "note wrong shape": dict(GOOD, notes=[{"note_id": "N001", "author": "A"}]),
        }
        for label, record in bad_records.items():
            with self.subTest(label):
                self._write_text(json.dumps({"T001": record}))
                with self.assertRaises(ValueError):
                    self._engine()

    def test_legacy_file_without_notes_still_loads(self):
        legacy = {k: v for k, v in GOOD.items() if k != "notes"}
        self._write_text(json.dumps({"T001": legacy}))
        engine = self._engine()
        self.assertEqual(engine.get_ticket_notes("T001"), [])
        self.assertEqual(engine.add_note("T001", "Mentor A", "upgrading old data"), "N001")