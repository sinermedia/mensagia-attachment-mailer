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
            client.get_agendas()
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
