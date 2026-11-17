from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from difflib import SequenceMatcher
import re
from uuid import uuid4

from src.ingestion.content_extractor import ExtractedAdvertisement, extract_text
from src.lineage.similarity import compare as compare_lineage_text, candidate_relationship


VERIFICATION_STATES = {
    "independently_supported",
    "independently_contradicted",
    "independently_unresolved",
    "inaccessible",
    "not_comparable",
    "snapshot_match_only",
}

EMPLOYER_RELATIONSHIPS = {
    "employer_owned_official",
    "verified_employer_associated_ats",
    "unverified_ats",
    "third_party_portal",
    "unverified_recruiter_page",
    "reposted_advertisement",
    "archived_or_historical_snapshot",
    "unknown",
}


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
    verification_status: str = "independently_unresolved"
    employer_relationship: str = "unknown"
    evidence_id: str = field(default_factory=lambda: uuid4().hex)
    source_family: str = "unknown"
    source_published_at: str | None = None
    source_modified_at: str | None = None
    source_relationship: str = "unknown"
    lineage_group_id: str | None = None
    lineage_status: str = "not_assessed"
    lineage_review_status: str = "not_assessed"
    lineage_provenance: str = "No adjudicated relationship is available; similarity is candidate-only."

    def to_dict(self) -> dict:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _norm_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (value or "").lower())).strip()


