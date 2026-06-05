from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EmailMessage:
    """Represents a single email to be sent via the Mensagia API.

    Encapsulates all the data required to schedule and deliver one email
    through Mensagia's transactional sending endpoint. The message uses a
    pre-designed template stored in the Mensagia platform rather than raw
    HTML, which is why the body is referenced by template ID rather than
    inline content.

    Attributes:
        from_email: Sender email address. Must be one of the verified sender
            addresses registered in the Mensagia account.
        to_email: Recipient email address.
        subject: Subject line of the email.
        template_id: Numeric ID of the Mensagia email template that defines
            the HTML body of the message.
        start_date: Scheduled send datetime. The Mensagia API queues the
            message and delivers it at this moment.
        attachments: List of publicly accessible URLs pointing to files that
            will be attached to the email. Defaults to an empty list.
        certified: Whether to send as a certified (tracked/registered) email.
            Use 1 for certified delivery, 0 for standard. Defaults to 0.
    """

    from_email: str
    to_email: str
    subject: str
    template_id: int
    start_date: datetime
    attachments: list = field(default_factory=list)
    certified: int = 0
