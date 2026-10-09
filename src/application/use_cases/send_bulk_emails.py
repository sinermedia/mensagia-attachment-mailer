import time
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.campaign import Campaign
from src.domain.entities.email_message import EmailMessage
from src.domain.ports.email_sender import EmailNotSentError, EmailRejectedError, EmailSender
from src.domain.ports.recipient_source import RecipientSource
from src.domain.scheduling import StartMode, calculate_start_dates
from src.domain.attachment_url import resolve_attachment_url


@dataclass
class SendResult:
    """Aggregates the outcome of a bulk email send operation.

    After executing SendBulkEmailsUseCase, callers inspect this object to
    understand which recipients received an email, which were skipped
    (see Recipient.skip_reason), and which failed during sending.

    Attributes:
        sent: List of dicts with keys 'recipient' (Recipient) and 'response'
            (raw API response dict). One entry per successfully sent email.
            In dry-run mode the response dict is always empty.
        skipped: List of Recipient objects that were excluded before sending
            because their source gave a skip reason (no email address, no
            attachment value...).
        already_sent: List of Recipient objects that were excluded because a
            send_registry showed they already received this exact campaign
            in a previous, interrupted run. Empty when no send_registry is
            given.
        errors: List of dicts with keys 'recipient' (Recipient) and 'error'
            (str). One entry per recipient whose send attempt raised an
            exception (inaccessible attachment, API error, etc.). Recipients
            retried at the end of the run appear here only if the retry
            failed too.
        uncertain: List of dicts with keys 'recipient' (Recipient),
            'start_dates' (sorted list of datetime) and 'sent' (bool). One
            entry per recipient with send attempts that may have been
            scheduled without the API confirming it, in this run or in a
            previous interrupted one. The user must check those slots in
            the Mensagia portal: when 'sent' is True the recipient also got
            a confirmed email, so any of those slots is a duplicate. Always
            empty in dry-run mode.
    """

    sent: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    already_sent: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    uncertain: list = field(default_factory=list)


