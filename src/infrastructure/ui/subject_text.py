from src.domain.subject_fields import SubjectFieldError, SubjectTemplate, subject_placeholder
from src.infrastructure.ui.i18n import t


def subject_field_lines(names: list[str]) -> list[str]:
    """List the fields or columns that can be used in the subject, and how.

    Shown on the step that knows the available names, so the user can see
    how each one is written in the subject.

    Args:
        names: Custom field names of the account, or column names of the file.

    Returns:
        One 'name → #written_name#' line per name, leaving out the names
        that cannot be written between # signs.
    """
    return [f"{name} → {written}" for name in names if (written := subject_placeholder(name))]


def subject_error_message(error: SubjectFieldError, rows: bool) -> str:
    """Explain why the fields of the subject cannot be used.

    Args:
        error: The error raised when binding the subject.
        rows: True when the names are columns of a file, False for the
            custom fields of the agenda.

    Returns:
        One translated line for the unknown fields, if any, and one per
        ambiguous field.
    """
    lines = []
    if error.unknown:
        key = "subject_error_unknown_columns" if rows else "subject_error_unknown_fields"
        lines.append(t(key, names=", ".join(f"#{name}#" for name in error.unknown)))
    for name, matches in error.ambiguous.items():
        lines.append(t("subject_error_ambiguous", name=f"#{name}#", names=", ".join(matches)))
    return "\n".join(lines)


def subject_example_line(template: SubjectTemplate | None, pending: list) -> str | None:
    """Show, as an example, the final subject of the first recipient.

    Args:
        template: The bound subject, or None when it was never bound.
        pending: Recipients that will be sent, in send order.

    Returns:
        The translated example line, or None when every recipient gets the
        subject as written or nobody will be sent the email.
    """
    if template is None or not template.has_fields or not pending:
        return None
    return t("summary_subject_example", value=pending[0].subject)
