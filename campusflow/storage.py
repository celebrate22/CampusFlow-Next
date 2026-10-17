# campusflow/storage.py
"""JSON persistence and unique sequential ticket IDs (T001, T002, ...).

File format: one JSON object mapping ticket ID -> ticket record, e.g.
    {"T001": {"id": "T001", ..., "assigned_to": null, "notes": []}}
Files written by the first CampusFlow version (no "notes" key) still load; they get
notes = [] in memory and are upgraded the next time the data is saved.
"""
import json
import os
import tempfile

from .validation import validate_collection

DEFAULT_FILENAME = os.path.join("data", "tickets.json")


def _reject_duplicate_keys(pairs):
    """json.load silently keeps the LAST duplicate key; refuse instead."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key '{key}' in JSON object")
        result[key] = value
    return result


class TicketStorage:
    def __init__(self, filename=DEFAULT_FILENAME):
        self.filename = filename
        self._current_id_counter = 0

    def find_highest_existing_id(self, loaded_data):
        """Return the highest numeric part of IDs like 'T004' (0 if none)."""
        highest = 0
        for ticket_id in loaded_data.keys():
            if (
                isinstance(ticket_id, str)
                and ticket_id.startswith("T")
                and ticket_id[1:].isdigit()
            ):
                highest = max(highest, int(ticket_id[1:]))
        return highest

    def generate_next_sequential_id(self):
        self._current_id_counter += 1
        return f"T{self._current_id_counter:03d}"

    def release_id(self, ticket_id):
        """Give back the most recently generated ID (used when a save fails)."""
        if ticket_id == f"T{self._current_id_counter:03d}" and self._current_id_counter > 0:
            self._current_id_counter -= 1

    def load_tickets_from_json(self):
        """Parse and fully validate the file, then return the tickets.

        A missing file starts fresh. Anything malformed or inconsistent raises
        ValueError, and in that case NOTHING (including the ID counter) is changed.
        """
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                raw = json.load(f, object_pairs_hook=_reject_duplicate_keys)
        except FileNotFoundError:
            self._current_id_counter = 0
            return {}
        except (ValueError, UnicodeDecodeError) as e:  # JSONDecodeError is a ValueError
            raise ValueError(
                f"Data Persistence Error: The file '{self.filename}' is corrupted, "
                f"malformed, or has duplicate keys.\n"
                f"Details: {e}\n"
                f"Please repair the file manually or move it to start fresh."
            ) from e

        try:
            data = validate_collection(raw)
        except ValueError as e:
            raise ValueError(
                f"Data Persistence Error: The file '{self.filename}' failed validation.\n"
                f"Details: {e}\n"
                f"The load was rejected and current data was left unchanged."
            ) from e

        self._current_id_counter = self.find_highest_existing_id(data)
        return data

    def save_tickets_to_json(self, all_tickets):
        """Write atomically: write a temp file, then replace the real file.

        A crash mid-write can therefore never leave a half-written tickets file.
        """
        directory = os.path.dirname(self.filename)
        tmp_path = None
        try:
            if directory:
                os.makedirs(directory, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=directory or ".", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(all_tickets, f, indent=4)
            os.replace(tmp_path, self.filename)
        except (OSError, TypeError, ValueError) as e:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise OSError(
                f"Failed to write ticket data to storage file '{self.filename}': {e}"
            ) from e