def _sim(a: str | None, b: str | None) -> float:
    a, b = _norm_text(a), _norm_text(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _canon_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return url.rstrip("/")
    path = re.sub(r"/+", "/", p.path or "/").rstrip("/") or "/"
    # Preserve query parameters that identify a vacancy. Dropping the whole
    # query made /careers/search?gh_jid=A and ?gh_jid=B compare as the same job.
    vacancy_keys = {"gh_jid", "job_id", "jobid", "req", "reqid", "requisitionid", "positionid", "id"}
    stable_query = sorted(
        (key, value) for key, value in parse_qsl(p.query, keep_blank_values=False)
        if key.lower() in vacancy_keys
    )
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", urlencode(stable_query), ""))


_THIRD_PARTY_RECRUITMENT_HOSTS = {
    "greenhouse.io", "lever.co", "workable.com", "ashbyhq.com", "smartrecruiters.com",
    "myworkdayjobs.com", "workday.com", "indeed.com", "linkedin.com", "ziprecruiter.com",
    "glassdoor.com", "naukri.com", "monster.com", "foundit.in", "dice.com",
}
_ARCHIVE_HOSTS = {"web.archive.org", "archive.today", "archive.ph"}
_KNOWN_ATS_HOSTS = {
    "greenhouse.io", "lever.co", "workable.com", "ashbyhq.com", "smartrecruiters.com",
    "myworkdayjobs.com", "workday.com", "icims.com", "jobvite.com", "taleo.net",
}
MAX_CURRENT_POSTING_AGE_DAYS = 180


def _host(url: str | None) -> str:
    return (urlparse(url or "").hostname or "").lower().rstrip(".")


def _host_matches(host: str, domains: set[str]) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def _host_is_third_party(host: str) -> bool:
    return _host_matches(host, _THIRD_PARTY_RECRUITMENT_HOSTS)


def _mapping_matches_url(source_url: str, mapping: dict) -> bool:
    host = _host(source_url)
    domain = str(mapping.get("authorized_domain", "")).lower().rstrip(".")
    if not domain or not _host_matches(host, {domain}):
        return False
    prefix = mapping.get("authorized_path_prefix")
    if mapping.get("relationship_type") == "verified_employer_associated_ats":
        if not isinstance(prefix, str) or not prefix.startswith("/"):
            return False
    return not prefix or urlparse(source_url).path.lower().startswith(str(prefix).lower())


def _authority_assessment(source_url: str, advertisement: ExtractedAdvertisement, authorized_domains: set[str] | None = None, authority_mappings: list[dict] | None = None) -> dict:
    host = _host(source_url)
    allowed = {d.lower().rstrip(".") for d in (authorized_domains or set())}
    archived = _host_matches(host, _ARCHIVE_HOSTS)
    is_ats = _host_matches(host, _KNOWN_ATS_HOSTS)
    matching_mappings = [m for m in (authority_mappings or []) if _mapping_matches_url(source_url, m)]
    mapped_relationships = {m.get("relationship_type") for m in matching_mappings if m.get("verification_status") == "verified"}
    legacy_allowed = bool(allowed and _host_matches(host, allowed) and authority_mappings is None)
    is_verified_ats = bool(allowed and _host_matches(host, allowed) and ((is_ats and legacy_allowed) or "verified_employer_associated_ats" in mapped_relationships))
    is_employer_official = bool(allowed and _host_matches(host, allowed) and not is_ats and ("employer_owned_official" in mapped_relationships or legacy_allowed))
    if archived:
        return {
            "employer_relationship": "archived_or_historical_snapshot",
            "authority_level": "archived_snapshot",
            "source_type": "archived_snapshot",
            "snapshot_only": True,
            "explanation": "Source is an archive/snapshot host; evidence is historical snapshot context, not current independent authorization.",
        }
    if is_verified_ats:
        return {
            "employer_relationship": "verified_employer_associated_ats",
            "authority_level": "employer_authoritative",
            "source_type": "verified_employer_associated_ats",
            "snapshot_only": False,
            "explanation": "ATS host is in verified employer-associated domains.",
        }
    if is_employer_official:
        return {
            "employer_relationship": "employer_owned_official",
            "authority_level": "employer_authoritative",
            "source_type": "employer_official_career_page",
            "snapshot_only": False,
            "explanation": "Source domain is explicitly authorized as employer-owned/official.",
        }
    if is_ats:
        return {
            "employer_relationship": "unverified_ats",
            "authority_level": "unverified",
            "source_type": "ats_platform_unverified_employer_relationship",
            "snapshot_only": False,
            "explanation": "ATS platform detected but employer relationship is not verified; cannot be treated as employer-authoritative automatically.",
        }
    if _host_matches(host, {"indeed.com", "linkedin.com", "ziprecruiter.com", "glassdoor.com", "naukri.com", "monster.com", "foundit.in", "dice.com"}):
        return {
            "employer_relationship": "third_party_portal",
            "authority_level": "third_party",
            "source_type": "third_party_recruitment_platform",
            "snapshot_only": False,
            "explanation": "Third-party job portal/repost source; not employer-authoritative by itself.",
        }
    if "recruit" in (source_url or "").lower():
        return {
            "employer_relationship": "unverified_recruiter_page",
            "authority_level": "unverified",
            "source_type": "unverified_recruiter_page",
            "snapshot_only": False,
            "explanation": "Recruiter-related source without verified employer relationship.",
        }
    return {
        "employer_relationship": "reposted_advertisement" if _host_is_third_party(host) else "unverified_recruiter_page",
        "authority_level": "unverified",
        "source_type": "unverified_source",
        "snapshot_only": False,
        "explanation": "Source authority/employer relationship could not be verified from available information.",
    }


def _parse_date(value: str | None):
    if not value:
        return None
    v = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(v.replace("Z", "+00:00") if fmt.endswith("%z") else v, fmt)
        except Exception:
            continue
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", v)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d")
        except Exception:
            return None
    return None


