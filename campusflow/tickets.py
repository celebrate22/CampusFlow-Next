"""Ticket data shape, input validators and the priority engine.

Everything here is plain business logic: no input(), no print(), no file access.
That makes it easy to unit test.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional

ALLOWED_CATEGORIES = ("Network", "Hardware", "Software", "Other")
ALLOWED_URGENCIES = ("low", "medium", "high")
ALLOWED_STATUSES = ("open", "in_progress", "resolved")
ALLOWED_PRIORITIES = ("critical", "high", "medium", "low")

# Lower weight = more urgent. Shared by the Open Work Queue and search sorting.
PRIORITY_WEIGHTS = {"critical": 1, "high": 2, "medium": 3, "low": 4}

NOTE_MIN_LENGTH = 5
NOTE_MAX_LENGTH = 300

TICKET_ID_PATTERN = re.compile(r"T[0-9]+")
NOTE_ID_PATTERN = re.compile(r"N[0-9]+")


@dataclass
class Ticket:
    id: str
    title: str
    category: str
    urgency: str
    affected_users: int
    priority: str
    status: str = "open"
    assigned_to: Optional[str] = None
    notes: List[dict] = field(default_factory=list)  # each: note_id, author, message


# ---------- validators ----------
def validate_title(title_text) -> str:
    """Return the trimmed title, or raise ValueError if it is blank or not text."""
    if not isinstance(title_text, str):
        raise ValueError("Validation Failed: Title must be text.")
    cleaned = title_text.strip()
    if cleaned == "":
        raise ValueError("Validation Failed: Title cannot be empty or just blank spaces.")
    return cleaned


def validate_category(category_text) -> str:
    """Normalize case ('network' -> 'Network') and check against allowed categories."""
    cleaned = str(category_text).strip().capitalize()
    if cleaned not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"Validation Failed: Category must be one of {list(ALLOWED_CATEGORIES)}."
        )
    return cleaned


def validate_urgency(urgency_text) -> str:
    """Normalize case ('HIGH' -> 'high') and check against allowed urgency levels."""
    cleaned = str(urgency_text).strip().lower()
    if cleaned not in ALLOWED_URGENCIES:
        raise ValueError(
            f"Validation Failed: Urgency must be one of {list(ALLOWED_URGENCIES)}."
        )
    return cleaned


def validate_status(status_text) -> str:
    """Normalize case and check against the allowed workflow states."""
    cleaned = str(status_text).strip().lower()
    if cleaned not in ALLOWED_STATUSES:
        raise ValueError(
            f"Validation Failed: Status must be one of {list(ALLOWED_STATUSES)}."
        )
    return cleaned


def validate_affected_users(users_input) -> int:
    """Return affected_users as a positive int.

    Rejects text, decimals (5.5, 5.0, "5.0"), booleans, zero and negatives.
    Whole-number strings such as "12" or " 12 " are accepted, because the CLI
    receives everything as text from input().
    """
    if isinstance(users_input, bool):
        raise ValueError("Validation Failed: affected_users cannot be a boolean value.")

    if isinstance(users_input, int):
        value = users_input
    elif isinstance(users_input, str) and re.fullmatch(r"[+-]?[0-9]+", users_input.strip()):
        value = int(users_input.strip())
    else:
        raise ValueError(
            "Validation Failed: affected_users must be a positive whole integer "
            "(not text or decimal)."
        )

    if value <= 0:
        raise ValueError("Validation Failed: affected_users cannot be 0 or negative.")
    return value


def validate_staff_name(staff_name) -> str:
    """Return the trimmed staff label, or raise ValueError if blank / not text."""
    if not isinstance(staff_name, str) or staff_name.strip() == "":
        raise ValueError("Assignment Failed: Staff member name cannot be blank.")
    return staff_name.strip()


def validate_note_author(author) -> str:
    """Return the trimmed author label, or raise ValueError if blank / not text."""
    if not isinstance(author, str) or author.strip() == "":
        raise ValueError("Note Failed: Author cannot be blank.")
    return author.strip()


def validate_note_message(message) -> str:
    """Return the trimmed message; it must be 5-300 characters AFTER trimming."""
    if not isinstance(message, str):
        raise ValueError("Note Failed: Message must be text.")
    cleaned = message.strip()
    if not (NOTE_MIN_LENGTH <= len(cleaned) <= NOTE_MAX_LENGTH):
        raise ValueError(
            f"Note Failed: Message must be {NOTE_MIN_LENGTH}-{NOTE_MAX_LENGTH} characters "
            f"after trimming (got {len(cleaned)})."
        )
    return cleaned


# ---------- priority engine ----------
def calculate_priority(urgency: str, affected_users: int) -> str:
    """Apply the priority rules in order; the first match wins."""
    # RULE 1: high urgency AND 10 or more affected users -> critical
    if urgency == "high" and affected_users >= 10:
        return "critical"
    # RULE 2: high urgency OR 10 or more affected users -> high
    if urgency == "high" or affected_users >= 10:
        return "high"
    # RULE 3: medium urgency OR 3 or more affected users -> medium
    if urgency == "medium" or affected_users >= 3:
        return "medium"
    # RULE 4: everything else -> low
    return "low"


# ---------- ordering ----------
def ticket_number(ticket_id) -> int:
    """Numeric part of an ID: 'T10' -> 10. Unparseable IDs count as 0.

    Sorting by this number (not by the text) keeps T2 before T10.
    """
    raw = str(ticket_id)
    return int(raw[1:]) if raw[1:].isdigit() else 0


def priority_sort_key(ticket):
    """Sort key: priority weight first, then earlier numeric ticket ID."""
    weight = PRIORITY_WEIGHTS.get(str(ticket.get("priority", "low")).lower(), 5)
    return (weight, ticket_number(ticket.get("id", "T0")))