class SendBulkEmailsUseCase:
    """Orchestrates sending a personalised email with attachment to a list of recipients.

    This use case implements the core business logic of the application:
    given a set of configuration choices made by the user (sender, template,
    and a recipient source that also knows where each attachment is) it
    reads the recipients, computes staggered send dates, and dispatches one
    email per recipient through the injected email sender adapter.

    Recipients that their source marks with a skip reason (no email address,
    no attachment value...) are not sent. If an attachment URL is
    inaccessible or the send fails for any reason the recipient is moved to
    the errors list and processing continues with the remaining ones.

    The email sender is injected at construction time, and the recipient
    source on each run, keeping this class testable without a real network
    or API.

    Attributes:
        email_sender: Adapter that dispatches emails.
    """

    def __init__(self, email_sender: EmailSender):
        """Initialise the use case with its delivery port.

        Args:
            email_sender: Adapter that dispatches emails through the
                delivery mechanism (typically the Mensagia API).
        """
        self.email_sender = email_sender

    def execute(
        self,
        from_email: str,
        recipient_source: RecipientSource,
        subject: str,
        template_id: int,
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
        """Run the bulk send for all sendable recipients of the given source.

        Workflow:
        1. Read every recipient of the source.
        2. Leave out those the source marks with a skip reason.
        3. Compute staggered send dates to respect Mensagia's rate limits,
           from the chosen start (postponed if it is too close) or 10 to 20
           minutes from now, continuing after the last slot of a previous
           run when resuming.
        4. For each eligible recipient: resolve the attachment URL, optionally
           verify it is reachable, build the EmailMessage, and send it.
        5. Retry once, after all other recipients, every send that got no
           answer from the API (not processed or uncertain outcome).
        6. Collect outcomes in a SendResult (sent / skipped / errors /
           uncertain).

        Args:
            from_email: Verified sender email address to use as the 'from' field.
            recipient_source: Where the recipients come from, and which of
                their fields holds the attachment URL (or relative filename).
            subject: Subject line for all outgoing emails.
            template_id: ID of the Mensagia template that defines the email body.
            certified: 1 to send as certified email, 0 for standard.
            now: Override for the current datetime, used in tests to make
                scheduling deterministic. Defaults to datetime.now().
            attachment_base_url: Root URL prepended to relative attachment values.
                Required when any recipient stores only a filename in its
                attachment field. Optional when all values are absolute URLs.
            attachment_checker: Optional AttachmentChecker instance. When provided,
                each attachment URL is verified before sending; recipients whose
                attachment is not reachable are added to the errors list.
                Pass None to skip URL verification entirely.
            dry_run: When True, all logic runs normally (eligibility check,
                URL resolution, accessibility check) but the email is never
                actually dispatched. Useful for previewing what would be sent.
                The logger, when given, records the same entries as in a
                real send, so the preview explains every skipped recipient.
            logger: Optional SendLogger instance. When provided, one
                structured log line is written per recipient outcome plus
                opening and closing summary lines, in dry-run mode too
                (where a sent entry means it would be sent). Pass None to
                disable logging entirely.
            progress_callback: Optional callable invoked as
                progress_callback(current, total) after each eligible recipient
                is processed (sent or errored), where current is the
                1-indexed position and total is len(eligible). Lets a UI
                (e.g. a progress bar) reflect progress without needing to
                reimplement this loop. Fires in dry-run mode too, and not
                for end-of-run retries. Pass None to disable.
            send_registry: Optional SendRegistry instance. When provided,
                recipients already recorded as sent for this exact campaign
                (source, template, attachment field, subject and start mode) are
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
            errored and uncertain recipients.

        Raises:
            ValueError: If start_mode is StartMode.FIXED and start_at is None.
        """
        # A fixed start needs its date; fail before touching anything
        if start_mode == StartMode.FIXED and start_at is None:
            raise ValueError("a fixed start mode requires start_at")
        if start_mode != StartMode.FIXED:
            start_at = None

        # Read every recipient: the source decides which ones cannot be sent,
        # since that depends on what it can hold
        recipients = recipient_source.get_recipients()
        eligible = [r for r in recipients if r.skip_reason is None]
        skipped = [r for r in recipients if r.skip_reason is not None]

        # Exclude recipients already sent this exact campaign in a previous,
        # interrupted run so restarting never double-sends. Filtering (but
        # not writing) also applies during dry-run so previews stay accurate.
        campaign = Campaign(recipient_source.identity, template_id, recipient_source.attachment_field,
                            subject, start_mode)
        already_sent = []
        last_scheduled = None
        uncertain = {}
        if send_registry:
            sent_keys = send_registry.get_sent_keys(campaign)
            already_sent = [r for r in eligible if r.key in sent_keys]
            eligible = [r for r in eligible if r.key not in sent_keys]

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

        # Log the opening summary and all skipped/already-sent recipients before the send loop
        if logger:
            logger.log_start(
                from_email, subject, template_id, recipient_source.log_fields,
                recipient_source.attachment_field, certified, len(eligible), len(skipped),
                start_mode=start_mode, start_at=start_at,
                first_slot=start_dates[0] if start_dates else None,
            )
            for r in skipped:
                logger.log_skip(r, r.skip_reason)
            for r in already_sent:
                logger.log_skip(r, "already_sent")

        def record_error(recipient, error: Exception) -> None:
            """Add a final failure to the result and the log.

            Args:
                recipient: Recipient whose send failed for good.
                error: The exception that caused the failure.
            """
            result.errors.append({"recipient": recipient, "error": str(error)})
            if logger:
                logger.log_error(recipient, str(error))

        def process(recipient, start_date: datetime, final: bool) -> bool:
            """Build and send the email of one recipient, recording its outcome.

            Args:
                recipient: Recipient to email.
                start_date: Send slot assigned to this attempt.
                final: True for the end-of-run retry, whose failures are
                    always reported as errors.

            Returns:
                True when the API gave no answer and the recipient must be
                retried at the end of the run; False otherwise.
            """
            # Prepare the message. Failures here happen before any API call,
            # so they are final: retrying would fail the same way
            try:
                attachment_url = resolve_attachment_url(recipient.attachment, attachment_base_url)
                if attachment_checker and not attachment_checker.is_accessible(attachment_url):
                    raise ValueError(f"attachment not accessible: {attachment_url}")
                message = EmailMessage(
                    from_email=from_email,
                    to_email=recipient.email,
                    subject=subject,
                    template_id=template_id,
                    start_date=start_date,
                    attachments=[attachment_url],
                    certified=certified,
                )
            except Exception as exc:
                record_error(recipient, exc)
                return False

            # A dry run stops here: everything that could fail locally was
            # checked, so the recipient is logged as one that would be sent
            if dry_run:
                result.sent.append({"recipient": recipient, "response": {}})
                if logger:
                    logger.log_ok(recipient, attachment_url)
                return False

            # Record the attempt before calling the API, so an abrupt close
            # right after the API accepts it leaves it on record as uncertain.
            # Pause before each API call to stay within the 1 request-per-second limit
            if send_registry:
                send_registry.mark_attempt(campaign, recipient.key, start_date)
            time.sleep(1)

            try:
                response = self.email_sender.send(message)
            except (EmailRejectedError, EmailNotSentError) as exc:
                # Nothing was scheduled, so the attempt is forgotten. Only a
                # request that was not processed is worth retrying
                if send_registry:
                    send_registry.discard_attempt(campaign, recipient.key, start_date)
                error = exc
                retry = isinstance(exc, EmailNotSentError) and not final
            except Exception as exc:
                # Uncertain outcome, or an unexpected error treated as such to
                # stay on the safe side: the email may exist, so keep the
                # attempt on record and remember its slot for the warning
                uncertain.setdefault(recipient.key, []).append(start_date)
                if logger:
                    logger.log_uncertain(recipient, start_date, str(exc))
                error = exc
                retry = not final
            else:
                result.sent.append({"recipient": recipient, "response": response})
                if logger:
                    logger.log_ok(recipient, attachment_url)
                if send_registry:
                    send_registry.mark_sent(campaign, recipient.key, start_date)
                return False

            if not retry:
                record_error(recipient, error)
            return retry

        # Process each eligible recipient paired with its scheduled send time,
        # reporting progress after every one regardless of outcome (dry-run
        # included) so a UI progress bar stays accurate
        to_retry = []
        for i, (recipient, start_date) in enumerate(zip(eligible, start_dates), 1):
            if process(recipient, start_date, final=False):
                to_retry.append(recipient)
            if progress_callback:
                progress_callback(i, len(eligible))

        # Retry unanswered sends once, after every other recipient: this gives a
        # transient network failure time to recover, and the new slots follow
        # the last one of this run so the sending rhythm is kept
        if to_retry:
            retry_dates = calculate_start_dates(len(to_retry), now, start_dates[-1])
            for recipient, start_date in zip(to_retry, retry_dates):
                process(recipient, start_date, final=True)

        # Report every uncertain attempt with whether the recipient ended up
        # sent, which turns those slots into possible duplicates. Recipients
        # no longer in the source cannot be shown and are left out
        confirmed_keys = {item["recipient"].key for item in result.sent} | {r.key for r in already_sent}
        recipients_by_key = {r.key: r for r in recipients}
        result.uncertain = [
            {"recipient": recipients_by_key[key], "start_dates": sorted(dates), "sent": key in confirmed_keys}
            for key, dates in uncertain.items()
            if key in recipients_by_key
        ]

        # Log the closing summary once all recipients have been processed
        if logger:
            logger.log_done(len(result.sent), len(result.skipped), len(result.errors))

        # A clean run (no errors) means nothing is left pending for this
        # campaign, so forget its progress and stop blocking future re-sends
        if send_registry and not dry_run and not result.errors:
            send_registry.clear(campaign)

        return result
