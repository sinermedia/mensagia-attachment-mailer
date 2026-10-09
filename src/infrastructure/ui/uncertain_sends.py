from datetime import datetime

from src.infrastructure.ui.i18n import t


# Slot format shown to the user: the same day-first layout and seconds
# precision they need to find the message in the Mensagia portal.
_SLOT_FORMAT = "%d/%m/%Y %H:%M:%S"


def format_slots(dates: list[datetime]) -> str:
    """Render send slots as a comma-separated, human-readable list.

    Args:
        dates: Send slots to render, in the order they must appear.

    Returns:
        The slots formatted as 'dd/mm/yyyy hh:mm:ss', joined with ', '.
    """
    return ", ".join(d.strftime(_SLOT_FORMAT) for d in dates)


def resume_uncertain_lines(uncertain: dict[str, list[datetime]], contacts: list) -> list[str]:
    """Build the lines listing a previous run's unresolved attempts.

    Shown when resuming a campaign, so the user knows which recipients
    may get a duplicate and which slots to check in the Mensagia portal.

    Args:
        uncertain: Mapping of recipient key to unresolved send slots, as
            returned by SendRegistry.get_uncertain_attempts().
        contacts: Contacts of the group, used to show each email address.

    Returns:
        One translated line per contact. Contacts no longer in the group
        are shown by key so the warning is never silently dropped.
    """
    emails = {str(c.id): c.email for c in contacts}
    return [
        t("uncertain_item", email=emails.get(key, f"#{key}"), slots=format_slots(sorted(dates)))
        for key, dates in uncertain.items()
    ]


def result_uncertain_lines(uncertain: list[dict]) -> list[str]:
    """Build the end-of-run messages about sends that may have been scheduled.

    Args:
        uncertain: SendResult.uncertain entries, each with 'contact',
            'start_dates' and 'sent' keys.

    Returns:
        One translated message per entry: a possible-duplicate warning when
        the contact also got a confirmed email, or an unconfirmed-send
        warning when it did not.
    """
    lines = []
    for item in uncertain:
        key = "possible_duplicate" if item["sent"] else "uncertain_unconfirmed"
        lines.append(t(key, email=item["contact"].email, slots=format_slots(item["start_dates"])))
    return lines
