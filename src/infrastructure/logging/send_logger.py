import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path


def _default_log_dir() -> Path:
    """Return the default log directory depending on execution context.

    Returns:
        Path next to the executable when bundled with PyInstaller, or the
        'logs' sub-directory at the repository root in development mode.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "logs"
    return Path(__file__).parents[3] / "logs"


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


class SendLogger:
    """Writes a structured log file for a single real bulk-send operation.

    Produces one log file per send session in the configured directory.
    Every line carries an ISO-8601 timestamp and a keyword tag that makes
    it trivial to filter outcomes with grep:

    - [SEND_START] — opening summary with all shared send parameters
    - [SEND_OK]    — one entry per successfully dispatched email
    - [SEND_SKIP]  — one entry per contact excluded before sending
    - [SEND_ERROR] — one entry per contact whose send attempt failed
    - [SEND_DONE]  — closing summary with total counts

    Example grep usage::

        grep SEND_OK  mensagia_send_20240115_143000.log   # all successes
        grep SEND_ERROR mensagia_send_20240115_143000.log  # all failures

    Attributes:
        log_path: Absolute Path of the log file created for this session.
    """

    def __init__(self, log_dir: str | None = None):
        """Create the log file and configure the underlying Python logger.

        The log directory is created if it does not exist. The file is named
        with a datetime stamp so each session produces a separate file.

        Args:
            log_dir: Directory to write the log file into. Defaults to a
                'logs' sub-directory next to the executable (frozen bundle)
                or at the repository root (development run).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_path = Path(log_dir) if log_dir is not None else _default_log_dir()
        dir_path.mkdir(parents=True, exist_ok=True)
        self.log_path = dir_path / f"mensagia_send_{timestamp}.log"

        # Unique logger name prevents handler accumulation across instances
        self._logger = logging.getLogger(f"mensagia_{uuid.uuid4().hex}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        handler = logging.FileHandler(self.log_path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        self._logger.addHandler(handler)

    def log_start(
        self,
        from_email: str,
        subject: str,
        template_id: int,
        group_id: int,
        field_name: str,
        certified: int,
        eligible_count: int,
        skipped_count: int,
    ) -> None:
        """Log the opening line of a send session with all shared parameters.

        Call this once before iterating over contacts so that the parameters
        common to every email in the batch are recorded only once.

        Args:
            from_email: Verified sender email address.
            subject: Email subject line.
            template_id: Numeric ID of the selected template.
            group_id: Numeric ID of the target contact group.
            field_name: Name of the extra field used as attachment source.
            certified: 1 if sending as certified email, 0 otherwise.
            eligible_count: Number of contacts that will be sent to.
            skipped_count: Number of contacts excluded before sending.
        """
        self._logger.info(
            f"[SEND_START] from={from_email} subject={_q(subject)} "
            f"template_id={template_id} group_id={group_id} field={field_name} "
            f"certified={certified} eligible={eligible_count} skipped={skipped_count}"
        )

    def log_ok(self, contact, attachment_url: str) -> None:
        """Log a successful individual email dispatch.

        Args:
            contact: Contact domain entity that received the email.
            attachment_url: Fully resolved URL of the sent attachment.
        """
        self._logger.info(
            f"[SEND_OK]    id={contact.id} name={_q(contact.name)} "
            f"to={contact.email} attachment={_q(attachment_url)}"
        )

    def log_skip(self, contact, reason: str) -> None:
        """Log a contact that was excluded before any send attempt.

        Args:
            contact: Contact domain entity that was skipped.
            reason: Machine-readable skip reason: 'no_email' when the
                contact has no email address, 'no_attachment' when the
                attachment field is empty.
        """
        email = contact.email or ""
        self._logger.info(
            f"[SEND_SKIP]  id={contact.id} name={_q(contact.name)} "
            f"to={email} reason={reason}"
        )

    def log_error(self, contact, reason: str) -> None:
        """Log a contact whose send attempt raised an exception.

        Args:
            contact: Contact domain entity whose send failed.
            reason: Human-readable error description (typically the
                exception message).
        """
        self._logger.info(
            f"[SEND_ERROR] id={contact.id} name={_q(contact.name)} "
            f"to={contact.email} reason={_q(reason)}"
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
