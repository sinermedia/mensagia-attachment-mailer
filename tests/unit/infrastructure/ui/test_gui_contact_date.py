from datetime import date, datetime, time, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.domain.date_input import DateFormat
from src.domain.entities.agenda import Agenda
from src.domain.entities.contact import Contact
from src.domain.entities.extra_field import ExtraField
from src.domain.scheduling import StartMode
# Reuse the window fixture, the event-loop helper and the Tk availability skip
from tests.unit.infrastructure.ui.test_gui_group_selection import _wait_until, app, pytestmark  # noqa: F401
from tests.unit.infrastructure.ui.test_gui_file_source import write_csv


# Reference time used by every test: Thursday 8 October 2026, 10:07
NOW = datetime(2026, 10, 8, 10, 7, 0)


@pytest.fixture(autouse=True)
def fixed_now():
    """Freeze the GUI's notion of the current time."""
    with patch("src.infrastructure.ui.gui.gui_app._now", return_value=NOW):
        yield


def _type_time(window, hour: str, minute: str):
    """Select the contact date mode and type the time fields."""
    window._subject_entry.insert(0, "Subject")
    window._start_mode_var.set(StartMode.CONTACT_DATE.value)
    window._update_start_fields()
    for entry, text in zip(window._start_fields[3:], (hour, minute)):
        entry.delete(0, "end")
        entry.insert(0, text)


class TestGuiContactDateStart:
    """Covers the third start option on the subject step."""

    def test_only_the_time_fields_are_enabled(self, app):
        """With the contact date mode, the date is greyed out and the time can be typed."""
        app._start_mode_var.set(StartMode.CONTACT_DATE.value)
        app._update_start_fields()
        states = [str(e.cget("state")) for e in app._start_fields]
        assert states == ["disabled", "disabled", "disabled", "normal", "normal"]

    def test_next_reads_the_time_without_lead_checks(self, app):
        """A time already past today is accepted: the emails of today use the "now" schedule."""
        _type_time(app, "09", "00")
        with patch.object(app, "_load_templates") as load:
            app._subject_next()
        load.assert_called_once()
        assert (app._start_mode, app._start_at, app._start_time) == (StartMode.CONTACT_DATE, None, time(9, 0))

    def test_next_refuses_an_invalid_time(self, app):
        """An unreadable time is explained and the step does not move on."""
        _type_time(app, "25", "00")
        with patch.object(app, "_load_templates") as load:
            app._subject_next()
        load.assert_not_called()
        assert app._start_error.cget("text") == "The time is not valid."

    def test_remembers_the_chosen_time(self, app):
        """The time of a send by contact date is remembered with the mode."""
        app._start_mode, app._start_at, app._start_time = StartMode.CONTACT_DATE, None, time(9, 30)
        assert app._start_selections() == {"start_mode": "contact_date", "start_time": "09:30"}


def _agenda_ready(window):
    """Leave the wizard on the extra field step of an agenda send by contact date."""
    window._start_mode, window._start_time = StartMode.CONTACT_DATE, time(9, 0)
    window._source_kind = "agenda"
    window.extra_fields = [ExtraField(1, "Adjunto"), ExtraField(2, "Fecha"), ExtraField(3, "Otra")]
    window.selected_field = window.extra_fields[0]


class TestGuiDateFieldStep:
    """Covers choosing the custom field and format of the send day."""

    def test_field_next_goes_to_the_date_step(self, app):
        """In the contact date mode the step after the extra field is the date field step."""
        _agenda_ready(app)
        app._field_var.set("1")
        with patch.object(app, "_show_date_step") as show_date:
            app._field_next()
        show_date.assert_called_once()

    def test_attachment_field_cannot_be_the_date_field(self, app):
        """The field chosen for the attachment is listed but cannot be selected."""
        _agenda_ready(app)
        app._show_date_step()
        states = [str(w.cget("state")) for w in app._date_field_list.winfo_children()]
        assert states == ["disabled", "normal", "normal"]

    def test_remembered_field_and_format_are_preselected(self, app):
        """The date field and format used last time are selected again."""
        _agenda_ready(app)
        app._last_sel = {"date_field": "Fecha", "date_format": "yyyy-mm-dd"}
        app._show_date_step()
        assert app._date_field_var.get() == "2"
        assert app._date_format_var.get() == "yyyy-mm-dd"

    def test_next_requires_a_field(self, app):
        """The step does not move on without a date field."""
        _agenda_ready(app)
        app._show_date_step()
        with patch.object(app, "_show_frame") as show:
            app._date_next()
        show.assert_not_called()

    def test_next_keeps_the_field_and_format(self, app):
        """A chosen field and format move on to the certified step."""
        _agenda_ready(app)
        app._show_date_step()
        app._date_field_var.set("2")
        app._date_format_var.set(DateFormat.DMY_DASH.value)
        with patch.object(app, "_show_frame") as show:
            app._date_next()
        show.assert_called_once_with("certified")
        assert (app.selected_date_field.name, app._date_format) == ("Fecha", DateFormat.DMY_DASH)

    def test_certified_back_returns_to_the_date_step(self, app):
        """Going back from the certified step returns to the date field step."""
        _agenda_ready(app)
        with patch.object(app, "_show_frame") as show:
            app._certified_back()
        show.assert_called_once_with("date")


