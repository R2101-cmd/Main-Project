from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from urllib.parse import urlparse
import re

from src.ingestion.content_extractor import ExtractedAdvertisement, extract_text


@dataclass(frozen=True)
class EvidenceObservation:
    source_url: str | None
    source_type: str
    observed_at: str
    retrieval_status: str
    evidence_state: str
    summary: str
    rationale: str
    details: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


_THIRD_PARTY_RECRUITMENT_HOSTS = {
    "greenhouse.io",
    "lever.co",
    "workable.com",
    "ashbyhq.com",
    "indeed.com",
    "linkedin.com",
    "ziprecruiter.com",
}


def _host_is_third_party(host: str) -> bool:
    host = host.lower().split(":", 1)[0].rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in _THIRD_PARTY_RECRUITMENT_HOSTS)


def _source_type(source_url: str, advertisement: ExtractedAdvertisement) -> str:
    host = (urlparse(source_url).hostname or "").lower()
    if _host_is_third_party(host):
        return "third_party_recruitment_platform"
    employer_token = _norm(advertisement.employer)
    host_token = _norm(host.split(".", 1)[0])
    if employer_token and (employer_token in host_token or host_token in employer_token):
        return "employer_controlled_or_employer_named_domain"
    return "public_source_unknown_control"


def _authorization_basis(ad: ExtractedAdvertisement, source_url: str, authorized_domains: set[str] | None) -> str:
    host = (urlparse(source_url).hostname or "").lower().rstrip(".")
    allowed = {item.lower().rstrip(".") for item in (authorized_domains or set())}
    if host in allowed or any(host.endswith("." + domain) for domain in allowed):
        return "verified_source_domain"
    if _host_is_third_party(host):
        return "third_party_recruitment_platform_without_employer_domain_verification"
    employer_token = _norm(ad.employer)
    host_token = _norm(host.split(".", 1)[0])
    if employer_token and (employer_token in host_token or host_token in employer_token):
        return "employer_name_matches_source_domain"
    return "employer_source_relationship_unresolved"


def _compare(ad: ExtractedAdvertisement, candidate: ExtractedAdvertisement, source_url: str, authorized_domains: set[str] | None = None) -> tuple[str, str, dict]:
    checks = {
        "title": bool(ad.title and candidate.title and _norm(ad.title) == _norm(candidate.title)),
        "employer": bool(ad.employer and candidate.employer and _norm(ad.employer) == _norm(candidate.employer)),
        "location": bool(ad.location and candidate.location and _norm(ad.location) == _norm(candidate.location)),
        "application_url": bool(ad.application_url and candidate.application_url and ad.application_url == candidate.application_url),
    }
    matched_fields = [field for field, matched in checks.items() if matched]
    details = {
        "matched_fields": matched_fields,
        "field_matches": checks,
        "vacancy_match": bool(checks["title"] and (checks["employer"] or checks["application_url"] or checks["location"])),
        "source_scope": "public_vacancy_specific",
        "authorization_basis": _authorization_basis(ad, source_url, authorized_domains),
        "evidence_excerpt": candidate.description[:500],
        "evidence_url": source_url,
        "candidate_application_url": candidate.application_url,
        "application_url_match": checks["application_url"],
    }
    if details["vacancy_match"] and details["authorization_basis"] in {"verified_source_domain", "employer_name_matches_source_domain"}:
        return "supported", "The public vacancy-specific source matches these fields: " + ", ".join(matched_fields) + "; its source-domain relationship supports employer authorization.", details
    if details["vacancy_match"]:
        return "unverified", "The source confirms a matching public vacancy, but employer authorization is unresolved because the source-domain relationship is not verified.", details
    contradiction = bool(ad.title and candidate.title and _norm(ad.title) != _norm(candidate.title) and ad.employer and candidate.employer and _norm(ad.employer) == _norm(candidate.employer))
    if contradiction:
        return "contradicted", "The source identifies the same employer but a different role; it does not support authorization of this advertised vacancy.", details
    return "unverified", "The source was retrieved but did not provide enough matching vacancy-specific detail.", details


def collect_vacancy_evidence(advertisement: ExtractedAdvertisement, source_urls: list[str], fetcher, authorized_domains: set[str] | None = None) -> list[dict]:
    """Check explicitly identified public sources; fetcher is injected for deterministic tests.

    This deliberately does not scrape search engines or bypass access controls. Callers can
    supply official careers/recruitment URLs discovered from legitimate public links.
    """
    if not source_urls:
        return [EvidenceObservation(None, "official_source", _now(), "unavailable", "unavailable", "No official public source URL was available to check.", "Employer identity or a public careers URL must be established before vacancy-specific checking.", {}).to_dict()]
    observations: list[dict] = []
    seen: set[str] = set()
    for url in source_urls:
        if not url or url in seen:
            continue
        seen.add(url)
        try:
            page = fetcher(url)
            if not isinstance(page, dict):
                raise ValueError("fetcher returned no page record")
            content_type = str(page.get("content_type") or "").lower()
            final_url = str(page.get("url") or url)
            candidate = extract_text(page.get("content"), is_html="html" in content_type or "xhtml" in content_type)
            source_type = _source_type(final_url, advertisement)
            if not candidate.description.strip():
                observations.append(EvidenceObservation(url, source_type, _now(), "available", "unavailable", "The source was retrieved but no meaningful vacancy content could be extracted.", "Extraction failure is not evidence about authorization.", {"submitted_url": url, "final_url": final_url, "content_type": content_type, "extraction_warnings": candidate.warnings}).to_dict())
                continue
            state, rationale, details = _compare(advertisement, candidate, final_url, authorized_domains)
            details.update({"submitted_url": url, "final_url": final_url, "content_type": content_type, "candidate_warnings": candidate.warnings, "candidate_conflicts": candidate.conflicts})
            observations.append(EvidenceObservation(url, source_type, _now(), "available", state, f"Retrieved source. Compared title, employer, location and application destination: {details}.", rationale, details).to_dict())
        except Exception as exc:  # collector records an honest source-level failure
            observations.append(EvidenceObservation(url, "public_source_unknown_control", _now(), "failed", "unavailable", "The source could not be retrieved.", f"Retrieval failed without asserting anything about authorization: {type(exc).__name__}: {exc}", {"submitted_url": url}).to_dict())
    if not observations:
        observations.append(EvidenceObservation(None, "official_source", _now(), "unavailable", "unavailable", "No source was checked.", "No usable source URL was supplied.", {}).to_dict())
    return observations


def candidate_official_sources(extracted: ExtractedAdvertisement, original_url: str | None = None, explicit_urls: list[str] | None = None) -> list[str]:
    explicit_urls = explicit_urls or []
    candidates = list(explicit_urls)
    if original_url and "linkedin.com" not in urlparse(original_url).netloc.lower():
        candidates.append(original_url)
    candidates.extend(url for url in extracted.candidate_source_urls if _is_specific_job_url(url))
    if extracted.application_url and "linkedin.com" not in urlparse(extracted.application_url).netloc.lower():
        candidates.append(extracted.application_url)
    return list(dict.fromkeys(candidates))


def _is_specific_job_url(url: str) -> bool:
    """Keep likely vacancy URLs; reject generic employer/platform homepages."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or "linkedin.com" in parsed.netloc.lower():
        return False
    path = parsed.path.rstrip("/").lower()
    return any(marker in path for marker in ("/job/", "/jobs/", "/career/", "/careers/", "/vacanc", "/position/", "/requisition/"))
