# campusflow/workflow.py
"""Business rules: create, view, assign, change status, notes, search and the work queue.

Error convention (one pattern everywhere): invalid input / illegal action raises
ValueError, unknown ticket raises KeyError, failed save raises OSError. Every action
validates BEFORE it mutates, and a failed save is undone, so a rejected action
leaves the whole ticket collection unchanged.
"""
import copy
from dataclasses import asdict

from .notes import build_note, sorted_notes
from .search import search_tickets
from .tickets import (
    PRIORITY_WEIGHTS,  # re-exported: older code/tests import it from here
    Ticket,
    calculate_priority,
    priority_sort_key,
    validate_affected_users,
    validate_category,
    validate_staff_name,
    validate_status,
    validate_title,
    validate_urgency,
)

# Allowed status moves. Anything not listed here is rejected.
ALLOWED_TRANSITIONS = {
    "open": {"in_progress"},
    "in_progress": {"resolved"},
    "resolved": {"open"},  # explicit reopen
}

# Original Open Work Queue: ONLY open tickets (see docs/design-decisions.md).
QUEUE_STATUSES = {"open"}

# Notes may only be added while the ticket is still being worked on.
NOTE_STATUSES = {"open", "in_progress"}


def can_transition(current_status, target_status):
    """True if the workflow allows current -> target (assignment rule is checked separately)."""
    return target_status in ALLOWED_TRANSITIONS.get(current_status, set())


class WorkflowEngine:
    def __init__(self, storage_manager):
        self.storage = storage_manager
        # F7: reload on startup (raises ValueError if the file is corrupted)
        self.tickets = self.storage.load_tickets_from_json()

    # ---------- helpers ----------
    def _get_ticket(self, ticket_id):
        """Return the REAL stored ticket (internal use only)."""
        if not isinstance(ticket_id, str) or ticket_id not in self.tickets:
            raise KeyError(f"Operation Failed: Ticket ID '{ticket_id}' does not exist.")
        return self.tickets[ticket_id]

    def _save_or_undo(self, undo):
        """Save to disk; if saving fails, undo the in-memory change and re-raise."""
        try:
            self.storage.save_tickets_to_json(self.tickets)
        except OSError:
            undo()
            raise

    # ---------- F7: reload ----------
    def reload_from_storage(self):
        """Re-read the JSON file. On ANY validation failure memory stays untouched."""
        loaded = self.storage.load_tickets_from_json()  # raises before we replace anything
        self.tickets = loaded
        return len(loaded)

    # ---------- F1 ----------
    def create_and_store_ticket(self, raw_user_inputs):
        title = validate_title(raw_user_inputs.get("title", ""))
        category = validate_category(raw_user_inputs.get("category", ""))
        urgency = validate_urgency(raw_user_inputs.get("urgency", ""))
        affected_users = validate_affected_users(raw_user_inputs.get("affected_users"))

        # Only generate an ID after every check has passed.
        next_id = self.storage.generate_next_sequential_id()
        ticket = Ticket(
            id=next_id,
            title=title,
            category=category,
            urgency=urgency,
            affected_users=affected_users,
            priority=calculate_priority(urgency, affected_users),
            status="open",
            assigned_to=None,
            notes=[],
        )

        self.tickets[next_id] = asdict(ticket)

        def undo():
            self.tickets.pop(next_id, None)
            self.storage.release_id(next_id)

        self._save_or_undo(undo)
        return next_id

    # ---------- F2 (deep copies: callers can never edit stored data, notes included) ----------
    def get_single_ticket_by_id(self, ticket_id):
        return copy.deepcopy(self._get_ticket(ticket_id))

    def get_all_tickets_list(self):
        return [copy.deepcopy(t) for t in self.tickets.values()]

    # ---------- F3 ----------
    def assign_ticket_to_staff(self, ticket_id, staff_name):
        ticket = self._get_ticket(ticket_id)

        clean_name = validate_staff_name(staff_name)
        if ticket["status"] == "resolved":
            raise ValueError(
                "Assignment Failed: Cannot assign staff to a 'resolved' ticket. Reopen it first."
            )

        previous = ticket["assigned_to"]
        ticket["assigned_to"] = clean_name
        self._save_or_undo(lambda: ticket.update(assigned_to=previous))

    # ---------- F4 ----------
    def transition_ticket_status(self, ticket_id, target_status):
        ticket = self._get_ticket(ticket_id)
        current = ticket["status"]

        if not isinstance(target_status, str) or target_status.strip() == "":
            raise ValueError("Workflow Error: Target status cannot be empty.")
        target = validate_status(target_status)

        if not can_transition(current, target):
            if current == "resolved":
                raise ValueError(
                    "Workflow Error: A resolved ticket is locked. "
                    "It must be explicitly reopened to 'open' first."
                )
            raise ValueError(
                f"Workflow Error: Cannot transition from '{current}' to '{target}'. "
                f"Allowed next status: {sorted(ALLOWED_TRANSITIONS[current])}."
            )

        if target == "in_progress" and not ticket.get("assigned_to"):
            raise ValueError(
                "Workflow Error: Cannot move an unassigned ticket into 'in_progress'. "
                "Assign staff first."
            )

        ticket["status"] = target
        self._save_or_undo(lambda: ticket.update(status=current))

    # ---------- F5 (original queue: unchanged behaviour) ----------
    def get_sorted_work_queue(self):
        """Open tickets only, ordered critical -> low, ties broken by earlier numeric ID."""
        queue = [t for t in self.tickets.values() if t["status"] in QUEUE_STATUSES]
        return [copy.deepcopy(t) for t in sorted(queue, key=priority_sort_key)]

    # ---------- Notes ----------
    def add_note(self, ticket_id, author, message):
        """Add a follow-up note and return its note ID (e.g. 'N001').

        Contract:
          - ticket must exist (KeyError) and be 'open' or 'in_progress' (ValueError)
          - author must be non-blank; message must be 5-300 chars after trimming (ValueError)
          - on any failure nothing changes and no note ID is consumed
          - if the save fails, the note is removed again and OSError is re-raised
        """
        ticket = self._get_ticket(ticket_id)
        if ticket["status"] not in NOTE_STATUSES:
            raise ValueError(
                f"Note Failed: Ticket '{ticket_id}' is '{ticket['status']}'. "
                "Notes can only be added to open or in_progress tickets; reopen it first."
            )

        note = build_note(ticket, author, message)  # validates; does not touch the ticket
        ticket["notes"].append(note)

        def undo():
            if ticket["notes"] and ticket["notes"][-1] is note:
                ticket["notes"].pop()

        self._save_or_undo(undo)
        return note["note_id"]

    def get_ticket_notes(self, ticket_id):
        """All notes for a ticket as copies, in note-ID order (works for resolved tickets too)."""
        return sorted_notes(self._get_ticket(ticket_id))

    # ---------- Search (read-only) ----------
    def search(self, title_query="", category="", status="", priority=""):
        """Title substring (case-insensitive) AND every supplied filter. Never edits data."""
        return search_tickets(self.tickets.values(), title_query, category, status, priority)