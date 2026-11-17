import socket

import pytest
import requests

from src.ingestion import url_fetcher
from src.ingestion.url_fetcher import FetchError, UnsafeURL


class FakeResponse:
    def __init__(self, body=b"<html><main>Job</main></html>", headers=None, status_code=200):
        self.body = body
        self.headers = headers or {}
        self.status_code = status_code
        self.encoding = None
        self.closed = False

    def iter_content(self, _size):
        yield self.body

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def stub_public_dns(monkeypatch):
    monkeypatch.setattr(url_fetcher, "_validated_public_addresses", lambda url: (url, ["93.184.216.34"]))


def test_missing_response_metadata_is_safe(monkeypatch):
    stub_public_dns(monkeypatch)
    response = FakeResponse(headers=None)
    monkeypatch.setattr(url_fetcher, "_pinned_get", lambda url, timeout, *args: (response, FakeSession()))
    page = url_fetcher.fetch_public_page("https://example.com/job")
    assert page["content_type"] == ""
    assert page["content"]
    assert response.closed


def test_failed_request_becomes_fetch_error(monkeypatch):
    stub_public_dns(monkeypatch)
    def fail(*args, **kwargs):
        raise requests.Timeout("timed out")
    monkeypatch.setattr(url_fetcher, "_pinned_get", fail)
    with pytest.raises(FetchError, match="retrieval failed"):
        url_fetcher.fetch_public_page("https://example.com/job")


def test_unsupported_content_type_is_rejected_and_response_closed(monkeypatch):
    stub_public_dns(monkeypatch)
    response = FakeResponse(headers={"Content-Type": "application/pdf"})
    monkeypatch.setattr(url_fetcher, "_pinned_get", lambda url, timeout, *args: (response, FakeSession()))
    with pytest.raises(FetchError, match="unsupported content type"):
        url_fetcher.fetch_public_page("https://example.com/job")
    assert response.closed


def test_empty_response_is_rejected(monkeypatch):
    stub_public_dns(monkeypatch)
    monkeypatch.setattr(url_fetcher, "_pinned_get", lambda url, timeout, *args: (FakeResponse(body=b"", headers={}), FakeSession()))
    with pytest.raises(FetchError, match="empty response"):
        url_fetcher.fetch_public_page("https://example.com/job")


def test_response_size_limit_is_enforced(monkeypatch):
    stub_public_dns(monkeypatch)
    monkeypatch.setattr(url_fetcher, "_pinned_get", lambda url, timeout, *args: (FakeResponse(body=b"123456"), FakeSession()))
    with pytest.raises(FetchError, match="size limit"):
        url_fetcher.fetch_public_page("https://example.com/job", max_bytes=5)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/a", "https://user:pass@example.com/a", "https://example.com:bad/a", "http://localhost/a", "http://127.0.0.1/a", "http://[::1]/a"])
def test_invalid_scheme_credentials_localhost_and_private_ips_are_rejected(url):
    with pytest.raises(UnsafeURL):
        url_fetcher.validate_public_url(url)


