from src.domain.entities.email_message import EmailMessage
from src.domain.ports.email_sender import EmailSender
from src.infrastructure.api.mensagia_client import MensagiaClient


class MensagiaEmailSender(EmailSender):
    def __init__(self, client: MensagiaClient):
        self.client = client

    def send(self, message: EmailMessage) -> dict:
        payload = {
            "from": message.from_email,
            "to": message.to_email,
            "subject": message.subject,
            "template_id": message.template_id,
            "start_date": message.start_date.strftime("%Y-%m-%d %H:%M:%S"),
            "certified": message.certified,
        }
        if message.attachments:
            payload["attachments"] = message.attachments
        return self.client.send_email(payload)
