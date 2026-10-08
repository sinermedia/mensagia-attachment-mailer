from dataclasses import dataclass


@dataclass(frozen=True)
class Campaign:
    """Identifies a bulk send, so an interrupted one can be recognised and resumed.

    A campaign is defined by the choices a user would make again when
    restarting an interrupted send: the target group, the template, the
    extra field holding the attachment and the subject. Two sends with the
    same values are the same campaign for the send registry. The class is
    immutable so it can be compared and passed around safely.

    Attributes:
        group_id: ID of the target agenda group.
        template_id: ID of the email template used.
        field_name: Name of the extra field holding the attachment URL.
        subject: Email subject line.
    """

    group_id: int
    template_id: int
    field_name: str
    subject: str
