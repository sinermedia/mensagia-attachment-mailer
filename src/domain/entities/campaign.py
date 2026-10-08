from dataclasses import dataclass

from src.domain.scheduling import StartMode


@dataclass(frozen=True)
class Campaign:
    """Identifies a bulk send, so an interrupted one can be recognised and resumed.

    A campaign is defined by the choices a user would make again when
    restarting an interrupted send: the target group, the template, the
    extra field holding the attachment, the subject and the start mode.
    Two sends with the same values are the same campaign for the send
    registry. The chosen start date is not part of it: changing it must
    not turn an interrupted send into a new one that emails everybody
    again. The class is immutable so it can be compared and passed around
    safely.

    Attributes:
        group_id: ID of the target agenda group.
        template_id: ID of the email template used.
        field_name: Name of the extra field holding the attachment URL.
        subject: Email subject line.
        start_mode: How the first email is scheduled. Defaults to
            StartMode.NOW.
    """

    group_id: int
    template_id: int
    field_name: str
    subject: str
    start_mode: StartMode = StartMode.NOW
