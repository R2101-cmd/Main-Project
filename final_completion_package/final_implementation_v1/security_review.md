# Security and retrieval review

## Implemented protections

- Restricts URLs to HTTP and HTTPS; rejects URL credentials, invalid ports, localhost and non-public IPv4/IPv6 answers.
- Rejects a DNS response if any returned address is not globally routable, including private, loopback, link-local, shared and reserved ranges.
- Resolves immediately before a request and pins the selected validated numeric IP into the urllib3 socket connection. The request still uses the original hostname for HTTP virtual hosting and HTTPS certificate/SNI validation. This closes the DNS validation/request resolution gap for the direct connection path.
- Disables environment-derived proxies for this fetcher so the request cannot silently route through an unvalidated proxy.
- Validates redirect destinations independently and permits at most one redirect. Private/invalid redirects are rejected before connecting.
- Retains streaming response-size limits, timeout, content-type allowlist and no-auth/no-CAPTCHA-bypass behavior; closes response and session resources.

## Tests

`tests/test_url_fetcher.py` covers invalid schemes, credentials, localhost, private IPv4, IPv6 and mapped IPv4, shared address space, DNS failure, private redirect rejection, redirect limit, unsupported types, empty/oversized bodies, environment proxy handling, and a deterministic DNS-answer-change simulation proving that the actual pool receives the single validated numeric address.

## Limits

No claim is made that an external DNS-rebinding exploit was observed. The test demonstrates the TOCTOU mitigation at the transport boundary using a simulated changing DNS answer. The implementation uses urllib3 connection-pool extension points and should be retested when requests/urllib3 versions change. It does not bypass authentication, CAPTCHA, robots controls or other access restrictions.
