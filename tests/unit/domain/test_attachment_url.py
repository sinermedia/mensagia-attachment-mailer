import pytest
from src.domain.attachment_url import resolve_attachment_url


def test_full_https_url_returned_as_is():
    """An absolute HTTPS URL is returned unchanged, with no base URL needed."""
    url = "https://example.com/file.pdf"
    assert resolve_attachment_url(url) == url


def test_full_http_url_returned_as_is():
    """An absolute HTTP URL is returned unchanged, with no base URL needed."""
    url = "http://example.com/file.pdf"
    assert resolve_attachment_url(url) == url


def test_relative_path_combined_with_base_url():
    """A relative filename is joined to the base URL with a single slash separator."""
    result = resolve_attachment_url("file.pdf", "https://example.com/files/")
    assert result == "https://example.com/files/file.pdf"


def test_base_url_without_trailing_slash():
    """A base URL without a trailing slash is still joined correctly."""
    result = resolve_attachment_url("file.pdf", "https://example.com/files")
    assert result == "https://example.com/files/file.pdf"


def test_relative_path_with_leading_slash():
    """A relative path with a leading slash is joined without duplicating the slash."""
    result = resolve_attachment_url("/file.pdf", "https://example.com")
    assert result == "https://example.com/file.pdf"


def test_relative_path_without_base_url_raises():
    """A relative path without any base URL raises ValueError."""
    with pytest.raises(ValueError):
        resolve_attachment_url("file.pdf")


def test_relative_path_with_none_base_url_raises():
    """A relative path with an explicit None base URL raises ValueError."""
    with pytest.raises(ValueError):
        resolve_attachment_url("file.pdf", None)
