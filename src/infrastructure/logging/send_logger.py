import logging
import uuid
from datetime import datetime
from pathlib import Path

from src.domain.scheduling import StartMode
from src.infrastructure.config.app_paths import user_data_dir


def _default_log_dir() -> Path:
    """Return the default log directory depending on execution context.

    Returns:
        The 'logs' sub-directory of the shared user data directory: next to
        the .exe on Windows, in ~/Mensagia Mailer on macOS, or at the
        repository root in development mode (see user_data_dir).
    """
    return user_data_dir() / "logs"


def _q(value: str) -> str:
    """Wrap a string in double quotes when it contains spaces or is empty.

    Args:
        value: The value to optionally quote.

    Returns:
        The original string if it contains no spaces, otherwise the string
        wrapped in double quotes with any embedded double quotes escaped.
    """
    s = str(value)
    if not s or " " in s:
        return '"' + s.replace('"', '\\"') + '"'
    return s


def _who(recipient) -> str:
    """Identify a recipient in a log line, the way the user can find it in its source.

    An agenda contact is identified by its ID and name. A file row has
    neither, so it is identified by its row number, as a spreadsheet shows
    it, and its attachment value, which tells apart rows sent to the same
    address.

    Args:
        recipient: Recipient the line is about.

    Returns:
        The 'name=value' pairs identifying the recipient, email included.
    """
    if recipient.row is not None:
        return f"row={recipient.row} to={recipient.email} attachment={_q(recipient.attachment)}"
    return f"id={recipient.key} name={_q(recipient.name)} to={recipient.email}"


