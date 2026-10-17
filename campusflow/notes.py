"""Follow-up note helpers. Pure functions: no printing, no file access, no mutation.

A note is {"note_id": "N001", "author": "...", "message": "..."} and lives in a
ticket's "notes" list. Note IDs are per ticket. The next ID is derived from the
notes that exist, so a rejected note can never consume an ID.
"""
from .tickets import validate_note_author, validate_note_message


def _note_number(note_id) -> int:
    raw = str(note_id)
    return int(raw[1:]) if raw.startswith("N") and raw[1:].isdigit() else 0


def next_note_id(ticket) -> str:
    """Return the next free note ID for this ticket (N001 for a ticket with no notes)."""
    highest = max((_note_number(n.get("note_id")) for n in ticket.get("notes", [])), default=0)
    return f"N{highest + 1:03d}"


def build_note(ticket, author, message) -> dict:
    """Validate author + message and return a NEW note dict. Does not touch the ticket."""
    clean_author = validate_note_author(author)
    clean_message = validate_note_message(message)
    return {
        "note_id": next_note_id(ticket),
        "author": clean_author,
        "message": clean_message,
    }


def sorted_notes(ticket) -> list:
    """Copies of the ticket's notes in numeric note-ID order."""
    return [dict(n) for n in sorted(ticket.get("notes", []), key=lambda n: _note_number(n.get("note_id")))]