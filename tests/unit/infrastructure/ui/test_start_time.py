from datetime import datetime, time
import pytest
from src.domain.scheduling import StartMode
from src.infrastructure.ui.i18n import set_language
from src.infrastructure.ui.start_time import (
    StartInputError, default_start_fields, read_contact_start_time, read_fixed_start, summary_start_lines,
)


# Reference time used by every test: Thursday 8 October 2026, 10:07
NOW = datetime(2026, 10, 8, 10, 7, 0)


@pytest.fixture(autouse=True)
def _english_ui():
    """Pin the UI language so assertions on messages are deterministic."""
    set_language("en")


class TestReadFixedStart:
    """Covers turning the date and time typed by the user into a validated fixed start."""

    def test_combines_a_valid_date_and_time(self):
        """Returns the date and time typed, with zero seconds."""
        assert read_fixed_start("15/10/2026", "9:00", NOW) == datetime(2026, 10, 15, 9, 0, 0)

    def test_reports_an_invalid_date(self):
        """Explains that the date is not valid, for a date that does not exist."""
        with pytest.raises(StartInputError, match="date is not valid"):
            read_fixed_start("31/02/2026", "09:00", NOW)

    def test_reports_an_invalid_time(self):
        """Explains that the time is not valid."""
        with pytest.raises(StartInputError, match="time is not valid"):
            read_fixed_start("15/10/2026", "25:00", NOW)

    def test_reports_a_start_too_soon(self):
        """Explains the 10-minute minimum lead when the start is too close."""
        with pytest.raises(StartInputError, match="at least 10 minutes from now"):
            read_fixed_start("08/10/2026", "10:15", NOW)

    def test_reports_a_start_too_far_with_the_limit(self):
        """States the latest date and time allowed when the start is too far ahead."""
        with pytest.raises(StartInputError, match="19/11/2026 10:07"):
            read_fixed_start("20/11/2026", "09:00", NOW)


class TestDefaultStartFields:
    """Covers the date and time proposed when the user has not typed any."""

    def test_proposes_today_and_the_now_schedule(self):
        """Proposes today's date and the first slot of the "now" mode."""
        assert default_start_fields(NOW, None) == ("08/10/2026", "10:20")

    def test_prefers_the_remembered_time(self):
        """Proposes the time used last, still with today's date."""
        assert default_start_fields(NOW, "09:30") == ("08/10/2026", "09:30")

    def test_ignores_an_unreadable_remembered_time(self):
        """Falls back to the "now" schedule when the remembered time cannot be read."""
        assert default_start_fields(NOW, "later") == ("08/10/2026", "10:20")

    def test_uses_the_next_day_when_the_now_schedule_crosses_midnight(self):
        """Proposes tomorrow when the "now" schedule falls after midnight."""
        assert default_start_fields(datetime(2026, 10, 8, 23, 55), None) == ("09/10/2026", "00:10")


class TestSummaryStartLines:
    """Covers how the summary describes the chosen start."""

    def test_describes_the_now_mode(self):
        """Describes the "now" mode and notes the time is set when the send starts."""
        assert summary_start_lines(StartMode.NOW, None) == [
            "Start: now (in 10 to 20 minutes)",
            "The final time is set when the send starts.",
        ]

    def test_describes_a_fixed_start(self):
        """Shows the chosen date and time of a fixed start."""
        lines = summary_start_lines(StartMode.FIXED, datetime(2026, 10, 15, 9, 0))
        assert lines[0] == "Start: fixed date, 15/10/2026 at 09:00"

    def test_describes_a_contact_date_start(self):
        """Shows the chosen time of a send on each contact's date."""
        lines = summary_start_lines(StartMode.CONTACT_DATE, None, time(9, 0))
        assert lines[0] == "Start: on the date given for each contact, at 09:00"


class TestReadContactStartTime:
    """Covers reading the time of a send on each contact's date."""

    def test_reads_a_time(self):
        """A valid time is read with the tolerant rules."""
        assert read_contact_start_time("9h30") == time(9, 30)

    def test_reports_an_invalid_time(self):
        """An unreadable time is reported with the translated message."""
        with pytest.raises(StartInputError, match="The time is not valid."):
            read_contact_start_time("25:00")
