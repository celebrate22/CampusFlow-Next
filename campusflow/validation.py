"""Whole-record and whole-collection validation, used when loading JSON.

Everything returns NEW normalized dicts and never edits its input, so a failed
validation can never leave half-changed data behind.
"""
from .tickets import (
    ALLOWED_CATEGORIES,
    ALLOWED_PRIORITIES,
    ALLOWED_STATUSES,
    ALLOWED_URGENCIES,
    NOTE_ID_PATTERN,
    NOTE_MAX_LENGTH,
    NOTE_MIN_LENGTH,
    TICKET_ID_PATTERN,
    calculate_priority,
)

REQUIRED_TICKET_KEYS = (
    "id", "title", "category", "urgency", "affected_users", "priority", "status", "assigned_to",
)
OPTIONAL_TICKET_KEYS = ("notes",)  # absent in files written by the first CampusFlow version
NOTE_KEYS = {"note_id", "author", "message"}


def _fail(ticket_id, problem):
    raise ValueError(f"ticket '{ticket_id}': {problem}")


def validate_note_record(ticket_id, note, seen_ids) -> dict:
    if not isinstance(note, dict):
        _fail(ticket_id, "each note must be a JSON object.")
    if set(note.keys()) != NOTE_KEYS:
        _fail(ticket_id, f"a note must have exactly the keys {sorted(NOTE_KEYS)}.")
    note_id, author, message = note["note_id"], note["author"], note["message"]
    if not isinstance(note_id, str) or not NOTE_ID_PATTERN.fullmatch(note_id):
        _fail(ticket_id, f"invalid note ID {note_id!r}.")
    if note_id in seen_ids:
        _fail(ticket_id, f"duplicate note ID '{note_id}'.")
    if not isinstance(author, str) or author.strip() == "":
        _fail(ticket_id, f"note '{note_id}' has a blank author.")
    if not isinstance(message, str) or not (NOTE_MIN_LENGTH <= len(message.strip()) <= NOTE_MAX_LENGTH):
        _fail(ticket_id, f"note '{note_id}' message must be {NOTE_MIN_LENGTH}-{NOTE_MAX_LENGTH} characters.")
    return {"note_id": note_id, "author": author.strip(), "message": message.strip()}


def validate_ticket_record(key, record) -> dict:
    """Check one stored ticket and return a normalized copy (adds notes=[] if missing)."""
    if not isinstance(key, str) or not TICKET_ID_PATTERN.fullmatch(key):
        raise ValueError(f"invalid ticket ID {key!r} (expected T followed by digits).")
    if not isinstance(record, dict):
        _fail(key, "record must be a JSON object.")

    missing = [k for k in REQUIRED_TICKET_KEYS if k not in record]
    if missing:
        _fail(key, f"missing required keys {missing}.")
    unexpected = [k for k in record if k not in REQUIRED_TICKET_KEYS + OPTIONAL_TICKET_KEYS]
    if unexpected:
        _fail(key, f"unexpected keys {unexpected}.")

    if record["id"] != key:
        _fail(key, f"stored id {record['id']!r} does not match its key.")
    if not isinstance(record["title"], str) or record["title"].strip() == "":
        _fail(key, "title must be non-blank text.")
    if record["category"] not in ALLOWED_CATEGORIES:
        _fail(key, f"illegal category {record['category']!r}.")
    if record["urgency"] not in ALLOWED_URGENCIES:
        _fail(key, f"illegal urgency {record['urgency']!r}.")

    users = record["affected_users"]
    if isinstance(users, bool) or not isinstance(users, int) or users <= 0:
        _fail(key, f"affected_users must be a positive integer, got {users!r}.")

    if record["priority"] not in ALLOWED_PRIORITIES:
        _fail(key, f"illegal priority {record['priority']!r}.")
    expected_priority = calculate_priority(record["urgency"], users)
    if record["priority"] != expected_priority:
        _fail(key, f"priority {record['priority']!r} contradicts urgency/affected_users "
                   f"(rules give {expected_priority!r}).")

    if record["status"] not in ALLOWED_STATUSES:
        _fail(key, f"illegal status {record['status']!r}.")
    assigned = record["assigned_to"]
    if assigned is not None and (not isinstance(assigned, str) or assigned.strip() == ""):
        _fail(key, "assigned_to must be null or a non-blank name.")
    if record["status"] == "in_progress" and assigned is None:
        _fail(key, "an in_progress ticket must be assigned.")

    raw_notes = record.get("notes", [])
    if not isinstance(raw_notes, list):
        _fail(key, "notes must be a list.")
    seen, notes = set(), []
    for raw_note in raw_notes:
        note = validate_note_record(key, raw_note, seen)
        seen.add(note["note_id"])
        notes.append(note)

    return {
        "id": key,
        "title": record["title"].strip(),
        "category": record["category"],
        "urgency": record["urgency"],
        "affected_users": users,
        "priority": record["priority"],
        "status": record["status"],
        "assigned_to": assigned.strip() if isinstance(assigned, str) else None,
        "notes": notes,
    }


def validate_collection(data) -> dict:
    """Validate the whole {ticket_id: record} mapping. All-or-nothing."""
    if not isinstance(data, dict):
        raise ValueError("file must contain a JSON object mapping ticket IDs to ticket data.")
    return {key: validate_ticket_record(key, record) for key, record in data.items()}