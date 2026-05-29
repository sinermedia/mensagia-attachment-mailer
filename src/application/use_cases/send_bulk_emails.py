from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.email_message import EmailMessage
from src.domain.entities.extra_field import ExtraField
from src.domain.ports.contact_repository import ContactRepository
from src.domain.ports.email_sender import EmailSender
from src.domain.scheduling import calculate_start_dates
from src.domain.attachment_url import resolve_attachment_url


@dataclass
class SendResult:
    sent: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    errors: list = field(default_factory=list)


class SendBulkEmailsUseCase:
    def __init__(self, contact_repository: ContactRepository, email_sender: EmailSender):
        self.contact_repository = contact_repository
        self.email_sender = email_sender

    def execute(
        self,
        from_email: str,
        group_id: int,
        subject: str,
        template_id: int,
        extra_field: ExtraField,
        certified: int,
        now: datetime = None,
        attachment_base_url: str | None = None,
        attachment_checker=None,
        dry_run: bool = False,
    ) -> SendResult:
        contacts = self.contact_repository.get_by_group(group_id, in_mail_blacklist=False)

        eligible = [
            c for c in contacts
            if c.email and c.extra_fields.get(extra_field.name)
        ]
        skipped = [c for c in contacts if c not in eligible]

        start_dates = calculate_start_dates(len(eligible), now)
        result = SendResult(skipped=skipped)

        for contact, start_date in zip(eligible, start_dates):
            try:
                attachment_url = resolve_attachment_url(
                    contact.extra_fields[extra_field.name], attachment_base_url
                )
                if attachment_checker and not attachment_checker.is_accessible(attachment_url):
                    raise ValueError(f"attachment not accessible: {attachment_url}")
                message = EmailMessage(
                    from_email=from_email,
                    to_email=contact.email,
                    subject=subject,
                    template_id=template_id,
                    start_date=start_date,
                    attachments=[attachment_url],
                    certified=certified,
                )
                response = {} if dry_run else self.email_sender.send(message)
                result.sent.append({"contact": contact, "response": response})
            except Exception as exc:
                result.errors.append({"contact": contact, "error": str(exc)})

        return result
