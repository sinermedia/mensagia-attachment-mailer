from unittest.mock import patch, MagicMock
from requests.exceptions import ConnectionError, Timeout
from src.infrastructure.http.http_attachment_checker import HttpAttachmentChecker


# Single shared instance — HttpAttachmentChecker is stateless
checker = HttpAttachmentChecker()


def test_returns_true_for_200():
    """Returns True when the server responds with HTTP 200 to a HEAD request."""
    with patch("requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=200)
        assert checker.is_accessible("https://example.com/file.pdf") is True


def test_returns_false_for_404():
    """Returns False when the server responds with HTTP 404 (file not found)."""
    with patch("requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=404)
        assert checker.is_accessible("https://example.com/file.pdf") is False


def test_returns_false_for_403():
    """Returns False when the server responds with HTTP 403 (forbidden)."""
    with patch("requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=403)
        assert checker.is_accessible("https://example.com/file.pdf") is False


def test_falls_back_to_get_on_405():
    """Falls back to a GET request and returns True when HEAD returns 405."""
    mock_get_response = MagicMock(status_code=200)
    mock_get_response.__enter__ = MagicMock(return_value=mock_get_response)
    mock_get_response.__exit__ = MagicMock(return_value=False)
    with patch("requests.head") as mock_head, patch("requests.get") as mock_get:
        mock_head.return_value = MagicMock(status_code=405)
        mock_get.return_value = mock_get_response
        assert checker.is_accessible("https://example.com/file.pdf") is True


def test_returns_false_on_connection_error():
    """Returns False when a network ConnectionError occurs."""
    with patch("requests.head", side_effect=ConnectionError()):
        assert checker.is_accessible("https://example.com/file.pdf") is False


def test_returns_false_on_timeout():
    """Returns False when the request times out."""
    with patch("requests.head", side_effect=Timeout()):
        assert checker.is_accessible("https://example.com/file.pdf") is False


def _get_response(status_code: int) -> MagicMock:
    """Build a streaming GET response usable as a context manager."""
    response = MagicMock(status_code=status_code)
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    return response


class TestTimeoutRetry:
    """Covers the single retry of a check that ran out of time, and that nothing else is retried."""

    def test_retry_after_a_timeout_succeeds(self):
        """Returns True when the check times out and the second attempt gets HTTP 200."""
        with patch("requests.head", side_effect=[Timeout(), MagicMock(status_code=200)]) as mock_head:
            assert checker.is_accessible("https://example.com/file.pdf") is True
        assert mock_head.call_count == 2

    def test_second_timeout_gives_up(self):
        """Returns False after two timeouts, without a third attempt."""
        with patch("requests.head", side_effect=Timeout()) as mock_head:
            assert checker.is_accessible("https://example.com/file.pdf") is False
        assert mock_head.call_count == 2

    def test_retry_answered_with_404_is_not_accessible(self):
        """Returns False when the retry after a timeout gets HTTP 404."""
        with patch("requests.head", side_effect=[Timeout(), MagicMock(status_code=404)]):
            assert checker.is_accessible("https://example.com/file.pdf") is False

    def test_retry_with_a_connection_error_is_not_accessible(self):
        """Returns False when the retry after a timeout fails to connect."""
        with patch("requests.head", side_effect=[Timeout(), ConnectionError()]):
            assert checker.is_accessible("https://example.com/file.pdf") is False

    def test_timeout_of_the_get_fallback_is_retried(self):
        """Retries the whole check when the GET used after a 405 times out."""
        with patch("requests.head", return_value=MagicMock(status_code=405)), \
                patch("requests.get", side_effect=[Timeout(), _get_response(200)]) as mock_get:
            assert checker.is_accessible("https://example.com/file.pdf") is True
        assert mock_get.call_count == 2

    def test_error_status_is_not_retried(self):
        """Checks only once when the server answers with an error status such as 404."""
        with patch("requests.head", return_value=MagicMock(status_code=404)) as mock_head:
            checker.is_accessible("https://example.com/file.pdf")
        assert mock_head.call_count == 1

    def test_connection_error_is_not_retried(self):
        """Checks only once when the connection fails for a reason other than a timeout."""
        with patch("requests.head", side_effect=ConnectionError()) as mock_head:
            checker.is_accessible("https://example.com/file.pdf")
        assert mock_head.call_count == 1