def _freshness(ad: ExtractedAdvertisement, candidate: ExtractedAdvertisement, max_age_days: int = MAX_CURRENT_POSTING_AGE_DAYS) -> dict:
    today = datetime.now(timezone.utc).date()
    source_date_values = [candidate.valid_through, candidate.date_posted or candidate.posting_date, candidate.date_modified]
    if any(value and _parse_date(value) is None for value in source_date_values):
        invalid = next(value for value in source_date_values if value and _parse_date(value) is None)
        return {"status": "unresolved", "basis": "invalid_source_date", "value": invalid, "age_days": None, "explanation": "A source date could not be parsed reliably."}
    expiry_value = candidate.valid_through
    expiry = _parse_date(expiry_value)
    if expiry and expiry.date() < today:
        return {"status": "stale", "basis": "valid_through", "value": expiry_value, "age_days": (today-expiry.date()).days, "explanation": "The source's stated validity date has passed."}
    posted_value = candidate.date_posted or candidate.posting_date
    modified_value = candidate.date_modified
    posted = _parse_date(posted_value)
    modified = _parse_date(modified_value)
    if posted and posted.date() > today or modified and modified.date() > today:
        return {"status": "unresolved", "basis": "future_source_date", "value": modified_value if modified and modified.date() > today else posted_value, "age_days": None, "explanation": "A source date is in the future, so freshness cannot be established."}
    selected = modified if modified and (not posted or modified.date() >= posted.date()) else posted
    basis = "date_modified" if selected is modified and modified else "date_posted"
    raw = modified_value if basis == "date_modified" else posted_value
    if selected is None:
        has_raw_date = any((candidate.date_posted, candidate.date_modified, candidate.valid_through, candidate.posting_date))
        return {"status": "unresolved" if has_raw_date else "unknown", "basis": "invalid_source_date" if has_raw_date else "missing_source_date", "value": raw, "age_days": None, "explanation": "A reliable source publication/modification date is unavailable."}
    age = (today-selected.date()).days
    if age < 0:
        return {"status": "unresolved", "basis": basis, "value": raw, "age_days": age, "explanation": "A source date is in the future, so freshness cannot be established."}
    if age > max_age_days:
        return {"status": "stale", "basis": basis, "value": raw, "age_days": age, "explanation": f"The latest reliable posting/modification date is older than the configured {max_age_days}-day policy window."}
    return {"status": "current", "basis": basis, "value": raw, "age_days": age, "explanation": f"The latest reliable source date is within the configured {max_age_days}-day policy window."}


def _source_family(url: str | None) -> str:
    return _host(url) or "unknown"


def _salary_conflict(left: str | None, right: str | None) -> bool | None:
    """Compare salary only when currency and pay period are explicit/comparable."""
    if not left or not right:
        return None
    def parse(value: str):
        text = value.lower().replace(",", "")
        currency = "INR" if any(x in text for x in ("₹", "inr", " rs", "rupee")) else "USD" if any(x in text for x in ("$", "usd", "dollar")) else "EUR" if any(x in text for x in ("€", "eur")) else None
        period = "annual" if any(x in text for x in ("annual", "annum", "year", "lpa")) else "monthly" if any(x in text for x in ("month", "monthly", "per mo")) else "hourly" if any(x in text for x in ("hour", "hourly", "/hr")) else None
        nums = re.findall(r"\d+(?:\.\d+)?", text)
        if not currency or not period or len(nums) != 1:
            return None
        amount = float(nums[0])
        if "lpa" in text or "lakh" in text:
            amount *= 100000
        elif "k" in text:
            amount *= 1000
        return currency, period, amount
    a, b = parse(left), parse(right)
    if not a or not b or a[:2] != b[:2]:
        return None
    return abs(a[2]-b[2]) > max(1.0, max(a[2], b[2]) * .02)


def _field_status(name: str, adv: str | None, src: str | None, *, exact: bool = False, similarity: float | None = None, sim_threshold: float = 0.86, conflict: bool = False, note: str = "") -> dict:
    status = "unknown"
    matched = False
    if conflict:
        status = "conflict"
    elif adv and src:
        if exact or (adv.strip().lower() == src.strip().lower()):
            status = "exact_match"
            matched = True
        elif similarity is not None and similarity >= sim_threshold:
            status = "similar_match"
            matched = True
        else:
            status = "mismatch"
    elif adv and not src:
        status = "missing_in_source"
    elif src and not adv:
        status = "missing_in_advertisement"
    else:
        status = "not_comparable"
    return {"field": name, "advertised": adv, "observed": src, "status": status, "matched": matched, "similarity": similarity, "note": note}


