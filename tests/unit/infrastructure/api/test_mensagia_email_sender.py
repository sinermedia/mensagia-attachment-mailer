from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.domain.entities.email_message import EmailMessage
from src.domain.ports.email_sender import (
    EmailNotSentError,
    EmailRejectedError,
    EmailSendUncertainError,
)
from src.infrastructure.api.mensagia_client import MensagiaAPIError
from src.infrastructure.api.mensagia_email_sender import MensagiaEmailSender


def make_message():
    """Build a minimal EmailMessage for sender tests."""
    return EmailMessage(
        from_email="from@test.com",
        to_email="to@test.com",
        subject="Hello",
        template_id=5,
        start_date=datetime(2024, 1, 15, 14, 40, 0),
        attachments=["https://example.com/a.pdf"],
        certified=0,
    )


@pytest.fixture
def client():
    """Mock MensagiaClient."""
    return MagicMock()


@pytest.fixture
def sender(client):
    """MensagiaEmailSender wired with the mock client."""
    return MensagiaEmailSender(client)


class TestMensagiaEmailSenderErrorTranslation:
    """Tests that API failures are translated into the EmailSender port's error types.

    The use case decides whether to retry a contact and whether to warn about
    a possible duplicate based only on these domain errors, so the mapping
    from transport and HTTP failures must be precise.
    """

    def test_returns_api_response_on_success(self, sender, client):
        """A successful call returns the raw API response unchanged."""
        client.send_email.return_value = {"data": {"id": 1}}
        assert sender.send(make_message()) == {"data": {"id": 1}}

    def test_failure_before_reaching_server_is_not_sent(self, sender, client):
        """A transport error that never reached the server becomes EmailNotSentError."""
        client.send_email.side_effect = MensagiaAPIError("Connection error", reached_server=False)
        with pytest.raises(EmailNotSentError):
            sender.send(make_message())

    def test_failure_after_reaching_server_is_uncertain(self, sender, client):
        """A transport error after the request was sent becomes EmailSendUncertainError."""
        client.send_email.side_effect = MensagiaAPIError("Connection error", reached_server=True)
        with pytest.raises(EmailSendUncertainError):
            sender.send(make_message())

    def test_client_error_response_is_rejected(self, sender, client):
        """A 4xx answer means the API refused the email, so it becomes EmailRejectedError."""
        client.send_email.side_effect = MensagiaAPIError("invalid", http_code=422)
        with pytest.raises(EmailRejectedError):
            sender.send(make_message())

    def test_too_many_requests_is_not_sent(self, sender, client):
        """A 429 answer means the request was not processed, so it becomes EmailNotSentError."""
        client.send_email.side_effect = MensagiaAPIError("slow down", http_code=429)
        with pytest.raises(EmailNotSentError):
            sender.send(make_message())

    def test_server_error_response_is_uncertain(self, sender, client):
        """A 5xx answer may hide a partially processed request, so it becomes EmailSendUncertainError."""
        client.send_email.side_effect = MensagiaAPIError("gateway timeout", http_code=504)
        with pytest.raises(EmailSendUncertainError):
            sender.send(make_message())

    def test_translated_error_keeps_original_message(self, sender, client):
        """The translated error keeps the original message so it can be shown to the user."""
        client.send_email.side_effect = MensagiaAPIError("invalid address", http_code=422)
        with pytest.raises(EmailRejectedError, match="invalid address"):
            sender.send(make_message())
