from src.domain.entities.email_message import EmailMessage
from src.domain.ports.email_sender import (
    EmailNotSentError,
    EmailRejectedError,
    EmailSender,
    EmailSendError,
    EmailSendUncertainError,
)
from src.infrastructure.api.mensagia_client import MensagiaAPIError, MensagiaClient


# HTTP status meaning the API refused to process the request because of the
# rate limit; nothing was created, so the email can be retried safely.
_HTTP_TOO_MANY_REQUESTS = 429


def _translate_error(exc: MensagiaAPIError) -> EmailSendError:
    """Map a MensagiaAPIError to the EmailSender port's error type.

    The mapping is conservative: whenever the API may have created the
    message, the error is uncertain so the user gets warned about a
    possible duplicate instead of risking a silent one.

    Args:
        exc: The error raised by MensagiaClient.

    Returns:
        EmailNotSentError when the request was not processed (connection
        never opened, or 429), EmailRejectedError for other 4xx answers,
        and EmailSendUncertainError for 5xx answers or failures after the
        request was sent.
    """
    # Transport failure: whether the request left the machine decides it
    if exc.http_code is None:
        return EmailNotSentError(str(exc)) if not exc.reached_server else EmailSendUncertainError(str(exc))

    # Rate limited: the API refused to process it at all
    if exc.http_code == _HTTP_TOO_MANY_REQUESTS:
        return EmailNotSentError(str(exc))

    # Other 4xx: a deliberate refusal, typically a validation error
    if 400 <= exc.http_code < 500:
        return EmailRejectedError(str(exc))

    # 5xx (e.g. a gateway timeout) may hide a request processed behind the proxy
    return EmailSendUncertainError(str(exc))


class MensagiaEmailSender(EmailSender):
    """Implements EmailSender by posting messages to the Mensagia API.

    This adapter translates a domain EmailMessage into the form-encoded
    payload expected by the Mensagia 'email/simple' endpoint and dispatches
    the request through the injected MensagiaClient. Attachments are included
    only when the message has at least one attachment URL, because the API
    rejects the 'attachments' field when sent as an empty value.
    """

    def __init__(self, client: MensagiaClient):
        """Initialise the sender with a configured API client.

        Args:
            client: Authenticated MensagiaClient instance used to make
                API calls.
        """
        self.client = client

    def send(self, message: EmailMessage) -> dict:
        """Dispatch an email message through the Mensagia simple send API.

        Converts the domain EmailMessage into the form-encoded dictionary
        format required by the Mensagia API and posts it. The start_date
        is formatted as 'YYYY-MM-DD HH:MM:SS' as mandated by the API.
        Attachments are only included in the payload when the message has
        at least one URL to avoid sending an empty field.

        Args:
            message: The EmailMessage domain object containing all send
                parameters for this individual email.

        Returns:
            The raw parsed JSON response from the Mensagia API, typically
            containing the scheduled message ID and status.

        Raises:
            EmailRejectedError: The API refused the email (4xx answer).
            EmailNotSentError: The request was not processed (connection
                never opened, or rate limited); safe to retry.
            EmailSendUncertainError: The request may have been processed
                but no reliable answer arrived (response timeout, dropped
                connection, 5xx answer).
        """
        # Build the base payload with the fields always required by the API
        payload = {
            "from": message.from_email,
            "to": message.to_email,
            "subject": message.subject,
            "template_id": message.template_id,
            "start_date": message.start_date.strftime("%Y-%m-%d %H:%M:%S"),
            "certified": message.certified,
        }

        # Only add the attachments field when there are actual URLs to send;
        # the Mensagia API returns a validation error if the field is empty
        if message.attachments:
            payload["attachments"] = message.attachments

        # Translate API errors so the use case can decide on retries and
        # duplicate warnings without depending on the infrastructure layer
        try:
            return self.client.send_email(payload)
        except MensagiaAPIError as exc:
            raise _translate_error(exc) from exc
