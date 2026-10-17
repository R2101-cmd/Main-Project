import requests
import pytest

from src.ingestion import url_fetcher
from src.ingestion.url_fetcher import FetchError


class FakeResponse:
    def __init__(self, body=b"<html><main>Job</main></html>", headers=None, status_code=200):
        self.body = body
        self.headers = headers
        self.status_code = status_code
        self.encoding = None

    def iter_content(self, _size):
        yield self.body


def test_missing_response_metadata_is_safe(monkeypatch):
    monkeypatch.setattr(url_fetcher, "validate_public_url", lambda url: url)
    monkeypatch.setattr(url_fetcher.requests, "get", lambda *args, **kwargs: FakeResponse(headers=None))
    page = url_fetcher.fetch_public_page("https://example.com/job")
    assert page["content_type"] == ""
    assert page["content"]


def test_failed_request_becomes_fetch_error(monkeypatch):
    monkeypatch.setattr(url_fetcher, "validate_public_url", lambda url: url)
    def fail(*args, **kwargs):
        raise requests.Timeout("timed out")
    monkeypatch.setattr(url_fetcher.requests, "get", fail)
    with pytest.raises(FetchError, match="retrieval failed"):
        url_fetcher.fetch_public_page("https://example.com/job")


def test_unsupported_content_type_is_rejected(monkeypatch):
    monkeypatch.setattr(url_fetcher, "validate_public_url", lambda url: url)
    monkeypatch.setattr(url_fetcher.requests, "get", lambda *args, **kwargs: FakeResponse(headers={"Content-Type": "application/pdf"}))
    with pytest.raises(FetchError, match="unsupported content type"):
        url_fetcher.fetch_public_page("https://example.com/job")


def test_empty_response_is_rejected(monkeypatch):
    monkeypatch.setattr(url_fetcher, "validate_public_url", lambda url: url)
    monkeypatch.setattr(url_fetcher.requests, "get", lambda *args, **kwargs: FakeResponse(body=b"", headers={}))
    with pytest.raises(FetchError, match="empty response"):
        url_fetcher.fetch_public_page("https://example.com/job")
