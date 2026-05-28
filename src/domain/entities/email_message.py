from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EmailMessage:
    from_email: str
    to_email: str
    subject: str
    template_id: int
    start_date: datetime
    attachments: list = field(default_factory=list)
    certified: int = 0
