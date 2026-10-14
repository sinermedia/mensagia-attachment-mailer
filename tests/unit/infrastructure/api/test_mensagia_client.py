from http.client import RemoteDisconnected
from unittest.mock import MagicMock

import pytest
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout
from urllib3.exceptions import (
    ConnectTimeoutError,
    MaxRetryError,
    NameResolutionError,
    NewConnectionError,
    ProtocolError,
)

from src.infrastructure.api.mensagia_client import MensagiaAPIError, MensagiaClient


def _wrapped(reason):
    """Wrap a urllib3 low-level error the same way requests does after its single attempt."""
    return MaxRetryError(None, "/v1/email/simple", reason=reason)


@pytest.fixture
def client():
    """MensagiaClient whose HTTP session is replaced by a mock."""
    c = MensagiaClient("token")
    c.session = MagicMock()
    return c


class TestMensagiaClientTransportErrors:
    """Tests that transport failures say whether the request reached the server.

    A failure while opening the connection means the request never left the
    machine, so nothing can have been created on the Mensagia side. A failure
    after the connection was established (no response, connection dropped)
    means the request may have been processed even though no answer arrived.
    """

    @pytest.mark.parametrize("exc", [
        ConnectTimeout(_wrapped(ConnectTimeoutError("connect timed out"))),
        ConnectionError(_wrapped(NewConnectionError(None, "Connection refused"))),
        ConnectionError(_wrapped(NameResolutionError("api.mensagia.com", None, "no DNS"))),
    ], ids=["connect_timeout", "refused", "dns"])
    def test_connection_failures_did_not_reach_server(self, client, exc):
        """Errors raised while opening the connection report reached_server=False."""
        client.session.post.side_effect = exc
        with pytest.raises(MensagiaAPIError) as info:
            client.send_email({})
        assert info.value.reached_server is False
        assert info.value.http_code is None

    @pytest.mark.parametrize("exc", [
        ReadTimeout("read timed out"),
        ConnectionError(ProtocolError("Connection aborted.", RemoteDisconnected("closed"))),
    ], ids=["read_timeout", "aborted_after_send"])
    def test_failures_after_connecting_may_have_reached_server(self, client, exc):
        """Errors raised after the connection was open report reached_server=True."""
        client.session.post.side_effect = exc
        with pytest.raises(MensagiaAPIError) as info:
            client.send_email({})
        assert info.value.reached_server is True
        assert info.value.http_code is None

    def test_get_also_reports_whether_request_reached_server(self, client):
        """GET requests classify transport failures the same way as POST requests."""
        client.session.get.side_effect = ConnectTimeout(_wrapped(ConnectTimeoutError("t")))
        with pytest.raises(MensagiaAPIError) as info:
            client.get_agendas_page()
        assert info.value.reached_server is False

    def test_http_error_response_reached_server(self, client):
        """An error response from the API always reports reached_server=True with its HTTP code."""
        response = MagicMock(ok=False, status_code=422, text="bad")
        response.json.return_value = {"error": {"message": "invalid", "code": "validation"}}
        client.session.post.return_value = response
        with pytest.raises(MensagiaAPIError) as info:
            client.send_email({})
        assert info.value.reached_server is True
        assert info.value.http_code == 422


GENERIC = "The data validation is not correct. See validation_errors array."


def _error_response(error) -> MagicMock:
    """Build a 400 response whose JSON body holds *error* under the 'error' key."""
    response = MagicMock(ok=False, status_code=400, text="raw body")
    response.json.return_value = {"error": error}
    return response


def _raised(client, error) -> MensagiaAPIError:
    """Return the error raised when the API answers a send with *error*."""
    client.session.post.return_value = _error_response(error)
    with pytest.raises(MensagiaAPIError) as info:
        client.send_email({})
    return info.value


class TestMensagiaClientValidationErrors:
    """Covers the detail of validation errors kept from the API response and added to the error text."""

    def test_detail_of_one_field_follows_the_message(self, client):
        """Adds the field and its messages after the generic message."""
        error = _raised(client, {"code": "VALIDATION_FAIL", "message": GENERIC, "http_code": "400",
                                 "validation_errors": {"email": ["First reason.", "Second reason."]}})
        assert str(error) == f"{GENERIC} [email: First reason.; Second reason.]"
        assert error.code == "VALIDATION_FAIL"

    def test_each_field_gets_its_own_detail(self, client):
        """Lists every field with its own messages, in the order of the response."""
        error = _raised(client, {"message": GENERIC, "validation_errors": {
            "email": ["Bad email."], "amount": ["The amount must be a number."]}})
        assert str(error) == f"{GENERIC} [email: Bad email.] [amount: The amount must be a number.]"

    def test_keeps_the_validation_errors(self, client):
        """Keeps the validation errors of the response on the exception."""
        detail = {"email": ["Bad email."]}
        error = _raised(client, {"message": GENERIC, "validation_errors": detail})
        assert error.validation_errors == detail

    def test_a_single_message_instead_of_a_list(self, client):
        """Accepts a field whose messages come as a single text instead of a list."""
        error = _raised(client, {"message": GENERIC, "validation_errors": {"email": "Bad email."}})
        assert str(error) == f"{GENERIC} [email: Bad email.]"

    def test_a_field_without_messages_is_left_out(self, client):
        """Leaves out a field whose list of messages is empty."""
        error = _raised(client, {"message": GENERIC, "validation_errors": {"email": [], "name": ["Too long."]}})
        assert str(error) == f"{GENERIC} [name: Too long.]"

    @pytest.mark.parametrize("detail", [None, {}, [], ["Bad email."], "Bad email.", {"email": []}],
                             ids=["null", "empty", "empty_list", "list", "text", "no_messages"])
    def test_missing_or_unexpected_detail_keeps_the_message(self, client, detail):
        """Shows only the message, without failing, when the detail is missing, empty or not an object."""
        error = _raised(client, {"message": GENERIC, "validation_errors": detail})
        assert str(error) == GENERIC
        assert error.validation_errors is None

    def test_no_detail_in_the_response(self, client):
        """Keeps the message as it is when the response has no validation errors at all."""
        error = _raised(client, {"message": "Unauthorized", "code": "unauthorized"})
        assert str(error) == "Unauthorized"
        assert error.validation_errors is None

    def test_get_requests_also_show_the_detail(self, client):
        """Adds the detail to errors of any call, not only to sends."""
        client.session.get.return_value = _error_response(
            {"message": GENERIC, "validation_errors": {"per_page": ["Too big."]}})
        with pytest.raises(MensagiaAPIError) as info:
            client.get_agendas_page()
        assert str(info.value) == f"{GENERIC} [per_page: Too big.]"

    def test_real_response_for_a_contact_marked_not_valid(self, client):
        """Shows the detail of the answer Mensagia gave for a contact marked as not valid in the agenda."""
        error = _raised(client, {
            "code": "VALIDATION_FAIL",
            "message": GENERIC,
            "http_code": "400",
            "validation_errors": {"to": ["There must be at least one valid recipient to send"]},
        })
        assert str(error) == f"{GENERIC} [to: There must be at least one valid recipient to send]"
