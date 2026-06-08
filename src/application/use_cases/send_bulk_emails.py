import time
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
    """Aggregates the outcome of a bulk email send operation.

    After executing SendBulkEmailsUseCase, callers inspect this object to
    understand which contacts received an email, which were skipped
    (missing email or attachment), and which failed during sending.

    Attributes:
        sent: List of dicts with keys 'contact' (Contact) and 'response'
            (raw API response dict). One entry per successfully sent email.
            In dry-run mode the response dict is always empty.
        skipped: List of Contact objects that were excluded before sending
            because they lacked an email address or an attachment URL value.
        errors: List of dicts with keys 'contact' (Contact) and 'error'
            (str). One entry per contact whose send attempt raised an
            exception (inaccessible attachment, API error, etc.).
    """

    sent: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def _skip_reason(contact, field_name: str) -> str:
    """Return the machine-readable reason why a contact was excluded from sending.

    Args:
        contact: The Contact that did not pass the eligibility filter.
        field_name: Name of the extra field that must hold an attachment value.

    Returns:
        'no_email' when the contact has no email address, 'no_attachment'
        when the attachment field is absent or empty.
    """
    if not contact.email:
        return "no_email"
    return "no_attachment"


class SendBulkEmailsUseCase:
    """Orchestrates sending a personalised email with attachment to a contact group.

    This use case implements the core business logic of the application:
    given a set of configuration choices made by the user (sender, template,
    group, extra field that holds the per-contact attachment URL) it fetches
    the eligible contacts, computes staggered send dates, and dispatches one
    email per contact through the injected email sender adapter.

    Contacts are automatically filtered out (skipped) if they have no email
    address or if their extra field does not contain an attachment value. If
    an attachment URL is inaccessible or the send fails for any reason the
    contact is moved to the errors list and processing continues with the
    remaining contacts.

    All infrastructure dependencies are injected at construction time,
    keeping this class testable without a real network or API.
    """

    def __init__(self, contact_repository: ContactRepository, email_sender: EmailSender):
        """Initialise the use case with its required infrastructure ports.

        Args:
            contact_repository: Adapter that retrieves contacts from the
                data source (typically the Mensagia API).
            email_sender: Adapter that dispatches emails through the
                delivery mechanism (typically the Mensagia API).
        """
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
        logger=None,
    ) -> SendResult:
        """Run the bulk send for all eligible contacts in the given group.

        Workflow:
        1. Fetch all contacts in the group (excluding the email blacklist).
        2. Filter down to contacts that have both an email and an attachment value.
        3. Compute staggered send dates to respect Mensagia's rate limits.
        4. For each eligible contact: resolve the attachment URL, optionally
           verify it is reachable, build the EmailMessage, and send it.
        5. Collect outcomes in a SendResult (sent / skipped / errors).

        Args:
            from_email: Verified sender email address to use as the 'from' field.
            group_id: ID of the Mensagia agenda group whose contacts to target.
            subject: Subject line for all outgoing emails.
            template_id: ID of the Mensagia template that defines the email body.
            extra_field: The ExtraField whose value holds each contact's attachment
                URL (or relative filename).
            certified: 1 to send as certified email, 0 for standard.
            now: Override for the current datetime, used in tests to make
                scheduling deterministic. Defaults to datetime.now().
            attachment_base_url: Root URL prepended to relative attachment values.
                Required when any contact stores only a filename in their
                extra field. Optional when all values are absolute URLs.
            attachment_checker: Optional AttachmentChecker instance. When provided,
                each attachment URL is verified before sending; contacts whose
                attachment is not reachable are added to the errors list.
                Pass None to skip URL verification entirely.
            dry_run: When True, all logic runs normally (eligibility check,
                URL resolution, accessibility check) but the email is never
                actually dispatched. Useful for previewing what would be sent.
                No log entries are written in dry-run mode.
            logger: Optional SendLogger instance. When provided and dry_run is
                False, one structured log line is written per contact outcome
                plus opening and closing summary lines. Pass None to disable
                logging entirely.

        Returns:
            A SendResult containing lists of sent, skipped, and errored contacts.
        """
        # Fetch all contacts in the group, excluding only those on the global
        # email blacklist. The API returns subscribed and unsubscribed contacts
        # alike — subscription status is not exposed by the Mensagia API.
        contacts = self.contact_repository.get_by_group(group_id, in_mail_blacklist=False)

        # Only contacts with both an email address and an attachment URL are eligible
        eligible = [
            c for c in contacts
            if c.email and c.extra_fields.get(extra_field.name)
        ]
        skipped = [c for c in contacts if c not in eligible]

        # Compute staggered start dates so emails are not sent all at once
        start_dates = calculate_start_dates(len(eligible), now)
        result = SendResult(skipped=skipped)

        # Log the opening summary and all skipped contacts before the send loop
        if logger and not dry_run:
            logger.log_start(
                from_email, subject, template_id, group_id,
                extra_field.name, certified, len(eligible), len(skipped),
            )
            for c in skipped:
                logger.log_skip(c, _skip_reason(c, extra_field.name))

        # Process each eligible contact paired with its scheduled send time
        for contact, start_date in zip(eligible, start_dates):
            try:
                # Resolve the attachment value to a fully qualified URL
                attachment_url = resolve_attachment_url(
                    contact.extra_fields[extra_field.name], attachment_base_url
                )

                # Optionally verify the attachment is reachable before sending
                if attachment_checker and not attachment_checker.is_accessible(attachment_url):
                    raise ValueError(f"attachment not accessible: {attachment_url}")

                # Build the email message for this contact
                message = EmailMessage(
                    from_email=from_email,
                    to_email=contact.email,
                    subject=subject,
                    template_id=template_id,
                    start_date=start_date,
                    attachments=[attachment_url],
                    certified=certified,
                )

                # Pause before each real API call to stay within the 1 request-per-second
                # rate limit; skipped in dry-run mode because no request is made
                if not dry_run:
                    time.sleep(1)
                response = {} if dry_run else self.email_sender.send(message)
                result.sent.append({"contact": contact, "response": response})

                if logger and not dry_run:
                    logger.log_ok(contact, attachment_url)

            except Exception as exc:
                # Any failure (network, API, inaccessible URL) is recorded and
                # processing continues with the next contact
                result.errors.append({"contact": contact, "error": str(exc)})
                if logger and not dry_run:
                    logger.log_error(contact, str(exc))

        # Log the closing summary once all contacts have been processed
        if logger and not dry_run:
            logger.log_done(len(result.sent), len(result.skipped), len(result.errors))

        return result
