import pytest
from src.domain.attachment_url import resolve_attachment_url


def test_full_https_url_returned_as_is():
    url = "https://example.com/file.pdf"
    assert resolve_attachment_url(url) == url


def test_full_http_url_returned_as_is():
    url = "http://example.com/file.pdf"
    assert resolve_attachment_url(url) == url


def test_relative_path_combined_with_base_url():
    result = resolve_attachment_url("file.pdf", "https://example.com/files/")
    assert result == "https://example.com/files/file.pdf"


def test_base_url_without_trailing_slash():
    result = resolve_attachment_url("file.pdf", "https://example.com/files")
    assert result == "https://example.com/files/file.pdf"


def test_relative_path_with_leading_slash():
    result = resolve_attachment_url("/file.pdf", "https://example.com")
    assert result == "https://example.com/file.pdf"


def test_relative_path_without_base_url_raises():
    with pytest.raises(ValueError):
        resolve_attachment_url("file.pdf")


def test_relative_path_with_none_base_url_raises():
    with pytest.raises(ValueError):
        resolve_attachment_url("file.pdf", None)
