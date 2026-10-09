from datetime import date, time
import pytest
from src.domain.date_input import DateFormat, SendDateError, parse_date, parse_send_date, parse_time


class TestParseDate:
    """Tests for parse_date(), the tolerant reader of day/month/year dates typed by the user."""

    @pytest.mark.parametrize("text", ["08/10/2026", "8/10/2026", "08-10-2026", "08.10.2026", "8/10/26", " 8 / 10 / 2026 "])
    def test_accepts_the_supported_variants(self, text):
        """Accepts /, - and . separators, optional leading zeros, 2-digit years and surrounding spaces."""
        assert parse_date(text) == date(2026, 10, 8)

    def test_reads_a_two_digit_year_in_this_century(self):
        """A two-digit year is read as 20yy."""
        assert parse_date("1/2/27") == date(2027, 2, 1)

    @pytest.mark.parametrize("text", ["31/02/2026", "00/10/2026", "08/13/2026"])
    def test_rejects_dates_that_do_not_exist(self, text):
        """Rejects a day or month out of range, such as 31 February."""
        with pytest.raises(ValueError):
            parse_date(text)

    @pytest.mark.parametrize("text", ["", "08/10", "2026/10/08", "08/10/202", "8 10 2026", "a/b/c", "08/10-2026x"])
    def test_rejects_text_that_is_not_a_day_month_year_date(self, text):
        """Rejects empty text, missing parts, a leading year, 3-digit years and unknown separators."""
        with pytest.raises(ValueError):
            parse_date(text)


class TestParseTime:
    """Tests for parse_time(), the tolerant reader of hour and minute typed by the user."""

    @pytest.mark.parametrize("text, expected", [
        ("09:05", time(9, 5)),
        ("9:5", time(9, 5)),
        ("9.30", time(9, 30)),
        ("9h30", time(9, 30)),
        ("9H30", time(9, 30)),
        ("9", time(9, 0)),
        ("23:59", time(23, 59)),
        (" 0:00 ", time(0, 0)),
    ])
    def test_accepts_the_supported_variants(self, text, expected):
        """Accepts :, . and h separators, optional leading zeros and an hour on its own."""
        assert parse_time(text) == expected

    @pytest.mark.parametrize("text", ["24:00", "9:60", "", "905", "9:5:00", "nine", "9:"])
    def test_rejects_invalid_times(self, text):
        """Rejects out-of-range values, seconds, missing minutes after a separator and non-numeric text."""
        with pytest.raises(ValueError):
            parse_time(text)


class TestParseSendDate:
    """Tests for parse_send_date(), the reader of a contact's send date in a chosen format."""

    @pytest.mark.parametrize("fmt, text", [
        (DateFormat.DMY_SLASH, "15/10/2026"),
        (DateFormat.DMY_DASH, "15-10-2026"),
        (DateFormat.YMD_SLASH, "2026/10/15"),
        (DateFormat.YMD_DASH, "2026-10-15"),
    ])
    def test_reads_each_format(self, fmt, text):
        """Each supported format is read in its own order and separator."""
        assert parse_send_date(text, fmt) == date(2026, 10, 15)

    @pytest.mark.parametrize("fmt, text", [
        (DateFormat.DMY_SLASH, "3/4/2026"),
        (DateFormat.DMY_SLASH, "03/04/26"),
        (DateFormat.YMD_DASH, "26-4-3"),
        (DateFormat.YMD_DASH, " 2026-04-03 "),
    ])
    def test_tolerates_missing_zeros_short_years_and_spaces(self, fmt, text):
        """Leading zeros are optional, a 2-digit year is 20yy and surrounding spaces are ignored."""
        assert parse_send_date(text, fmt) == date(2026, 4, 3)

    @pytest.mark.parametrize("fmt, text", [
        (DateFormat.DMY_SLASH, "15-10-2026"),     # another separator
        (DateFormat.DMY_SLASH, "2026/10/15"),     # another order
        (DateFormat.YMD_DASH, "15-10-2026"),      # day first in a year-first format
        (DateFormat.DMY_SLASH, "31/02/2026"),     # a day that does not exist
        (DateFormat.DMY_SLASH, "mañana"),
        (DateFormat.DMY_SLASH, "15/10/2026 x"),
    ])
    def test_rejects_values_that_do_not_match_the_format(self, fmt, text):
        """A value in another order or separator, or that is not a real date, is invalid."""
        with pytest.raises(SendDateError) as info:
            parse_send_date(text, fmt)
        assert info.value.reason == "invalid_send_date"

    @pytest.mark.parametrize("fmt, text", [
        (DateFormat.DMY_SLASH, "15/10/2026 10:00"),
        (DateFormat.DMY_SLASH, "15/10/2026 00:00:00"),
        (DateFormat.YMD_DASH, "2026-10-15T09:30"),
        (DateFormat.YMD_DASH, "2026-10-15 9h30"),
    ])
    def test_rejects_values_with_a_time(self, fmt, text):
        """A date followed by a time is rejected with its own reason, whatever the time."""
        with pytest.raises(SendDateError) as info:
            parse_send_date(text, fmt)
        assert info.value.reason == "send_date_has_time"
