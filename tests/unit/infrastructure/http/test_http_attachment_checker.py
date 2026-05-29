from unittest.mock import patch, MagicMock
from requests.exceptions import ConnectionError, Timeout
from src.infrastructure.http.http_attachment_checker import HttpAttachmentChecker


checker = HttpAttachmentChecker()


def test_returns_true_for_200():
    with patch("requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=200)
        assert checker.is_accessible("https://example.com/file.pdf") is True


def test_returns_false_for_404():
    with patch("requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=404)
        assert checker.is_accessible("https://example.com/file.pdf") is False


def test_returns_false_for_403():
    with patch("requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=403)
        assert checker.is_accessible("https://example.com/file.pdf") is False


def test_falls_back_to_get_on_405():
    mock_get_response = MagicMock(status_code=200)
    mock_get_response.__enter__ = MagicMock(return_value=mock_get_response)
    mock_get_response.__exit__ = MagicMock(return_value=False)
    with patch("requests.head") as mock_head, patch("requests.get") as mock_get:
        mock_head.return_value = MagicMock(status_code=405)
        mock_get.return_value = mock_get_response
        assert checker.is_accessible("https://example.com/file.pdf") is True


def test_returns_false_on_connection_error():
    with patch("requests.head", side_effect=ConnectionError()):
        assert checker.is_accessible("https://example.com/file.pdf") is False


def test_returns_false_on_timeout():
    with patch("requests.head", side_effect=Timeout()):
        assert checker.is_accessible("https://example.com/file.pdf") is False
