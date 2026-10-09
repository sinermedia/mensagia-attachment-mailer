import time
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.campaign import Campaign
from src.domain.entities.email_message import EmailMessage
from src.domain.entities.extra_field import ExtraField
from src.domain.ports.contact_repository import ContactRepository
from src.domain.ports.email_sender import EmailNotSentError, EmailRejectedError, EmailSender
from src.domain.scheduling import StartMode, calculate_start_dates
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
        already_sent: List of Contact objects that were excluded because a
            send_registry showed they already received this exact campaign
            in a previous, interrupted run. Empty when no send_registry is
            given.
        errors: List of dicts with keys 'contact' (Contact) and 'error'
            (str). One entry per contact whose send attempt raised an
            exception (inaccessible attachment, API error, etc.). Contacts
            retried at the end of the run appear here only if the retry
            failed too.
        uncertain: List of dicts with keys 'contact' (Contact),
            'start_dates' (sorted list of datetime) and 'sent' (bool). One
            entry per contact with send attempts that may have been
            scheduled without the API confirming it, in this run or in a
            previous interrupted one. The user must check those slots in
            the Mensagia portal: when 'sent' is True the contact also got a
            confirmed email, so any of those slots is a duplicate. Always
            empty in dry-run mode.
    """

    sent: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    already_sent: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    uncertain: list = field(default_factory=list)


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
        progress_callback=None,
        send_registry=None,
        start_mode: StartMode = StartMode.NOW,
        start_at: datetime | None = None,
    ) -> SendResult:
        """Run the bulk send for all eligible contacts in the given group.

        Workflow:
        1. Fetch all contacts in the group (excluding the email blacklist).
        2. Filter down to contacts that have both an email and an attachment value.
        3. Compute staggered send dates to respect Mensagia's rate limits,
           from the chosen start (postponed if it is too close) or 10 to 20
           minutes from now, continuing after the last slot of a previous
           run when resuming.
        4. For each eligible contact: resolve the attachment URL, optionally
           verify it is reachable, build the EmailMessage, and send it.
        5. Retry once, after all other contacts, every send that got no
           answer from the API (not processed or uncertain outcome).
        6. Collect outcomes in a SendResult (sent / skipped / errors /
           uncertain).

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
                The logger, when given, records the same entries as in a
                real send, so the preview explains every skipped contact.
            logger: Optional SendLogger instance. When provided, one
                structured log line is written per contact outcome plus
                opening and closing summary lines, in dry-run mode too
                (where a sent entry means it would be sent). Pass None to
                disable logging entirely.
            progress_callback: Optional callable invoked as
                progress_callback(current, total) after each eligible contact
                is processed (sent or errored), where current is the
                1-indexed position and total is len(eligible). Lets a UI
                (e.g. a progress bar) reflect progress without needing to
                reimplement this loop. Fires in dry-run mode too, and not
                for end-of-run retries. Pass None to disable.
            send_registry: Optional SendRegistry instance. When provided,
                contacts already recorded as sent for this exact campaign
                (group, template, extra field, subject and start mode) are
                excluded from the eligible list and reported in
                already_sent instead, and the schedule continues after the
                campaign's last recorded slot. Each API call is recorded
                with mark_attempt() before being made and resolved with
                mark_sent() or discard_attempt(); uncertain ones stay on
                record. The whole campaign record is cleared once a run
                completes with zero errors. Not written to during dry-run,
                though filtering and scheduling still apply so the preview
                matches what a real run would do. Pass None to disable.
            start_mode: How the first email is scheduled. Part of the
                campaign's identity in the send registry. Defaults to
                StartMode.NOW.
            start_at: Date and time chosen for the first email; required
                with StartMode.FIXED and ignored otherwise. A start that no
                longer leaves 10 minutes is postponed, never brought forward.
                It is not validated here: a dry run only checks the data.

        Returns:
            A SendResult containing lists of sent, skipped, already-sent,
            errored and uncertain contacts.

        Raises:
            ValueError: If start_mode is StartMode.FIXED and start_at is None.
        """
        # A fixed start needs its date; fail before touching anything
        if start_mode == StartMode.FIXED and start_at is None:
            raise ValueError("a fixed start mode requires start_at")
        if start_mode != StartMode.FIXED:
            start_at = None

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

        # Exclude contacts already sent this exact campaign in a previous,
        # interrupted run so restarting never double-sends. Filtering (but
        # not writing) also applies during dry-run so previews stay accurate.
        campaign = Campaign(str(group_id), template_id, extra_field.name, subject, start_mode)
        already_sent = []
        last_scheduled = None
        uncertain = {}
        if send_registry:
            sent_keys = send_registry.get_sent_keys(campaign)
            already_sent = [c for c in eligible if str(c.id) in sent_keys]
            eligible = [c for c in eligible if str(c.id) not in sent_keys]

            # The emails of a previous run may still be queued: continue the
            # schedule after its last slot so both runs never overlap
            last_scheduled = send_registry.get_last_start_date(campaign)

            # Attempts a previous run left unresolved may have been scheduled;
            # carry them over so they are reported with this run's outcome.
            # A dry run never reports them, as it does not contact the API
            if not dry_run:
                uncertain = {
                    key: list(dates)
                    for key, dates in send_registry.get_uncertain_attempts(campaign).items()
                }

        # Compute staggered start dates so emails are not sent all at once
        start_dates = calculate_start_dates(len(eligible), now, last_scheduled, start_at)
        result = SendResult(skipped=skipped, already_sent=already_sent)

        # Log the opening summary and all skipped/already-sent contacts before the send loop
        if logger:
            logger.log_start(
                from_email, subject, template_id, group_id,
                extra_field.name, certified, len(eligible), len(skipped),
                start_mode=start_mode, start_at=start_at,
                first_slot=start_dates[0] if start_dates else None,
            )
            for c in skipped:
                logger.log_skip(c, _skip_reason(c, extra_field.name))
            for c in already_sent:
                logger.log_skip(c, "already_sent")

        def record_error(contact, error: Exception) -> None:
            """Add a final failure to the result and the log.

            Args:
                contact: Contact whose send failed for good.
                error: The exception that caused the failure.
            """
            result.errors.append({"contact": contact, "error": str(error)})
            if logger:
                logger.log_error(contact, str(error))

        def process(contact, start_date: datetime, final: bool) -> bool:
            """Build and send the email of one contact, recording its outcome.

            Args:
                contact: Contact to email.
                start_date: Send slot assigned to this attempt.
                final: True for the end-of-run retry, whose failures are
                    always reported as errors.

            Returns:
                True when the API gave no answer and the contact must be
                retried at the end of the run; False otherwise.
            """
            # Prepare the message. Failures here happen before any API call,
            # so they are final: retrying would fail the same way
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
            except Exception as exc:
                record_error(contact, exc)
                return False

            # A dry run stops here: everything that could fail locally was
            # checked, so the contact is logged as one that would be sent
            if dry_run:
                result.sent.append({"contact": contact, "response": {}})
                if logger:
                    logger.log_ok(contact, attachment_url)
                return False

            # Record the attempt before calling the API, so an abrupt close
            # right after the API accepts it leaves it on record as uncertain.
            # Pause before each API call to stay within the 1 request-per-second limit
            if send_registry:
                send_registry.mark_attempt(campaign, str(contact.id), start_date)
            time.sleep(1)

            try:
                response = self.email_sender.send(message)
            except (EmailRejectedError, EmailNotSentError) as exc:
                # Nothing was scheduled, so the attempt is forgotten. Only a
                # request that was not processed is worth retrying
                if send_registry:
                    send_registry.discard_attempt(campaign, str(contact.id), start_date)
                error = exc
                retry = isinstance(exc, EmailNotSentError) and not final
            except Exception as exc:
                # Uncertain outcome, or an unexpected error treated as such to
                # stay on the safe side: the email may exist, so keep the
                # attempt on record and remember its slot for the warning
                uncertain.setdefault(str(contact.id), []).append(start_date)
                if logger:
                    logger.log_uncertain(contact, start_date, str(exc))
                error = exc
                retry = not final
            else:
                result.sent.append({"contact": contact, "response": response})
                if logger:
                    logger.log_ok(contact, attachment_url)
                if send_registry:
                    send_registry.mark_sent(campaign, str(contact.id), start_date)
                return False

            if not retry:
                record_error(contact, error)
            return retry

        # Process each eligible contact paired with its scheduled send time,
        # reporting progress after every one regardless of outcome (dry-run
        # included) so a UI progress bar stays accurate
        to_retry = []
        for i, (contact, start_date) in enumerate(zip(eligible, start_dates), 1):
            if process(contact, start_date, final=False):
                to_retry.append(contact)
            if progress_callback:
                progress_callback(i, len(eligible))

        # Retry unanswered sends once, after every other contact: this gives a
        # transient network failure time to recover, and the new slots follow
        # the last one of this run so the sending rhythm is kept
        if to_retry:
            retry_dates = calculate_start_dates(len(to_retry), now, start_dates[-1])
            for contact, start_date in zip(to_retry, retry_dates):
                process(contact, start_date, final=True)

        # Report every uncertain attempt with whether the contact ended up
        # sent, which turns those slots into possible duplicates. Contacts no
        # longer in the group cannot be shown and are left out
        confirmed_keys = {str(item["contact"].id) for item in result.sent} | {str(c.id) for c in already_sent}
        contacts_by_key = {str(c.id): c for c in contacts}
        result.uncertain = [
            {"contact": contacts_by_key[key], "start_dates": sorted(dates), "sent": key in confirmed_keys}
            for key, dates in uncertain.items()
            if key in contacts_by_key
        ]

        # Log the closing summary once all contacts have been processed
        if logger:
            logger.log_done(len(result.sent), len(result.skipped), len(result.errors))

        # A clean run (no errors) means nothing is left pending for this
        # campaign, so forget its progress and stop blocking future re-sends
        if send_registry and not dry_run and not result.errors:
            send_registry.clear(campaign)

        return result
