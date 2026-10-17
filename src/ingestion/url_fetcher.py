import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlparse
import requests

logger = logging.getLogger(__name__)

class UnsafeURL(ValueError):
    pass

class FetchError(ValueError):
    pass

def validate_public_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise UnsafeURL("a non-empty URL is required")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeURL("only public http and https URLs are supported")
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"}:
        raise UnsafeURL("localhost is not allowed")
    try:
        addresses = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeURL("hostname could not be resolved") from exc
    for item in addresses:
        address = ipaddress.ip_address(item[4][0])
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast:
            raise UnsafeURL("private or non-public destination is not allowed")
    return url

def fetch_public_page(url: str, timeout: float = 10, max_bytes: int = 2_000_000) -> dict:
    current = validate_public_url(url)
    try:
        response = requests.get(current, timeout=timeout, stream=True, headers={"User-Agent": "VacancyVerificationResearch/0.1"}, allow_redirects=False)
        headers = getattr(response, "headers", None) or {}
        status_code = getattr(response, "status_code", None)
        if not isinstance(status_code, int):
            raise FetchError("the response did not include a valid HTTP status")
        if 300 <= status_code < 400:
            location = headers.get("Location")
            if not location:
                raise FetchError("the server returned a redirect without a destination")
            current = validate_public_url(urljoin(current, location))
            response = requests.get(current, timeout=timeout, stream=True, headers={"User-Agent": "VacancyVerificationResearch/0.1"}, allow_redirects=False)
            headers = getattr(response, "headers", None) or {}
            status_code = getattr(response, "status_code", None)
        if not isinstance(status_code, int) or status_code < 200 or status_code >= 400:
            raise FetchError(f"the public page returned HTTP status {status_code}")
    except requests.RequestException as exc:
        logger.warning("Public page retrieval failed for %s: %s", current, exc)
        raise FetchError(f"public page retrieval failed: {exc}") from exc
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
    return {"url": current, "status": "available", "content_type": content_type, "content": b"".join(chunks).decode(encoding, errors="replace")}