def _compare(ad: ExtractedAdvertisement, candidate: ExtractedAdvertisement, source_url: str, authorized_domains: set[str] | None = None, authority_mappings: list[dict] | None = None, max_current_posting_age_days: int = MAX_CURRENT_POSTING_AGE_DAYS) -> tuple[str, str, str, dict]:
    auth = _authority_assessment(source_url, ad, authorized_domains, authority_mappings)
    # field comparisons
    title_sim = _sim(ad.title, candidate.title)
    desc_sim = _sim((ad.description or "")[:2000], (candidate.description or "")[:2000])
    emp_sim = _sim(ad.employer, candidate.employer)
    loc_sim = _sim(ad.location, candidate.location)
    ad_url = _canon_url(ad.application_url)
    src_url = _canon_url(candidate.application_url)
    ad_id = (ad.job_id or "").strip()
    src_id = (candidate.job_id or "").strip()
    id_conflict = bool(ad_id and src_id and ad_id.lower() != src_id.lower())
    url_conflict = bool(ad_url and src_url and ad_url != src_url)
    title_conflict = bool(ad.title and candidate.title and title_sim < 0.55 and _sim(ad.employer, candidate.employer) >= 0.85)
    ad_date = _parse_date(ad.date_posted or ad.posting_date)
    src_date = _parse_date(candidate.date_posted or candidate.posting_date)
    date_note = "not_comparable"
    date_conflict = False
    if ad_date and src_date:
        delta = abs((ad_date.date() - src_date.date()).days)
        date_conflict = delta > 45
        date_note = f"delta_days={delta}"
    elif ad.posting_date and candidate.posting_date:
        date_note = "unparsed_dates"
    rec_match = bool(ad.recruiter and candidate.recruiter and (_norm(ad.recruiter) == _norm(candidate.recruiter) or _sim(ad.recruiter, candidate.recruiter) >= 0.9))
    salary_sim = _sim(ad.salary, candidate.salary)
    salary_disagrees = _salary_conflict(ad.salary, candidate.salary)
    employment_sim = _sim(ad.employment_type, candidate.employment_type)

    fields = {
        "employer_identity": _field_status("employer_identity", ad.employer, candidate.employer, exact=_norm(ad.employer)==_norm(candidate.employer) and bool(ad.employer), similarity=emp_sim, sim_threshold=0.9),
        "job_title": _field_status("job_title", ad.title, candidate.title, exact=_norm(ad.title)==_norm(candidate.title) and bool(ad.title), similarity=title_sim, sim_threshold=0.88, conflict=title_conflict),
        "job_description": _field_status("job_description", (ad.description or "")[:300], (candidate.description or "")[:300], similarity=desc_sim, sim_threshold=0.75, note=f"similarity={desc_sim:.3f}"),
        "salary": _field_status("salary", ad.salary, candidate.salary, exact=_norm(ad.salary)==_norm(candidate.salary) and bool(ad.salary), similarity=salary_sim, sim_threshold=0.9, conflict=salary_disagrees is True, note="Amounts are compared only when currency and pay period are explicit and comparable."),
        "employment_type": _field_status("employment_type", ad.employment_type, candidate.employment_type, exact=_norm(ad.employment_type)==_norm(candidate.employment_type) and bool(ad.employment_type), similarity=employment_sim, sim_threshold=0.9),
        "job_id": _field_status("job_id", ad.job_id, candidate.job_id, exact=bool(ad_id and src_id and ad_id.lower()==src_id.lower()), conflict=id_conflict),
        "location": _field_status("location", ad.location, candidate.location, exact=_norm(ad.location)==_norm(candidate.location) and bool(ad.location), similarity=loc_sim, sim_threshold=0.86),
        "application_url": _field_status("application_url", ad.application_url, candidate.application_url, exact=bool(ad_url and src_url and ad_url==src_url), conflict=url_conflict),
        "posting_date": _field_status("posting_date", ad.date_posted or ad.posting_date, candidate.date_posted or candidate.posting_date, exact=bool(ad_date and src_date and ad_date.date()==src_date.date()), conflict=date_conflict, note=date_note),
        "recruiter_contact": _field_status("recruiter_contact", ad.recruiter or ad.contact, candidate.recruiter or candidate.contact, exact=rec_match, similarity=_sim(ad.recruiter or ad.contact, candidate.recruiter or candidate.contact), sim_threshold=0.9),
    }
    if ad.salary and candidate.salary and salary_disagrees is None and _norm(ad.salary) != _norm(candidate.salary):
        fields["salary"].update({"status": "not_comparable", "matched": False, "note": "Currency or pay period is missing or inconsistent; no salary contradiction is inferred."})
    elif salary_disagrees is False and ad.salary and candidate.salary:
        fields["salary"].update({"status": "similar_match", "matched": True, "note": "Comparable currency and pay period; normalized amounts are within 2%."})
    normalized_source_description = _norm_text(candidate.description)
    metadata_words = {"title", "role", "position", "company", "employer", "organization", "location", "based", "in", "job", "id", "requisition", "req", "posted", "published", "date", "salary", "pay", "compensation", "employment", "type", "apply", "application", "full", "time", "contract"}
    substantive_words = [word for word in normalized_source_description.split() if word not in metadata_words and word not in {"the", "and", "for", "with", "from", "this", "that", "are", "will", "our", "you", "your"}]
    substantive_desc = len(normalized_source_description) >= 55 and len(set(substantive_words)) >= 6 and normalized_source_description != _norm_text(candidate.title)
    matched_fields_internal = [name for name, f in fields.items() if f["matched"]]
    legacy_map = {"job_title": "title", "employer_identity": "employer", "location": "location", "application_url": "application_url"}
    matched_fields = [legacy_map[n] for n in ["job_title", "employer_identity", "location", "application_url"] if fields[n]["matched"]]
    contradicted_fields = [name for name, f in fields.items() if f["status"] in {"conflict", "mismatch"} and f.get("advertised") and f.get("observed") and name in {"job_id", "application_url", "job_title", "employer_identity", "posting_date"}]
    unknown_fields = [name for name, f in fields.items() if f["status"] in {"unknown", "not_comparable", "missing_in_source", "missing_in_advertisement"}]

    strong_identity = fields["job_id"]["status"] == "exact_match" or (fields["application_url"]["status"] == "exact_match")
    title_ok = fields["job_title"]["status"] in {"exact_match", "similar_match"}
    employer_ok = fields["employer_identity"]["status"] in {"exact_match", "similar_match"}
    employer_bad = fields["employer_identity"]["status"] in {"mismatch", "conflict"}
    location_ok = fields["location"]["status"] in {"exact_match", "similar_match"}
    # avoid treating trivial/echo descriptions as corroborating evidence
    desc_ok = substantive_desc and fields["job_description"]["status"] in {"exact_match", "similar_match"}
    # vacancy correspondence requires more than title alone and must not ignore clear employer mismatch
    employment_mismatch = fields["employment_type"]["status"] in {"mismatch", "conflict"}
    location_mismatch = fields["location"]["status"] in {"mismatch", "conflict"}
    salary_mismatch = fields["salary"]["status"] == "conflict"
    title_mismatch = fields["job_title"]["status"] in {"mismatch", "conflict"}
    description_conflict = bool(substantive_desc and len(_norm_text(ad.description)) >= 55 and desc_sim < 0.30)
    material_conflicts = [name for name, found in (("job_id", id_conflict), ("application_url", url_conflict), ("job_title", title_mismatch), ("job_description", description_conflict), ("location", location_mismatch), ("employment_type", employment_mismatch), ("salary", salary_mismatch), ("posting_date", date_conflict)) if found]
    vacancy_correspondence = (strong_identity and not employer_bad and not id_conflict) or (title_ok and desc_ok and (employer_ok or (location_ok and not employer_bad)) and not employer_bad and not material_conflicts)
    if title_ok and not (strong_identity or employer_ok or location_ok or desc_ok):
        vacancy_correspondence = False
    strong_contradiction = bool(strong_identity and not id_conflict and (employer_bad or title_mismatch or location_mismatch or employment_mismatch))
    comparable = any(f["status"] not in {"not_comparable", "missing_in_source", "missing_in_advertisement", "unknown"} for f in fields.values())

    authoritative = auth["authority_level"] == "employer_authoritative" and not auth.get("snapshot_only")
    employer_match = fields["employer_identity"]["status"] in {"exact_match", "similar_match"}
    employer_conflict = fields["employer_identity"]["status"] in {"mismatch", "conflict"}
    identity_status = "verified" if authoritative and employer_match else "contradicted" if authoritative and employer_conflict else "unresolved"
    identity_explanation = ("Employer name matches on an explicitly employer-authorized domain." if identity_status == "verified" else "Employer name conflicts with an explicitly employer-authorized domain." if identity_status == "contradicted" else "Employer identity relationship could not be independently established.")
    freshness = _freshness(ad, candidate, max_current_posting_age_days)
    stale = freshness["status"] == "stale"
    if auth.get("snapshot_only"):
        verification_status = "snapshot_match_only"
        evidence_state = "unverified"  # backward-compatible: snapshot is not independent support
        rationale = "Source is an archived/historical snapshot; it can inform context but must remain distinct from independent authorization evidence."
    elif freshness["status"] in {"stale", "unresolved", "unknown"}:
        verification_status = "independently_unresolved"
        evidence_state = "unverified"
        rationale = freshness["explanation"] + " Historical matching alone does not establish current authorization."
    elif not comparable:
        verification_status = "not_comparable"
        evidence_state = "unverified"
        rationale = "Retrieved source did not provide comparable vacancy attributes for a reliable determination."
    elif strong_contradiction and authoritative and employer_match:
        verification_status = "independently_contradicted"
        evidence_state = "contradicted"
        rationale = "Comparable fields conflict with the advertised vacancy on a verified employer-authoritative source."
    elif strong_contradiction:
        verification_status = "independently_unresolved"
        evidence_state = "unverified"
        rationale = "Comparable fields conflict, but the source does not establish an authoritative employer relationship and identity. The difference is not by itself proof of fraud."
    elif material_conflicts:
        verification_status = "independently_unresolved"
        evidence_state = "unverified"
        rationale = "Material vacancy-field differences prevent treating the records as the same vacancy: " + ", ".join(material_conflicts) + ". The differences are not by themselves proof of fraud."
    elif vacancy_correspondence and authoritative and employer_match and title_ok:
        verification_status = "independently_supported"
        evidence_state = "supported"
        rationale = "Vacancy attributes correspond, the extracted employer and title match, and the source is employer-authoritative (non-snapshot)."
    elif vacancy_correspondence:
        verification_status = "independently_unresolved"
        evidence_state = "unverified"
        rationale = "Vacancy attributes correspond, but employer/source authority or independence is not sufficiently established; authorization is unresolved."
    else:
        verification_status = "independently_unresolved"
        evidence_state = "unverified"
        rationale = "Evidence is insufficient to support or contradict this specific vacancy authorization."

    explanation = {
        "vacancy_correspondence": vacancy_correspondence,
        "strong_identity_match": strong_identity,
        "authoritative_source": authoritative,
        "employer_identity_status": identity_status,
        "employer_identity_explanation": identity_explanation,
        "vacancy_authorization_status": verification_status,
        "stale_evidence": stale,
        "freshness": freshness,
        "strong_contradiction": strong_contradiction,
        "material_conflicts": material_conflicts,
        "title_similarity": round(title_sim, 4),
        "description_similarity": round(desc_sim, 4),
        "authority": auth,
        "note": "Title similarity alone is not sufficient for authorization support."
    }
    legacy_rev = {"title":"job_title","employer":"employer_identity","location":"location","application_url":"application_url"}
    contradicted_legacy = [f for f in ["title","employer","location","application_url"] if fields[legacy_rev[f]]["status"] == "conflict"]
    details = {
        "field_comparisons": fields,
        "matched_fields": matched_fields,
        "matched_fields_all": matched_fields_internal,
        "contradicted_fields": contradicted_legacy,
        "contradicted_fields_all": contradicted_fields,
        "unknown_fields": unknown_fields,
        "advertised_values": {"title": ad.title, "employer": ad.employer, "location": ad.location, "application_url": ad.application_url, "job_id": ad.job_id, "posting_date": ad.date_posted or ad.posting_date, "date_posted": ad.date_posted, "date_modified": ad.date_modified, "valid_through": ad.valid_through, "recruiter": ad.recruiter or ad.contact, "salary": ad.salary, "employment_type": ad.employment_type},
        "evidence_values": {"title": candidate.title, "employer": candidate.employer, "location": candidate.location, "application_url": candidate.application_url, "job_id": candidate.job_id, "posting_date": candidate.date_posted or candidate.posting_date, "date_posted": candidate.date_posted, "date_modified": candidate.date_modified, "valid_through": candidate.valid_through, "recruiter": candidate.recruiter or candidate.contact, "salary": candidate.salary, "employment_type": candidate.employment_type},
        "vacancy_match": vacancy_correspondence,
        "source_scope": "public_vacancy_specific",
        "authorization_basis": "verified_employer_relationship" if authoritative else ("archived_snapshot" if auth.get("snapshot_only") else "employer_source_relationship_unresolved"),
        "employer_relationship": auth["employer_relationship"],
        "authority_assessment": auth,
        "evidence_excerpt": (candidate.description or "")[:500],
        "evidence_url": source_url,
        "candidate_application_url": candidate.application_url,
        "application_url_match": fields["application_url"]["matched"],
        "job_id_match": fields["job_id"]["matched"],
        "verification_status": verification_status,
        "matching_explanation": explanation,
    }
    summary = f"Compared employer, title, description, job ID, location, application URL, posting date, recruiter/contact. Verification status: {verification_status}."
    return evidence_state, verification_status, summary, {**details, "rationale_detail": rationale}


