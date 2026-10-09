from collections import Counter

from src.domain.date_input import DateFormat
from src.infrastructure.ui.i18n import t
from src.infrastructure.ui.start_time import DATE_FORMAT


# Format of the times in the per-day table: seconds matter, since emails of
# the same day are 12 seconds apart
_TIME_WITH_SECONDS = "%H:%M:%S"


def date_format_label(fmt: DateFormat) -> str:
    """Name a date format the way the user reads it.

    Args:
        fmt: The format to name.

    Returns:
        The format written with the letters of the active language, such
        as 'dd/mm/aaaa' in Spanish.
    """
    return t(f"date_format_{fmt.value}")


def skipped_lines(skipped: list, rows: bool) -> list[str]:
    """Count the discarded recipients of the summary, by reason.

    With a single reason the count fits in one line; with several, the
    total comes first and then each reason, the most frequent first. A
    reason about one field (an empty subject field) counts apart for each
    field, so the user knows which one to fill in.

    Args:
        skipped: Recipients left out, each with its skip_reason.
        rows: True when they are rows of a file, False for contacts.

    Returns:
        The translated lines to show.
    """
    counts = Counter((r.skip_reason, r.skip_detail) for r in skipped).most_common()

    def reason_text(reason: str, detail: str | None) -> str:
        """Translate a skip reason, naming its field when it has one."""
        return t(f"skip_reason_{reason}", field=detail or "")

    if len(counts) == 1:
        (reason, detail), count = counts[0]
        key = "summary_skipped_rows_one" if rows else "summary_skipped_one"
        return [t(key, reason=reason_text(reason, detail), count=count)]
    lines = [t("summary_skipped_rows" if rows else "summary_skipped", count=len(skipped))]
    lines += [t("summary_skipped_item", reason=reason_text(reason, detail), count=count)
              for (reason, detail), count in counts]
    return lines


def day_lines(previews: list) -> list[str]:
    """Build the per-day table of a send by contact date.

    Args:
        previews: DayPreview objects, in date order.

    Returns:
        A title followed by one line per day with its number of emails and
        the approximate time of the first and the last; empty without days.
    """
    if not previews:
        return []
    return [t("summary_days_title")] + [
        t("summary_day_line", date=p.day.strftime(DATE_FORMAT), count=p.count,
          first=p.first.strftime(_TIME_WITH_SECONDS), last=p.last.strftime(_TIME_WITH_SECONDS))
        for p in previews
    ]


def repeated_lines(groups: list) -> list[str]:
    """Build the warning about the same address and attachment on several dates.

    Args:
        groups: Lists of file rows sharing address and attachment, as
            returned by rows_on_several_dates().

    Returns:
        The warning followed by one line per group with its rows and dates;
        empty when there are no groups.
    """
    if not groups:
        return []
    lines = [t("summary_repeated_dates")]
    for group in groups:
        rows = ", ".join(t("summary_repeated_row", row=r.row, date=r.send_date.strftime(DATE_FORMAT)) for r in group)
        lines.append(t("summary_repeated_item", email=group[0].email, attachment=group[0].attachment, rows=rows))
    return lines
