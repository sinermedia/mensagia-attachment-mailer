from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import customtkinter as ctk
import pytest

from src.application.use_cases.send_bulk_emails import SendResult
from src.domain.entities.agenda import Agenda
from src.infrastructure.ui.i18n import t
# Reuse the window fixture, the event-loop helper and the Tk availability skip
from tests.unit.infrastructure.ui.test_gui_group_selection import app, pytestmark  # noqa: F401


LOG_PATH = Path("C:/Users/someone/AppData/Roaming/mensagia-mailer/logs/simulation_2026-10-14_10-00-00.log")

# An error as long as the real ones, which carry the full attachment URL
LONG_ERROR = ("attachment not accessible: https://files.example.com/clients/2026/october/"
              "invoices/very-long-folder-name/invoice-000123-customer-with-a-long-name.pdf")


def _errors(count: int) -> list[dict]:
    """Build *count* per-recipient errors, each with a long message."""
    return [{"recipient": MagicMock(email=f"user{i}@example.com"), "error": LONG_ERROR} for i in range(count)]


def _uncertain() -> list[dict]:
    """Build one send that may have been scheduled without confirmation."""
    return [{"recipient": MagicMock(email="maybe@example.com"),
             "start_dates": [datetime(2026, 10, 14, 10, 0, 0)], "sent": False}]


@pytest.fixture
def sending(app):
    """Yield the window on the sending step, with the choices of an agenda send."""
    app.selected_template = MagicMock(id=10)
    app.selected_sender = MagicMock(id=20)
    app.selected_agenda = Agenda(id=1, name="G", total_users=1)
    app.selected_field = MagicMock(id=30)
    app._source_kind = "agenda"
    app._can_send = True
    app._show_frame("sending")
    return app


def _details(window) -> str:
    """Return the text of the scrollable details of the result."""
    return window._result_details.get("1.0", "end").strip()


def _buttons(window) -> list[str]:
    """Return the texts of the action buttons under the result."""
    return [w.cget("text") for w in window._sending_actions.winfo_children()]


class TestGuiSendResult:
    """Covers the result step: summary always visible, details scrollable, log path and buttons below."""

    def test_summary_shows_only_the_counts(self, sending):
        """The summary line holds the counts of the run and none of the error lines."""
        result = SendResult(sent=[{}, {}], errors=_errors(3))
        sending._finish_send(result, dry_run=True, log_path=LOG_PATH)

        assert sending._result_label.cget("text") == t("dry_run_complete", sent=2, skipped=0, errors=3)

    def test_errors_go_to_the_scrollable_details(self, sending):
        """Each error is listed in the scrollable details, one per line."""
        sending._finish_send(SendResult(errors=_errors(2)), dry_run=True, log_path=LOG_PATH)

        assert _details(sending).splitlines() == [
            t("send_error", email="user0@example.com", error=LONG_ERROR),
            t("send_error", email="user1@example.com", error=LONG_ERROR),
        ]
        assert sending._result_details.winfo_manager() == "pack"

    def test_unconfirmed_sends_come_before_the_errors(self, sending):
        """The warnings about unconfirmed sends are listed before the errors."""
        sending._finish_send(SendResult(errors=_errors(1), uncertain=_uncertain()), dry_run=False, log_path=LOG_PATH)

        details = _details(sending)
        warning = t("uncertain_unconfirmed", email="maybe@example.com", slots="14/10/2026 10:00:00")
        assert details.startswith(warning)
        assert details.index(warning) < details.index("user0@example.com")

    def test_details_are_hidden_without_errors_or_warnings(self, sending):
        """A clean run shows no details box at all."""
        sending._finish_send(SendResult(sent=[{}]), dry_run=False, log_path=LOG_PATH)

        assert sending._result_details.winfo_manager() == ""

    def test_log_path_has_its_own_line(self, sending):
        """The log path is shown apart from the summary, under the details."""
        sending._finish_send(SendResult(errors=_errors(1)), dry_run=True, log_path=LOG_PATH)

        assert sending._result_log_label.cget("text") == t("log_saved", path=str(LOG_PATH))
        assert str(LOG_PATH) not in sending._result_label.cget("text")

    def test_many_errors_keep_everything_inside_the_window(self, sending):
        """With many long errors the step still fits in the window, so the log path and the buttons stay reachable."""
        from src.infrastructure.ui.gui.gui_app import PAD, WINDOW_H
        sending._finish_send(SendResult(sent=[{}], errors=_errors(40), uncertain=_uncertain()),
                             dry_run=True, log_path=LOG_PATH)
        sending.update_idletasks()

        # customtkinter scales both the window and the widgets to the screen's
        # DPI, so the required height is compared in the same scaled pixels
        scaling = ctk.ScalingTracker.get_window_scaling(sending)
        assert sending._frames["sending"].winfo_reqheight() <= (WINDOW_H - 2 * PAD) * scaling
        assert _buttons(sending) == [t("btn_send"), t("btn_back_to_summary")]

    def test_a_new_run_clears_the_previous_result(self, sending):
        """Starting another run empties the details and the log path of the previous one."""
        sending._finish_send(SendResult(errors=_errors(2)), dry_run=True, log_path=LOG_PATH)
        sending._clear_result()

        assert _details(sending) == ""
        assert sending._result_details.winfo_manager() == ""
        assert sending._result_log_label.cget("text") == ""

    def test_a_failed_send_hides_the_details_and_the_log(self, sending):
        """A send that fails as a whole shows only its error and a way back."""
        sending._finish_send(SendResult(errors=_errors(2)), dry_run=True, log_path=LOG_PATH)
        sending._fail_send("API error")

        assert sending._result_label.cget("text") == "API error"
        assert sending._result_details.winfo_manager() == ""
        assert sending._result_log_label.cget("text") == ""
        assert _buttons(sending) == [t("btn_back_to_summary")]
