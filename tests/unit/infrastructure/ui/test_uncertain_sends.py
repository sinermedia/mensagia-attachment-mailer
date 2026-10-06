from datetime import datetime

import pytest

from src.domain.entities.contact import Contact
from src.infrastructure.ui.i18n import get_language, set_language, t
from src.infrastructure.ui.uncertain_sends import (
    format_slots,
    resume_uncertain_lines,
    result_uncertain_lines,
)


SLOT_A = datetime(2024, 1, 15, 14, 40, 12)
SLOT_B = datetime(2024, 1, 15, 14, 52, 0)


def make_contact(contact_id, email):
    """Build a Contact for formatting tests."""
    return Contact(id=contact_id, name=f"Contact {contact_id}", email=email, extra_fields={})


@pytest.fixture(autouse=True)
def catalan():
    """Run every test in Catalan and restore the previous language afterwards."""
    previous = get_language()
    set_language("ca")
    yield
    set_language(previous)


class TestFormatSlots:
    """Tests for the human-readable rendering of send slots."""

    def test_single_slot_uses_day_month_year_and_seconds(self):
        """A slot is shown as dd/mm/yyyy hh:mm:ss, matching what the portal displays."""
        assert format_slots([SLOT_A]) == "15/01/2024 14:40:12"

    def test_several_slots_are_comma_separated(self):
        """Several slots are joined with commas in the given order."""
        assert format_slots([SLOT_A, SLOT_B]) == "15/01/2024 14:40:12, 15/01/2024 14:52:00"


class TestResumeUncertainLines:
    """Tests for the lines listing a previous run's unresolved attempts when resuming."""

    def test_one_line_per_contact_with_email_and_slots(self):
        """Each uncertain contact gets one line with its email and every slot to check."""
        contacts = [make_contact(1, "a@test.com"), make_contact(2, "b@test.com")]
        lines = resume_uncertain_lines({2: [SLOT_A, SLOT_B]}, contacts)
        assert lines == [t("uncertain_item", email="b@test.com", slots=format_slots([SLOT_A, SLOT_B]))]

    def test_unknown_contact_is_shown_by_id(self):
        """A contact no longer in the group is identified by its ID so the warning is not lost."""
        lines = resume_uncertain_lines({99: [SLOT_A]}, [])
        assert lines == [t("uncertain_item", email="#99", slots=format_slots([SLOT_A]))]


class TestResultUncertainLines:
    """Tests for the end-of-run messages about uncertain sends."""

    def test_sent_contact_is_reported_as_possible_duplicate(self):
        """A contact finally sent gets the possible-duplicate message with the extra slots."""
        item = {"contact": make_contact(1, "a@test.com"), "start_dates": [SLOT_A], "sent": True}
        assert result_uncertain_lines([item]) == [
            t("possible_duplicate", email="a@test.com", slots=format_slots([SLOT_A]))
        ]

    def test_unsent_contact_is_reported_as_unconfirmed(self):
        """A contact never confirmed gets the unconfirmed message with every slot."""
        item = {"contact": make_contact(1, "a@test.com"), "start_dates": [SLOT_A, SLOT_B], "sent": False}
        assert result_uncertain_lines([item]) == [
            t("uncertain_unconfirmed", email="a@test.com", slots=format_slots([SLOT_A, SLOT_B]))
        ]

    def test_messages_are_translated(self):
        """The messages come from the locale files, not from the raw keys."""
        item = {"contact": make_contact(1, "a@test.com"), "start_dates": [SLOT_A], "sent": True}
        assert "possible_duplicate" not in result_uncertain_lines([item])[0]
