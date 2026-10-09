from datetime import date, datetime

import pytest

from src.domain.date_input import DateFormat
from src.domain.entities.recipient import Recipient
from src.domain.scheduling import DayPreview
from src.infrastructure.ui.i18n import set_language
from src.infrastructure.ui.send_summary import date_format_label, day_lines, repeated_lines, skipped_lines


@pytest.fixture(autouse=True)
def english():
    """Run every test with the English texts."""
    set_language("en")


def skipped(*reasons: str) -> list[Recipient]:
    """Build one skipped recipient per reason given."""
    return [Recipient(key=str(i), email="a@x.com", attachment="a.pdf", skip_reason=r) for i, r in enumerate(reasons)]


class TestSkippedLines:
    """Covers the summary lines counting the discarded recipients by reason."""

    def test_no_discarded_recipients(self):
        """Without discarded recipients only the zero total is shown."""
        assert skipped_lines([], rows=False) == ["Discarded contacts: 0"]

    def test_a_single_reason_needs_no_total(self):
        """With one reason, the reason and its count fit in one line."""
        assert skipped_lines(skipped("no_email", "no_email"), rows=False) == ["Discarded contacts (no email): 2"]

    def test_several_reasons_show_the_total_and_each_reason(self):
        """With several reasons, the total comes first and then each reason, most frequent first."""
        lines = skipped_lines(skipped("past_send_date", "duplicate_row", "past_send_date"), rows=True)
        assert lines == ["Discarded rows: 3", "  · past date: 2", "  · duplicate row: 1"]


class TestDayLines:
    """Covers the per-day table of a contact date send."""

    def test_one_line_per_day_after_a_title(self):
        """Each day shows its number of emails and its first and last time."""
        previews = [
            DayPreview(date(2026, 10, 15), 120, datetime(2026, 10, 15, 9, 0, 0), datetime(2026, 10, 15, 9, 23, 48)),
            DayPreview(date(2026, 10, 16), 1, datetime(2026, 10, 16, 9, 0, 0), datetime(2026, 10, 16, 9, 0, 0)),
        ]
        assert day_lines(previews) == [
            "Emails per day (approximate times):",
            "15/10/2026   120 email(s)   09:00:00 – 09:23:48",
            "16/10/2026   1 email(s)   09:00:00 – 09:00:00",
        ]

    def test_no_days_no_lines(self):
        """Without emails to send there is no table."""
        assert day_lines([]) == []


class TestRepeatedLines:
    """Covers the warning about rows sent on several dates."""

    def test_lists_each_pair_with_its_rows_and_dates(self):
        """Each repeated address and attachment lists its rows and their dates, after the warning."""
        group = [
            Recipient(key="k1", email="a@x.com", attachment="a.pdf", row=2, send_date=date(2026, 10, 15)),
            Recipient(key="k2", email="a@x.com", attachment="a.pdf", row=7, send_date=date(2026, 10, 16)),
        ]
        lines = repeated_lines([group])
        assert lines[0].startswith("These recipients will receive the same attachment on different dates.")
        assert lines[1] == "- a@x.com, a.pdf: row 2 (15/10/2026), row 7 (16/10/2026)"

    def test_nothing_repeated_no_lines(self):
        """Without repeated rows there is no warning."""
        assert repeated_lines([]) == []


class TestDateFormatLabel:
    """Covers the names of the date formats shown to the user."""

    def test_formats_use_the_letters_of_the_language(self):
        """The format is shown with the letters of the language."""
        set_language("es")
        assert date_format_label(DateFormat.YMD_DASH) == "aaaa-mm-dd"