class TestGuiDateColumn:
    """Covers choosing the date column and format of a file."""

    def test_date_controls_only_appear_with_the_contact_date_mode(self, app, tmp_path):
        """The date column and format are shown only when sending by contact date."""
        app._load_file(write_csv(tmp_path / "f.csv", "Correo;Adjunto;Fecha\na@x.com;a.pdf;5/11/2026\n"))
        app._start_mode = StartMode.NOW
        app._show_columns_step()
        assert not app._date_column_box.winfo_manager()
        app._start_mode = StartMode.CONTACT_DATE
        app._show_columns_step()
        assert app._date_column_box.winfo_manager()

    def test_three_different_columns_are_required(self, app, tmp_path):
        """The date column cannot be one of the other two."""
        app._load_file(write_csv(tmp_path / "f.csv", "Correo;Adjunto;Fecha\na@x.com;a.pdf;5/11/2026\n"))
        app._start_mode = StartMode.CONTACT_DATE
        app._show_columns_step()
        app._email_column_var.set("Correo")
        app._attachment_column_var.set("Adjunto")
        app._date_column_var.set("Adjunto")
        with patch.object(app, "_show_frame") as show:
            app._columns_next()
        show.assert_not_called()
        app._date_column_var.set("Fecha")
        with patch.object(app, "_show_frame") as show:
            app._columns_next()
        show.assert_called_once_with("certified")
        assert (app._date_column, app._date_format) == ("Fecha", DateFormat.DMY_SLASH)


class TestGuiContactDateSummary:
    """Covers the summary of a send by contact date."""

    def test_summary_shows_the_reasons_the_days_and_the_repeated_rows(self, app, tmp_path):
        """The summary counts discarded rows by reason, lists each day and warns about repeated rows."""
        path = write_csv(tmp_path / "f.csv", "Correo;Adjunto;Fecha\n"
                         "a@x.com;https://x.com/a.pdf;9/10/2026\n"
                         "a@x.com;https://x.com/a.pdf;10/10/2026\n"
                         "b@x.com;https://x.com/b.pdf;7/10/2026\n"
                         "c@x.com;https://x.com/c.pdf;\n")
        app.selected_template = MagicMock(id=10, name="Template")
        app.selected_sender = MagicMock(id=20, name="Sender", email="from@example.com")
        app._subject_entry.insert(0, "Subject")
        app._source_kind = "file"
        app._start_mode, app._start_time = StartMode.CONTACT_DATE, time(9, 0)
        app._load_file(path)
        app._email_column, app._attachment_column = "Correo", "Adjunto"
        app._date_column, app._date_format = "Fecha", DateFormat.DMY_SLASH
        app._send_registry = MagicMock()
        app._send_registry.get_sent_keys.return_value = set()
        app._send_registry.get_uncertain_attempts.return_value = {}
        app._send_registry.get_last_start_dates_by_day.return_value = {}

        app._load_summary()
        _wait_until(app, lambda: app._summary_text.cget("text") != "")

        assert "Date column: Fecha (dd/mm/yyyy)" in app._summary_text.cget("text")
        assert "Start: on the date given for each contact, at 09:00" in app._summary_text.cget("text")
        assert app._summary_contacts_label.cget("text") == "Eligible rows: 2"
        assert app._summary_skipped_label.cget("text") == "Discarded rows: 2"
        details = app._summary_details.get("1.0", "end")
        assert "· no date: 1" in details and "· past date: 1" in details
        assert "09/10/2026   1 email(s)   09:00:00 – 09:00:00" in details
        assert "- a@x.com, https://x.com/a.pdf: row 2 (09/10/2026), row 3 (10/10/2026)" in details


class TestGuiContactDateSelections:
    """Covers the choices of the contact date mode remembered after a send."""

    def test_agenda_date_field_and_format_are_remembered(self, app):
        """An agenda send by contact date remembers the date field name and the format."""
        app.selected_template, app.selected_sender = MagicMock(id=10), MagicMock(id=20)
        app.selected_agenda, app.selected_field = Agenda(id=1, name="G", total_users=1), MagicMock(id=30)
        app._source_kind = "agenda"
        app._start_mode, app._start_time = StartMode.CONTACT_DATE, time(9, 0)
        app.selected_date_field, app._date_format = ExtraField(2, "Fecha"), DateFormat.YMD_DASH
        selections = app._selections()
        assert (selections["date_field"], selections["date_format"]) == ("Fecha", "yyyy-mm-dd")

    def test_file_date_column_and_format_are_remembered(self, app, tmp_path):
        """A file send by contact date remembers the date column name and the format."""
        app.selected_template, app.selected_sender = MagicMock(id=10), MagicMock(id=20)
        app._source_kind = "file"
        app._load_file(write_csv(tmp_path / "f.csv", "Correo;Adjunto;Fecha\na@x.com;a.pdf;5/11/2026\n"))
        app._email_column, app._attachment_column = "Correo", "Adjunto"
        app._start_mode, app._start_time = StartMode.CONTACT_DATE, time(9, 0)
        app._date_column, app._date_format = "Fecha", DateFormat.DMY_SLASH
        selections = app._selections()
        assert (selections["date_column"], selections["date_format"]) == ("Fecha", "dd/mm/yyyy")