class SendLogger:
    """Writes a structured log file for a single bulk-send operation or simulation.

    Produces one log file per send session in the configured directory.
    Every line carries an ISO-8601 timestamp and a keyword tag that makes
    it trivial to filter outcomes with grep:

    - [SIMULATION] — header line, only in simulation logs, stating that no
      email was sent
    - [SEND_START] — opening summary with all shared send parameters
    - [SEND_OK]    — one entry per successfully dispatched email
    - [SEND_SKIP]  — one entry per recipient excluded before sending
    - [SEND_ERROR] — one entry per recipient whose send attempt failed
    - [SEND_UNCERTAIN] — one entry per attempt that may have been scheduled
      although the API gave no reliable answer (possible duplicate)
    - [SEND_DONE]  — closing summary with total counts

    Example grep usage::

        grep SEND_OK  mensagia_send_20240115_143000.log   # all successes
        grep SEND_ERROR mensagia_send_20240115_143000.log  # all failures

    A simulation writes the same entries, where [SEND_OK] means the email
    would have been sent, to a file named mensagia_simulation_<timestamp>.log
    so it is never mistaken for the log of a real send.

    Attributes:
        log_path: Absolute Path of the log file created for this session.
    """

    def __init__(self, log_dir: str | None = None, simulation: bool = False):
        """Create the log file and configure the underlying Python logger.

        The log directory is created if it does not exist. The file is named
        with a datetime stamp so each session produces a separate file.

        Args:
            log_dir: Directory to write the log file into. Defaults to a
                'logs' sub-directory of the user data directory (next to
                the .exe on Windows, ~/Mensagia Mailer on macOS, the
                repository root in a development run).
            simulation: True to log a simulation (dry run): the file gets the
                mensagia_simulation_ prefix and opens with a [SIMULATION]
                header line.
        """
        # Simulations share the folder of real sends but use their own
        # prefix, so sorting by name keeps both kinds of log apart
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_path = Path(log_dir) if log_dir is not None else _default_log_dir()
        dir_path.mkdir(parents=True, exist_ok=True)
        prefix = "mensagia_simulation" if simulation else "mensagia_send"
        self.log_path = dir_path / f"{prefix}_{timestamp}.log"

        # Unique logger name prevents handler accumulation across instances
        self._logger = logging.getLogger(f"mensagia_{uuid.uuid4().hex}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        handler = logging.FileHandler(self.log_path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        self._logger.addHandler(handler)

        # State it on the very first line: a simulation log otherwise reads
        # exactly like a real one, [SEND_OK] entries included
        if simulation:
            self._logger.info("[SIMULATION] This is a simulation: no email was sent.")

    def log_start(
        self,
        from_email: str,
        subject: str,
        template_id: int,
        source: dict[str, str],
        field_name: str,
        certified: int,
        eligible_count: int,
        skipped_count: int,
        start_mode: StartMode = StartMode.NOW,
        start_at: datetime | None = None,
        first_slot: datetime | None = None,
    ) -> None:
        """Log the opening line of a send session with all shared parameters.

        Call this once before iterating over contacts so that the parameters
        common to every email in the batch are recorded only once.

        Args:
            from_email: Verified sender email address.
            subject: Email subject line.
            template_id: Numeric ID of the selected template.
            source: Fields identifying the recipient source, as given by
                its log_fields (e.g. {'group_id': '15'}).
            field_name: Name of the extra field or column holding the attachment.
            certified: 1 if sending as certified email, 0 otherwise.
            eligible_count: Number of recipients that will be sent to.
            skipped_count: Number of recipients excluded before sending.
            start_mode: How the first email is scheduled.
            start_at: Start chosen by the user in the fixed start mode, or
                None in the "now" mode.
            first_slot: Slot actually given to the first email, which can
                differ from *start_at* when it was postponed or the send
                was resumed. None when no email is scheduled.
        """
        # The chosen start and the first slot are recorded side by side, so
        # a postponed start can be spotted in the log
        schedule = f"start_mode={start_mode.value}"
        if start_at is not None:
            schedule += f" start_at={start_at.isoformat()}"
        if first_slot is not None:
            schedule += f" first_slot={first_slot.isoformat()}"
        origin = " ".join(f"{name}={_q(value)}" for name, value in source.items())
        self._logger.info(
            f"[SEND_START] from={from_email} subject={_q(subject)} "
            f"template_id={template_id} {origin} field={_q(field_name)} "
            f"certified={certified} eligible={eligible_count} skipped={skipped_count} {schedule}"
        )

    def log_ok(self, recipient, attachment_url: str) -> None:
        """Log a successful individual email dispatch.

        Args:
            recipient: Recipient that received the email.
            attachment_url: Fully resolved URL of the sent attachment, shown
                in place of a file row's attachment value.
        """
        # A file row already shows its attachment: replace it with the URL
        if recipient.row is not None:
            who = f"row={recipient.row} to={recipient.email}"
        else:
            who = _who(recipient)
        self._logger.info(f"[SEND_OK]    {who} attachment={_q(attachment_url)}")

    def log_skip(self, recipient, reason: str) -> None:
        """Log a recipient that was excluded before any send attempt.

        Args:
            recipient: Recipient that was skipped.
            reason: Machine-readable skip reason, such as 'no_email',
                'no_attachment' or 'already_sent'.
        """
        self._logger.info(f"[SEND_SKIP]  {_who(recipient)} reason={reason}")

    def log_error(self, recipient, reason: str) -> None:
        """Log a recipient whose send attempt raised an exception.

        Args:
            recipient: Recipient whose send failed.
            reason: Human-readable error description (typically the
                exception message).
        """
        self._logger.info(f"[SEND_ERROR] {_who(recipient)} reason={_q(reason)}")

    def log_uncertain(self, recipient, start_date: datetime, reason: str) -> None:
        """Log a send attempt that may have been scheduled although no answer arrived.

        The slot is recorded so the user can find the possible duplicate in
        the Mensagia portal later, even after the on-screen summary is gone.

        Args:
            recipient: Recipient of the uncertain attempt.
            start_date: Send slot requested in that attempt.
            reason: Human-readable error description.
        """
        self._logger.info(
            f"[SEND_UNCERTAIN] {_who(recipient)} "
            f"start_date={start_date.isoformat()} reason={_q(reason)}"
        )

    def log_done(self, sent: int, skipped: int, errors: int) -> None:
        """Log the closing summary line of the send session.

        Args:
            sent: Number of emails successfully dispatched.
            skipped: Number of contacts excluded before sending.
            errors: Number of contacts whose send attempt failed.
        """
        self._logger.info(
            f"[SEND_DONE]  sent={sent} skipped={skipped} errors={errors}"
        )
