"""Read-only search and filtering. Pure functions: never modify the tickets passed in."""
import copy

from .tickets import (
    ALLOWED_CATEGORIES,
    ALLOWED_PRIORITIES,
    ALLOWED_STATUSES,
    priority_sort_key,
)

FILTER_OPTIONS = {
    "category": ALLOWED_CATEGORIES,
    "status": ALLOWED_STATUSES,
    "priority": ALLOWED_PRIORITIES,
}


def _fold(value):
    return str(value or "").strip().casefold()


def normalize_filter(field, text):
    """Return the canonical option for a filter, '' for 'no filter', or raise ValueError."""
    cleaned = _fold(text)
    if cleaned == "":
        return ""
    for option in FILTER_OPTIONS[field]:
        if option.casefold() == cleaned:
            return option
    raise ValueError(f"Invalid {field} filter. Choose one of {list(FILTER_OPTIONS[field])} or leave blank.")


def search_tickets(tickets, title_query="", category="", status="", priority=""):
    """Return copies of tickets matching the title substring AND every supplied filter.

    Empty text for a filter means 'do not filter by that field'.
    """
    wanted_title = _fold(title_query)
    wanted = {
        "category": _fold(category),
        "status": _fold(status),
        "priority": _fold(priority),
    }
    results = []
    for ticket in tickets:
        if wanted_title and wanted_title not in _fold(ticket.get("title")):
            continue
        if any(value and _fold(ticket.get(name)) != value for name, value in wanted.items()):
            continue
        results.append(copy.deepcopy(ticket))
    return results


def sort_by_priority_then_id(tickets):
    """Optional view: critical -> low, ties by earlier numeric ticket ID. Returns a new list."""
    return sorted(tickets, key=priority_sort_key)