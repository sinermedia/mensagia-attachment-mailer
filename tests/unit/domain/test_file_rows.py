import json

import pytest

from src.domain.entities.recipient import Recipient
from src.domain.file_rows import email_skip_reason, row_key, skip_duplicate_rows


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
