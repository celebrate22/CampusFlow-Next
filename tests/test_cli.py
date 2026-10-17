import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import main
from campusflow.storage import TicketStorage


class TestCli(unittest.TestCase):
    def run_main(self, typed):
        with tempfile.TemporaryDirectory() as folder:
            storage = TicketStorage(os.path.join(folder, "t.json"))
            out = io.StringIO()
            with mock.patch("main.TicketStorage", return_value=storage), \
                 mock.patch("builtins.input", side_effect=typed), \
                 contextlib.redirect_stdout(out):
                main.main()
            return out.getvalue()

    def test_invalid_menu_choice_is_rejected_and_menu_keeps_running(self):
        output = self.run_main(["99", "abc", "13"])
        self.assertEqual(output.count("[INVALID OPTION]"), 2)
        self.assertIn("Goodbye!", output)

    def test_full_flow_create_note_search_report(self):
        typed = [
            "1", "Campus WiFi down", "network", "high", "15",       # create T001
            "8", "t001", "Mentor A", "router reboot attempted",     # note
            "9", "T001",                                            # view notes
            "10", "wifi", "", "open", "", "n",                      # search
            "7", "13",
        ]
        output = self.run_main(typed)
        self.assertIn("Note N001 added", output)
        self.assertIn("[N001] Mentor A: router reboot attempted", output)
        self.assertIn("1 ticket(s) found.", output)
        self.assertIn("Resolution Rate: 0.0%", output)

    def test_rejected_action_shows_friendly_message_not_a_crash(self):
        output = self.run_main(["8", "T404", "A", "some message", "13"])
        self.assertIn("[REJECTED]", output)
        self.assertIn("does not exist", output)

    def test_invalid_search_filter_reprompts(self):
        with mock.patch("builtins.input", side_effect=["urgent", "", "network"]), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main.prompt_filter("Priority", "priority"), "")
            self.assertEqual(main.prompt_filter("Category", "category"), "Network")
        self.assertIn("[INVALID]", out.getvalue())