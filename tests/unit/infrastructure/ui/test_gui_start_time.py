from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
from src.domain.entities.agenda import Agenda
from src.domain.scheduling import StartMode
# Reuse the window fixture, the event-loop helper and the Tk availability skip
from tests.unit.infrastructure.ui.test_gui_group_selection import _wait_until, app, pytestmark  # noqa: F401


# Reference time used by every test: Thursday 8 October 2026, 10:07
NOW = datetime(2026, 10, 8, 10, 7, 0)


@pytest.fixture(autouse=True)
def fixed_now():
    """Freeze the GUI's notion of the current time."""
    with patch("src.infrastructure.ui.gui.gui_app._now", return_value=NOW):
        yield


def _field_values(window) -> list:
    """Return the text of the five date and time fields, in order."""
    return [e.get() for e in window._start_fields]


def _fill(window, mode: str, day="", month="", year="", hour="", minute=""):
    """Select a start mode and type the given date and time parts.

    Args:
        window: The App instance to drive.
        mode: Start mode value to select ('now' or 'fixed').
        day, month, year, hour, minute: Text to type in each field.
    """
    window._subject_entry.insert(0, "Subject")
    window._start_mode_var.set("fixed")
    window._update_start_fields()
    for entry, text in zip(window._start_fields, (day, month, year, hour, minute)):
        entry.delete(0, "end")
        entry.insert(0, text)
    window._start_mode_var.set(mode)
    window._update_start_fields()


class TestGuiStartFields:
    """Covers the start mode selector and the date and time fields of the subject step."""

    def test_fields_are_disabled_when_starting_now(self, app):
        """Greys out the date and time fields when the "now" mode is selected."""
        app._start_mode_var.set("now")
        app._update_start_fields()

        assert all(str(e.cget("state")) == "disabled" for e in app._start_fields)

    def test_fields_are_enabled_for_a_fixed_start(self, app):
        """Lets the user edit the date and time fields in the fixed mode."""
        app._start_mode_var.set("fixed")
        app._update_start_fields()

        assert all(str(e.cget("state")) == "normal" for e in app._start_fields)

    def test_proposes_today_and_the_now_schedule(self, app):
        """Fills in today's date and the first slot of the "now" mode by default."""
        app._last_sel = {}
        app._restore_start_selection()

        assert app._start_mode_var.get() == "now"
        assert _field_values(app) == ["08", "10", "2026", "10", "20"]

    def test_restores_the_remembered_mode_and_time(self, app):
        """Selects the mode and proposes the time used in the last send, with today's date."""
        app._last_sel = {"start_mode": "fixed", "start_time": "09:30"}
        app._restore_start_selection()

        assert app._start_mode_var.get() == "fixed"
        assert _field_values(app) == ["08", "10", "2026", "09", "30"]

    def test_ignores_an_unknown_remembered_mode(self, app):
        """Falls back to the "now" mode when the remembered mode is not recognised."""
        app._last_sel = {"start_mode": "someday"}
        app._restore_start_selection()

        assert app._start_mode_var.get() == "now"

    def test_moves_to_the_next_field_once_one_is_complete(self, app):
        """Moves the cursor to the month once the two digits of the day are typed."""
        _fill(app, "fixed", day="15")
        with patch.object(app._start_fields[1], "focus_set") as focus:
            app._advance_start_field(0, MagicMock(char="5"))

        focus.assert_called_once()

    def test_stays_in_a_field_that_is_not_complete(self, app):
        """Keeps the cursor in the day while only one digit has been typed."""
        _fill(app, "fixed", day="1")
        with patch.object(app._start_fields[1], "focus_set") as focus:
            app._advance_start_field(0, MagicMock(char="1"))

        focus.assert_not_called()

    def test_does_not_move_on_keys_that_are_not_digits(self, app):
        """Keeps the cursor in place for keys such as Tab or the arrows."""
        _fill(app, "fixed", day="15")
        with patch.object(app._start_fields[1], "focus_set") as focus:
            app._advance_start_field(0, MagicMock(char=""))

        focus.assert_not_called()