def collect_vacancy_evidence(advertisement: ExtractedAdvertisement, source_urls: list[str], fetcher, authorized_domains: set[str] | None = None, authority_mappings: list[dict] | None = None, max_current_posting_age_days: int = MAX_CURRENT_POSTING_AGE_DAYS) -> list[dict]:
    """Check explicitly identified public sources; fetcher is injected for deterministic tests.

    Preserves provenance and records failures/inaccessible sources without asserting fraud.
    """
    if not source_urls:
        obs = EvidenceObservation(None, "official_source", _now(), "unavailable", "unavailable", "No official public source URL was available to check.", "Employer identity or a public careers URL must be established before vacancy-specific checking.", {"verification_status": "inaccessible", "employer_relationship": "unknown", "extraction_method": "not_attempted", "matched_fields": [], "contradicted_fields": [], "unknown_fields": ["employer_identity","job_title","job_description","job_id","location","application_url","posting_date","recruiter_contact"]}, verification_status="inaccessible", employer_relationship="unknown")
        return [obs.to_dict()]
    observations: list[dict] = []
    seen: set[str] = set()
    lineage_profiles: list[tuple[int, ExtractedAdvertisement]] = []
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
            http_status = page.get("http_status")
            extraction_method = "html_jsonld_visible_text" if ("html" in content_type or "xhtml" in content_type) else "plain_text"
            candidate = extract_text(page.get("content"), is_html="html" in content_type or "xhtml" in content_type)
            auth = _authority_assessment(final_url, advertisement, authorized_domains, authority_mappings)
            source_type = auth.get("source_type") or "public_source_unknown_control"
            retrieval_ts = _now()
            base_details = {
                "submitted_url": url,
                "final_url": final_url,
                "source_url": final_url,
                "source_url_recorded": final_url,
                "source_type": source_type,
                "employer_relationship": auth["employer_relationship"],
                "authority_assessment": auth,
                "retrieval_timestamp": retrieval_ts,
                "http_status": http_status,
                "extraction_method": extraction_method,
                "extraction_warnings": candidate.warnings,
                "candidate_conflicts": candidate.conflicts,
                "source_family": _source_family(final_url),
                "source_published_at": candidate.date_posted,
                "source_modified_at": candidate.date_modified,
                "source_relationship": "unknown",
                "lineage_group_id": None,
                "lineage_status": "not_assessed",
                "lineage_review_status": "not_assessed",
                "lineage_provenance": "No adjudicated relationship exists; URL/domain difference and similarity do not establish independence.",
                "date_posted": candidate.date_posted,
                "date_modified": candidate.date_modified,
                "valid_through": candidate.valid_through,
                "authority_configuration": [m for m in (authority_mappings or []) if _mapping_matches_url(final_url, m)],
            }
            if not (candidate.description or "").strip():
                details = {**base_details, "extraction_status": "no_usable_content", "matched_fields": [], "contradicted_fields": [], "unknown_fields": ["employer_identity","job_title","job_description","job_id","location","application_url","posting_date","recruiter_contact"], "verification_status": "not_comparable" if str(http_status).startswith("2") or http_status == 200 else "inaccessible", "matching_explanation": {"note": "Retrieved source had no usable vacancy content."}}
                vstatus = details["verification_status"]
                observations.append(EvidenceObservation(url, source_type, details["retrieval_timestamp"], "available", "unavailable", "The source was retrieved but no meaningful vacancy content could be extracted.", "Extraction failure or non-vacancy content is not evidence of fraud or authorization.", details, verification_status=vstatus, employer_relationship=auth["employer_relationship"], source_family=_source_family(final_url), source_published_at=candidate.date_posted, source_modified_at=candidate.date_modified).to_dict())
                continue
            evidence_state, vstatus, summary, cmp_details = _compare(advertisement, candidate, final_url, authorized_domains, authority_mappings, max_current_posting_age_days)
            cmp_details.update(base_details)
            cmp_details.update({"extraction_status": "content_extracted"})
            rationale = cmp_details.pop("rationale_detail", "Comparison completed.")
            observations.append(EvidenceObservation(url, source_type, cmp_details["retrieval_timestamp"], "available", evidence_state, summary, rationale, cmp_details, verification_status=vstatus, employer_relationship=auth["employer_relationship"], source_family=_source_family(final_url), source_published_at=candidate.date_posted, source_modified_at=candidate.date_modified).to_dict())
            lineage_profiles.append((len(observations) - 1, candidate))
        except Exception as exc:  # collector records an honest source-level failure
            err_details = {
                "submitted_url": url,
                "final_url": None,
                "source_url_recorded": url,
                "source_type": "inaccessible_source",
                "employer_relationship": "unknown",
                "retrieval_timestamp": _now(),
                "http_status": None,
                "extraction_method": "not_attempted",
                "extraction_status": "not_attempted",
                "matched_fields": [],
                "contradicted_fields": [],
                "unknown_fields": ["employer_identity","job_title","job_description","job_id","location","application_url","posting_date","recruiter_contact"],
                "verification_status": "inaccessible",
                "matching_explanation": {"error": str(exc), "error_type": type(exc).__name__},
                "error": str(exc),
                "retrieval_error": type(exc).__name__,
            }
            observations.append(EvidenceObservation(url, "inaccessible_source", err_details["retrieval_timestamp"], "failed", "unavailable", "The source could not be retrieved.", f"Retrieval failed without asserting anything about authorization or fraud: {type(exc).__name__}: {exc}", err_details, verification_status="inaccessible", employer_relationship="unknown").to_dict())
    if not observations:
        observations.append(EvidenceObservation(None, "official_source", _now(), "unavailable", "unavailable", "No source was checked.", "No usable source URL was supplied.", {"verification_status": "inaccessible", "employer_relationship": "unknown"}, verification_status="inaccessible", employer_relationship="unknown").to_dict())
    for left_pos, (left_index, left) in enumerate(lineage_profiles):
        for right_index, right in lineage_profiles[left_pos + 1:]:
            left_url = observations[left_index].get("source_url")
            right_url = observations[right_index].get("source_url")
            sim = compare_lineage_text(
                left.description or "", right.description or "", left.contact,
                right.contact, left.application_url, right.application_url,
                left.job_id, right.job_id,
            )
            relation, explanation = candidate_relationship(sim)
            candidate = {
                "other_evidence_id": observations[right_index].get("evidence_id"),
                "other_source_url": right_url,
                "similarity": round(sim.score, 4),
                "shared_job_id": sim.shared_job_id,
                "conflicting_job_ids": sim.conflicting_job_ids,
                "shared_contact": sim.shared_contact,
                "shared_application_url": sim.shared_application_url,
                "candidate_relationship": relation + "_candidate",
                "review_status": "candidate",
                "explanation": explanation + " No relationship has been adjudicated.",
            }
            observations[left_index]["details"].setdefault("lineage_candidates", []).append(candidate)
            reverse = {**candidate, "other_evidence_id": observations[left_index].get("evidence_id"), "other_source_url": left_url}
            observations[right_index]["details"].setdefault("lineage_candidates", []).append(reverse)
    return observations


def candidate_official_sources(extracted: ExtractedAdvertisement, original_url: str | None = None, explicit_urls: list[str] | None = None) -> list[str]:
    explicit_urls = explicit_urls or []
    candidates = list(explicit_urls)
    if original_url and "linkedin.com" not in urlparse(original_url).netloc.lower():
        candidates.append(original_url)
    candidates.extend(url for url in getattr(extracted, "candidate_source_urls", []) if _is_specific_job_url(url))
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