@pytest.mark.parametrize("address", ["10.1.2.3", "169.254.1.2", "100.64.0.1", "::", "::1", "fc00::1", "fe80::1", "::ffff:127.0.0.1"])
def test_ipv4_ipv6_and_non_global_dns_answers_are_blocked(monkeypatch, address):
    def fake_getaddrinfo(host, _port):
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        sockaddr = (address, 443, 0, 0) if family == socket.AF_INET6 else (address, 443)
        return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)]
    monkeypatch.setattr(url_fetcher.socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(UnsafeURL, match="non-public"):
        url_fetcher.validate_public_url("https://host.example/job")


def test_dns_resolution_failure_is_rejected(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("no name")
    monkeypatch.setattr(url_fetcher.socket, "getaddrinfo", fail)
    with pytest.raises(UnsafeURL, match="could not be resolved"):
        url_fetcher.validate_public_url("https://missing.example/job")


def test_redirect_to_private_address_is_blocked(monkeypatch):
    calls = []
    def validate(url):
        if "127.0.0.1" in url:
            raise UnsafeURL("private redirect rejected")
        return url, ["93.184.216.34"]
    monkeypatch.setattr(url_fetcher, "_validated_public_addresses", validate)
    response = FakeResponse(headers={"Location": "http://127.0.0.1/admin"}, status_code=302)
    def get(url, timeout, *args):
        calls.append(url)
        return response, FakeSession()
    monkeypatch.setattr(url_fetcher, "_pinned_get", get)
    with pytest.raises(UnsafeURL, match="private redirect"):
        url_fetcher.fetch_public_page("https://example.com/job")
    assert calls == ["https://example.com/job"]
    assert response.closed


def test_second_redirect_is_rejected(monkeypatch):
    stub_public_dns(monkeypatch)
    response = FakeResponse(headers={"Location": "/next"}, status_code=302)
    second = FakeResponse(headers={"Location": "/third"}, status_code=302)
    calls = iter([(response, FakeSession()), (second, FakeSession())])
    monkeypatch.setattr(url_fetcher, "_pinned_get", lambda url, timeout, *args: next(calls))
    with pytest.raises(FetchError, match="more than once"):
        url_fetcher.fetch_public_page("https://example.com/job")
    assert second.closed


def test_connection_uses_validated_pinned_ip_not_hostname(monkeypatch):
    seen = []
    monkeypatch.setattr(url_fetcher.socket, "create_connection", lambda address, timeout=None, source_address=None: seen.append(address) or object())
    conn = url_fetcher._PinnedHTTPSConnection("www.example.com", 443, pinned_address="93.184.216.34")
    conn._new_conn()
    assert seen == [("93.184.216.34", 443)]


def test_pinned_adapter_does_not_use_environment_proxy(monkeypatch):
    monkeypatch.setattr(url_fetcher, "_validated_public_addresses", lambda url: (url, ["93.184.216.34"]))
    captured = {}
    class Session:
        def __init__(self): self.trust_env = True
        def mount(self, prefix, adapter): captured[prefix] = adapter
        def get(self, *args, **kwargs): captured["trust_env"] = self.trust_env; return FakeResponse()
        def close(self): pass
    monkeypatch.setattr(url_fetcher.requests, "Session", Session)
    response, _ = url_fetcher._pinned_get("https://example.com", 3)
    assert response
    assert captured["trust_env"] is False
    assert captured["https://"].pinned_address == "93.184.216.34"


def test_fetch_pins_the_single_validated_dns_answer_into_urllib3_pool(monkeypatch):
    resolved = []
    def resolve(url):
        resolved.append(url)
        # The later answer intentionally differs; a correctly pinned request
        # never asks DNS for the hostname a second time before socket connect.
        answer = "93.184.216.34" if len(resolved) == 1 else "127.0.0.1"
        return url, [answer]
    monkeypatch.setattr(url_fetcher, "_validated_public_addresses", resolve)
    captured = {}
    class Session:
        def __init__(self): self.trust_env = True; self.adapters = {}
        def mount(self, prefix, adapter): self.adapters[prefix] = adapter
        def get(self, url, **kwargs):
            adapter = self.adapters["https://"]
            pool = adapter.poolmanager.connection_from_url(url)
            captured.update({"pool_ip": pool.conn_kw["pinned_address"], "host": pool.host, "trust_env": self.trust_env})
            return FakeResponse()
        def close(self): pass
    monkeypatch.setattr(url_fetcher.requests, "Session", Session)
    page = url_fetcher.fetch_public_page("https://www.example.com/job")
    assert page["status"] == "available"
    assert resolved == ["https://www.example.com/job"]
    assert captured == {"pool_ip": "93.184.216.34", "host": "www.example.com", "trust_env": False}

