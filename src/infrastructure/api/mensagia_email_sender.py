from src.domain.entities.email_message import EmailMessage
from src.domain.ports.email_sender import EmailSender
from src.infrastructure.api.mensagia_client import MensagiaClient


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
            MensagiaAPIError: If the API rejects the request or a transport
                error occurs.
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

        return self.client.send_email(payload)