class TestGuiStartValidation:
    """Covers the checks made on the start when leaving the subject step."""

    def test_rejects_a_date_that_does_not_exist(self, app):
        """Shows an error and stays on the step for a date such as 31/02."""
        _fill(app, "fixed", "31", "02", "2026", "09", "00")
        with patch.object(app, "_load_templates") as load:
            app._subject_next()

        load.assert_not_called()
        assert "date is not valid" in app._start_error.cget("text")

    def test_rejects_a_start_less_than_ten_minutes_ahead(self, app):
        """Shows an error and stays on the step for a start too close to now."""
        _fill(app, "fixed", "08", "10", "2026", "10", "15")
        with patch.object(app, "_load_templates") as load:
            app._subject_next()

        load.assert_not_called()
        assert "10 minutes" in app._start_error.cget("text")

    def test_rejects_a_start_beyond_six_weeks(self, app):
        """Shows an error with the latest start allowed for a start too far ahead."""
        _fill(app, "fixed", "20", "11", "2026", "09", "00")
        with patch.object(app, "_load_templates") as load:
            app._subject_next()

        load.assert_not_called()
        assert "19/11/2026 10:07" in app._start_error.cget("text")

    def test_accepts_a_valid_fixed_start(self, app):
        """Keeps the chosen start and moves on to the templates."""
        _fill(app, "fixed", "15", "10", "2026", "9", "0")
        with patch.object(app, "_load_templates") as load:
            app._subject_next()

        load.assert_called_once()
        assert (app._start_mode, app._start_at) == (StartMode.FIXED, datetime(2026, 10, 15, 9, 0))
        assert app._start_error.cget("text") == ""

    def test_ignores_the_fields_when_starting_now(self, app):
        """Moves on without reading the fields when the "now" mode is selected."""
        _fill(app, "now", "31", "02", "2026", "99", "99")
        with patch.object(app, "_load_templates") as load:
            app._subject_next()

        load.assert_called_once()
        assert (app._start_mode, app._start_at) == (StartMode.NOW, None)


class TestGuiStartSummaryAndMemory:
    """Covers how the chosen start reaches the summary and the remembered selections."""

    def test_the_summary_shows_a_fixed_start(self, app):
        """Lists the fixed start date and time and the note in the summary."""
        app.selected_agenda = Agenda(id=1, name="Group", total_users=1)
        app.selected_template = MagicMock(id=10, name="Template")
        app.selected_sender = MagicMock(id=20, name="Sender", email="from@example.com")
        app.selected_field = MagicMock(id=30)
        app.selected_field.name = "attachment"
        app._subject_entry.insert(0, "Subject")
        app._start_mode, app._start_at = StartMode.FIXED, datetime(2026, 10, 15, 9, 0)
        repo = MagicMock()
        repo.get_by_group.return_value = [MagicMock(email="a@example.com", extra_fields={"attachment": "a.pdf"})]
        with patch("src.infrastructure.ui.gui.gui_app.MensagiaContactRepository", return_value=repo):
            app._load_summary()
            _wait_until(app, lambda: app._summary_text.cget("text") != "")

        text = app._summary_text.cget("text")
        assert "Start: fixed date, 15/10/2026 at 09:00" in text
        assert "The final time is set when the send starts." in text

    def test_remembers_the_fixed_mode_and_time(self, app):
        """Saves the fixed mode and the chosen time with the other selections."""
        app._start_mode, app._start_at = StartMode.FIXED, datetime(2026, 10, 15, 9, 0)

        assert app._start_selections() == {"start_mode": "fixed", "start_time": "09:00"}

    def test_keeps_the_previous_time_when_starting_now(self, app):
        """Saves the "now" mode and keeps the time remembered from an earlier fixed start."""
        app._last_sel = {"start_time": "09:30"}
        app._start_mode, app._start_at = StartMode.NOW, None

        assert app._start_selections() == {"start_mode": "now", "start_time": "09:30"}
