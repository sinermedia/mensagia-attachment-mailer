from datetime import datetime, time
from unittest.mock import patch
import pytest
from src.domain.scheduling import StartMode
from src.infrastructure.ui.console import console_app
from src.infrastructure.ui.i18n import set_language


# Reference time used by every test: Thursday 8 October 2026, 10:07
NOW = datetime(2026, 10, 8, 10, 7, 0)


@pytest.fixture(autouse=True)
def _english_ui():
    """Pin the UI language so assertions on printed text are deterministic."""
    set_language("en")


def _choose(*answers):
    """Run the console start selection, answering its prompts in order.

    Args:
        answers: Text typed at each prompt.

    Returns:
        The (start mode, start date, start time) triple it returns.
    """
    with patch("builtins.input", side_effect=list(answers)):
        return console_app._choose_start(NOW)


class TestConsoleStartTime:
    """Covers the console questions about when the first email goes out."""

    def test_starts_now(self):
        """Returns the "now" mode without asking for a date when option 1 is chosen."""
        assert _choose("1") == (StartMode.NOW, None, None)

    def test_reads_a_fixed_start(self):
        """Returns the fixed mode with the date and time typed."""
        assert _choose("2", "15/10/2026", "9:00") == (StartMode.FIXED, datetime(2026, 10, 15, 9, 0), None)

    def test_enter_accepts_the_proposed_date_and_time(self):
        """Accepts today's date and the "now" schedule time when Enter is pressed."""
        assert _choose("2", "", "") == (StartMode.FIXED, datetime(2026, 10, 8, 10, 20), None)

    def test_shows_the_proposed_values_in_brackets(self):
        """Shows the proposed date and time between brackets in the prompts."""
        with patch("builtins.input", side_effect=["2", "", ""]) as fake_input:
            console_app._choose_start(NOW)

        prompts = [c.args[0] for c in fake_input.call_args_list]
        assert "[08/10/2026]" in prompts[1]
        assert "[10:20]" in prompts[2]

    def test_asks_again_for_an_invalid_date(self, capsys):
        """Explains the error and asks for the date again until it is valid."""
        assert _choose("2", "31/02/2026", "15/10/2026", "9") == (StartMode.FIXED, datetime(2026, 10, 15, 9, 0), None)
        assert "The date is not valid." in capsys.readouterr().out

    def test_asks_again_for_an_invalid_time(self, capsys):
        """Explains the error and asks for the time again until it is valid."""
        assert _choose("2", "15/10/2026", "25:00", "9h30") == (StartMode.FIXED, datetime(2026, 10, 15, 9, 30), None)
        assert "The time is not valid." in capsys.readouterr().out

    def test_asks_again_for_a_start_too_soon(self, capsys):
        """Explains the 10-minute minimum and asks for the date and time again."""
        result = _choose("2", "08/10/2026", "10:15", "15/10/2026", "9:00")

        assert result == (StartMode.FIXED, datetime(2026, 10, 15, 9, 0), None)
        assert "at least 10 minutes from now" in capsys.readouterr().out

    def test_proposes_the_rejected_values_when_asking_again(self):
        """Proposes the date and time just typed when asking again after a start too far ahead."""
        with patch("builtins.input", side_effect=["2", "20/11/2026", "9:00", "19/11/2026", ""]) as fake_input:
            result = console_app._choose_start(NOW)

        assert result == (StartMode.FIXED, datetime(2026, 11, 19, 9, 0), None)
        assert "[9:00]" in fake_input.call_args_list[4].args[0]

    def test_reads_a_contact_date_start(self):
        """Option 3 asks only for the time, since each contact gives its own day."""
        assert _choose("3", "9:00") == (StartMode.CONTACT_DATE, None, time(9, 0))

    def test_contact_date_proposes_the_now_schedule_time(self):
        """Enter accepts the time of the "now" schedule, proposed between brackets."""
        assert _choose("3", "") == (StartMode.CONTACT_DATE, None, time(10, 20))

    def test_contact_date_asks_again_for_an_invalid_time(self, capsys):
        """An unreadable time is explained and asked for again."""
        assert _choose("3", "25:00", "9") == (StartMode.CONTACT_DATE, None, time(9, 0))
        assert "The time is not valid." in capsys.readouterr().out
