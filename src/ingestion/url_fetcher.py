import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3 import PoolManager
from urllib3.poolmanager import key_fn_by_scheme as _pool_key_functions
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3 import HTTPConnectionPool, HTTPSConnectionPool

logger = logging.getLogger(__name__)

class UnsafeURL(ValueError):
    pass

class FetchError(ValueError):
    pass

def _validated_public_addresses(url: str) -> tuple[str, list[str]]:
    if not isinstance(url, str) or not url.strip():
        raise UnsafeURL("a non-empty URL is required")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeURL("only public http and https URLs are supported")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURL("credentials in public URLs are not allowed")
    try:
        parsed.port
    except ValueError as exc:
        raise UnsafeURL("URL contains an invalid port") from exc
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"}:
        raise UnsafeURL("localhost is not allowed")
    try:
        addresses = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeURL("hostname could not be resolved") from exc
    public_addresses = []
    for item in addresses:
        address = ipaddress.ip_address(item[4][0].split("%", 1)[0])
        if not address.is_global:
            raise UnsafeURL("private or non-public destination is not allowed")
        canonical = str(address)
        if canonical not in public_addresses:
            public_addresses.append(canonical)
    if not public_addresses:
        raise UnsafeURL("hostname did not resolve to a public address")
    return url, public_addresses


def validate_public_url(url: str) -> str:
    return _validated_public_addresses(url)[0]


class _PinnedHTTPConnection(HTTPConnection):
    def __init__(self, *args, pinned_address: str, **kwargs):
        self._pinned_address = pinned_address
        super().__init__(*args, **kwargs)

    def _new_conn(self):
        # Connect to the IP validated immediately before the request. HTTP Host
        # and HTTPS SNI still use self.host, preserving normal virtual hosting.
        return socket.create_connection((self._pinned_address, self.port), self.timeout, self.source_address)


class _PinnedHTTPSConnection(HTTPSConnection):
    def __init__(self, *args, pinned_address: str, **kwargs):
        self._pinned_address = pinned_address
        super().__init__(*args, **kwargs)

    def _new_conn(self):
        return socket.create_connection((self._pinned_address, self.port), self.timeout, self.source_address)


class _PinnedHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = _PinnedHTTPConnection


class _PinnedHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = _PinnedHTTPSConnection


class _PinnedPoolManager(PoolManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pool_classes_by_scheme = {"http": _PinnedHTTPConnectionPool, "https": _PinnedHTTPSConnectionPool}
        self.key_fn_by_scheme = {
            scheme: (lambda base: lambda context: base({key: value for key, value in context.items() if key != "pinned_address"}))(base)
            for scheme, base in _pool_key_functions.items()
        }


class _PinnedHTTPAdapter(HTTPAdapter):
    def __init__(self, pinned_address: str):
        self.pinned_address = pinned_address
        super().__init__(max_retries=0)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block
        self.poolmanager = _PinnedPoolManager(num_pools=connections, maxsize=maxsize, block=block, pinned_address=self.pinned_address, **pool_kwargs)


def _pinned_get(url: str, timeout: float, pinned_address: str | None = None):
    if pinned_address is None:
        _, addresses = _validated_public_addresses(url)
        pinned_address = addresses[0]
    session = requests.Session()
    session.trust_env = False  # avoid unvalidated environment proxies
    session.mount("http://", _PinnedHTTPAdapter(pinned_address))
    session.mount("https://", _PinnedHTTPAdapter(pinned_address))
    response = session.get(url, timeout=timeout, stream=True, headers={"User-Agent": "VacancyVerificationResearch/0.1"}, allow_redirects=False)
    return response, session


def _read_response(response, current: str, status_code: int, max_bytes: int) -> dict:
    headers = getattr(response, "headers", None) or {}
    content_type = str(headers.get("Content-Type") or "")
    media_type = content_type.split(";", 1)[0].strip().lower()
    allowed_types = {"", "text/html", "application/xhtml+xml", "text/plain"}
    if media_type not in allowed_types:
        raise FetchError(f"unsupported content type: {media_type}")
    chunks, size = [], 0
    iterator = getattr(response, "iter_content", None)
    if not callable(iterator):
        raise FetchError("the response did not provide readable content")
    for chunk in iterator(8192):
        if not chunk:
            continue
        size += len(chunk)
        if size > max_bytes:
            raise FetchError("response exceeds configured size limit")
        chunks.append(chunk)
    if not chunks:
        raise FetchError("the public page returned an empty response")
    encoding = getattr(response, "encoding", None) or "utf-8"
    return {"url": current, "status": "available", "http_status": status_code, "content_type": content_type, "content": b"".join(chunks).decode(encoding, errors="replace")}

def fetch_public_page(url: str, timeout: float = 10, max_bytes: int = 2_000_000) -> dict:
    current, addresses = _validated_public_addresses(url)
    response = None
    session = None
    try:
        response, session = _pinned_get(current, timeout, addresses[0])
        headers = getattr(response, "headers", None) or {}
        status_code = getattr(response, "status_code", None)
        if not isinstance(status_code, int):
            raise FetchError("the response did not include a valid HTTP status")
        if 300 <= status_code < 400:
            location = headers.get("Location")
            if not location:
                raise FetchError("the server returned a redirect without a destination")
            close = getattr(response, "close", None)
            if callable(close): close()
            if session is not None: session.close()
            current, redirect_addresses = _validated_public_addresses(urljoin(current, location))
            response, session = _pinned_get(current, timeout, redirect_addresses[0])
            headers = getattr(response, "headers", None) or {}
            status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int) and 300 <= status_code < 400:
            raise FetchError("the public page redirected more than once")
        if not isinstance(status_code, int) or status_code < 200 or status_code >= 300:
            raise FetchError(f"the public page returned HTTP status {status_code}")
    except requests.RequestException as exc:
        logger.warning("Public page retrieval failed for %s: %s", current, exc)
        if response is not None:
            close = getattr(response, "close", None)
            if callable(close): close()
        if session is not None: session.close()
        raise FetchError(f"public page retrieval failed: {exc}") from exc
    except Exception:
        if response is not None:
            close = getattr(response, "close", None)
            if callable(close): close()
        if session is not None: session.close()
        raise
    try:
        return _read_response(response, current, status_code, max_bytes)
    finally:
        close = getattr(response, "close", None)
        if callable(close): close()
        if session is not None: session.close()
