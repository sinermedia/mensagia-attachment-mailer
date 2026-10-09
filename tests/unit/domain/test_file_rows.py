import json
from datetime import date

import pytest

from src.domain.entities.recipient import Recipient
from src.domain.file_rows import email_skip_reason, row_key, rows_on_several_dates, skip_duplicate_rows


class TestEmailSkipReason:
    """Covers the validation of the email address read from a file row."""

    @pytest.mark.parametrize("email", [
        "a@x.com",
        "Ana.Garcia+facturas@sub.example.es",
        "info_2024%x-y@mi-empresa.com",
    ])
    def test_valid_addresses_are_accepted(self, email):
        """An address with one @, allowed characters and a dotted domain has no skip reason."""
        assert email_skip_reason(email) is None

    def test_empty_address_is_no_email(self):
        """An empty cell is reported as a missing email."""
        assert email_skip_reason("") == "no_email"

    @pytest.mark.parametrize("email", [
        "ana",                       # no @
        "ana@@x.com",                # two @
        "ana@x.com;luis@x.com",      # two addresses
        "ana@x.com, luis@x.com",     # two addresses with a comma
        "ana@localhost",             # domain without a dot
        "ana garcia@x.com",          # space
        "ana@x_y.com",               # underscore in the domain
        "@x.com",                    # nothing before the @
        "ana@",                      # nothing after the @
        "ana@.com",                  # empty domain label
        "ana@x.com.",                # trailing dot
        "anà@x.com",                 # non-ASCII letter
    ])
    def test_invalid_addresses_are_rejected(self, email):
        """An address that breaks any rule is reported as invalid, with no more detail."""
        assert email_skip_reason(email) == "invalid_email"


class TestRowKey:
    """Covers the key that identifies a file row in the send registry."""

    def test_key_holds_date_email_and_attachment(self):
        """The key encodes the date, the email and the attachment value."""
        assert json.loads(row_key("ana@x.com", "a.pdf")) == ["", "ana@x.com", "a.pdf"]

    def test_email_case_does_not_change_the_key(self):
        """The email is compared without case, as addresses are case-insensitive in practice."""
        assert row_key("Ana@X.com", "a.pdf") == row_key("ana@x.com", "a.pdf")

    def test_attachment_case_changes_the_key(self):
        """The attachment is compared exactly, since URLs and file names can be case-sensitive."""
        assert row_key("ana@x.com", "A.pdf") != row_key("ana@x.com", "a.pdf")

    def test_separators_inside_values_cannot_collide(self):
        """Values containing separators never produce the key of different values."""
        assert row_key("a@x.com", "b|c.pdf") != row_key("a@x.com|b", "c.pdf")


def make_row(row: int, email: str, attachment: str, skip_reason: str | None = None) -> Recipient:
    """Build a file-row recipient keyed like the file source does."""
    return Recipient(key=row_key(email, attachment), email=email, attachment=attachment,
                     row=row, skip_reason=skip_reason)


class TestSkipDuplicateRows:
    """Covers discarding rows that repeat the key of an earlier sendable row."""

    def test_later_row_with_the_same_key_is_skipped(self):
        """The second row with the same email and attachment is skipped as duplicate_row."""
        rows = [make_row(2, "a@x.com", "a.pdf"), make_row(3, "A@x.com", "a.pdf")]
        assert [r.skip_reason for r in skip_duplicate_rows(rows)] == [None, "duplicate_row"]

    def test_same_address_with_another_attachment_is_kept(self):
        """Several rows for the same address with different attachments are all sent."""
        rows = [make_row(2, "a@x.com", "a.pdf"), make_row(3, "a@x.com", "b.pdf")]
        assert [r.skip_reason for r in skip_duplicate_rows(rows)] == [None, None]

    def test_rows_already_skipped_keep_their_reason(self):
        """A row skipped for another reason keeps it and does not hide a later valid row."""
        rows = [make_row(2, "a@x.com", "", "no_attachment"), make_row(3, "a@x.com", "", "no_attachment")]
        assert [r.skip_reason for r in skip_duplicate_rows(rows)] == ["no_attachment", "no_attachment"]

    def test_order_and_rows_are_kept(self):
        """Rows come back in the same order, with their row numbers."""
        rows = [make_row(2, "a@x.com", "a.pdf"), make_row(5, "b@x.com", "b.pdf"), make_row(9, "a@x.com", "a.pdf")]
        assert [r.row for r in skip_duplicate_rows(rows)] == [2, 5, 9]


def make_dated_row(row: int, email: str, attachment: str, day: date | None,
                   skip_reason: str | None = None) -> Recipient:
    """Build a dated file-row recipient keyed like the file source does."""
    return Recipient(key=row_key(email, attachment, day.isoformat() if day else ""), email=email,
                     attachment=attachment, row=row, send_date=day, skip_reason=skip_reason)


class TestRowsOnSeveralDates:
    """Covers finding the same address and attachment sent on different days."""

    def test_groups_the_rows_of_each_repeated_pair(self):
        """Rows with the same address (any case) and attachment on different days are grouped, in row order."""
        rows = [
            make_dated_row(2, "a@x.com", "a.pdf", date(2026, 11, 5)),
            make_dated_row(3, "b@x.com", "b.pdf", date(2026, 11, 5)),
            make_dated_row(4, "A@x.com", "a.pdf", date(2026, 11, 6)),
        ]
        assert [[r.row for r in group] for group in rows_on_several_dates(rows)] == [[2, 4]]

    def test_rows_that_are_not_sent_are_ignored(self):
        """Skipped rows, such as duplicates or past days, do not count."""
        rows = [
            make_dated_row(2, "a@x.com", "a.pdf", date(2026, 11, 5)),
            make_dated_row(3, "a@x.com", "a.pdf", date(2026, 11, 6), "past_send_date"),
        ]
        assert rows_on_several_dates(rows) == []

    def test_rows_without_dates_are_ignored(self):
        """Outside the contact date mode nothing is reported."""
        rows = [make_dated_row(2, "a@x.com", "a.pdf", None), make_dated_row(3, "a@x.com", "b.pdf", None)]
        assert rows_on_several_dates(rows) == []
