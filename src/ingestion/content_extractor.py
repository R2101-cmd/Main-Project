import json
import html
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ExtractedAdvertisement:
    employer: str | None
    title: str | None
    description: str
    location: str | None
    salary: str | None
    contact: str | None
    application_url: str | None
    job_id: str | None = None
    posting_date: str | None = None
    recruiter: str | None = None
    employment_type: str | None = None
    warnings: list[str] = field(default_factory=list)
    conflicts: dict[str, list[str]] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)
    candidate_source_urls: list[str] = field(default_factory=list)
    date_posted: str | None = None
    date_modified: str | None = None
    valid_through: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_NOISE_SELECTORS = "nav, header, footer, script, style, noscript, form, aside"
_NOISE_HINTS = ("recommend", "similar-job", "suggested", "sign-in", "signin", "join now", "cookie")


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip(" |:-")
    return value or None


def _unique(values: list[str | None]) -> list[str]:
    result: list[str] = []
    for value in values:
        value = _clean(value)
        if value and value.lower() not in {item.lower() for item in result}:
            result.append(value)
    return result


def _json_ld(soup: BeautifulSoup | None) -> list[dict[str, Any]]:
    if soup is None:
        return []
    records: list[dict[str, Any]] = []
    for node in soup.select('script[type="application/ld+json"]'):
        try:
            parsed = json.loads(node.string or node.get_text())
        except (TypeError, json.JSONDecodeError):
            continue
        values = parsed if isinstance(parsed, list) else parsed.get("@graph", []) if isinstance(parsed, dict) and "@graph" in parsed else [parsed]
        records.extend(item for item in values if isinstance(item, dict))
    return records


def _first_meta(soup: BeautifulSoup | None, *names: str) -> str | None:
    if soup is None:
        return None
    for name in names:
        node = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if node and node.get("content"):
            return _clean(node["content"])
    return None


def _job_posting(records: list[dict[str, Any]]) -> dict[str, Any]:
    for record in records:
        kind = record.get("@type", [])
        kinds = kind if isinstance(kind, list) else [kind]
        if "JobPosting" in kinds:
            return record
    return {}


def _structured_ats_record(payload: Any) -> dict[str, Any] | None:
    """Normalize common ATS API JSON into the existing JobPosting shape."""
    if isinstance(payload, list):
        payload = payload[0] if payload and isinstance(payload[0], dict) else {}
    if not isinstance(payload, dict):
        return None
    candidate = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(candidate, dict) or not any(key in candidate for key in ("title", "job_title", "content", "description", "company_name", "id", "job_id")):
        return None
    organization = candidate.get("hiringOrganization") or candidate.get("employer")
    if not organization and candidate.get("company_name"):
        organization = {"name": candidate.get("company_name")}
    location = candidate.get("location") or candidate.get("jobLocation")
    if isinstance(location, dict) and location.get("name"):
        location = [{"address": {"addressLocality": location["name"]}}]
    elif isinstance(location, str):
        location = [{"address": {"addressLocality": location}}]
    # Prefer the stable ATS posting ID. Some Greenhouse payloads expose a
    # human-facing requisition label such as "See Opening ID" alongside it.
    identifier = candidate.get("id") or candidate.get("job_id") or candidate.get("job_identifier") or candidate.get("identifier") or candidate.get("requisition_id")
    return {
        "@type": "JobPosting",
        "title": candidate.get("title") or candidate.get("job_title") or candidate.get("name"),
        "hiringOrganization": organization,
        "jobLocation": location or [],
        "description": html.unescape(str(candidate.get("description") or candidate.get("content") or "")),
        "identifier": identifier,
        "datePosted": candidate.get("datePosted") or candidate.get("first_published") or candidate.get("publication_date") or candidate.get("date_posted"),
        "dateModified": candidate.get("dateModified") or candidate.get("updated_at") or candidate.get("update_date") or candidate.get("date_modified"),
        "url": candidate.get("url") or candidate.get("absolute_url") or candidate.get("application_url"),
        "employmentType": candidate.get("employmentType") or candidate.get("employment_type"),
        "baseSalary": candidate.get("baseSalary") or candidate.get("salary"),
    }


def _location_values(job: dict[str, Any], text: str) -> list[str]:
    values: list[str] = []
    locations = job.get("jobLocation", [])
    locations = locations if isinstance(locations, list) else [locations]
    for item in locations:
        if isinstance(item, dict):
            address = item.get("address", item)
            if isinstance(address, dict):
                values.append(", ".join(str(address[key]) for key in ("addressLocality", "addressRegion", "addressCountry") if address.get(key)))
            else:
                values.append(str(address))
    values += re.findall(r"(?:location|based in)\s*[:\-]\s*([^|.;\n]+)", text, re.I)
    return _unique(values)


def _main_text(soup: BeautifulSoup | None) -> str:
    if soup is None:
        return ""
    clone = BeautifulSoup(str(soup), "html.parser")
    for node in clone.select(_NOISE_SELECTORS):
        node.decompose()
    for node in list(clone.find_all(True) or []):
        # BeautifulSoup normally returns Tag instances here, but malformed or
        # parser-generated trees should not be allowed to crash extraction.
        if node is None or not hasattr(node, "get"):
            continue
        classes = node.get("class", []) or []
        if isinstance(classes, str):
            classes = [classes]
        hint = " ".join(str(value) for value in classes) + " " + str(node.get("id", ""))
        if any(term in hint.lower() for term in _NOISE_HINTS):
            node.decompose()
    # Preserve element boundaries so a label in one paragraph cannot consume the
    # next field while using the fallback label parser.
    text = clone.get_text(" | ", strip=True)
    text = re.split(r"\b(?:recommended jobs|similar jobs|people also viewed)\b", text, maxsplit=1, flags=re.I)[0]
    return _clean(text) or ""


def extract_text(html_or_text: str | bytes | None, is_html: bool = False) -> ExtractedAdvertisement:
    if html_or_text is None or html_or_text == b"" or html_or_text == "":
        return ExtractedAdvertisement(None, None, "", None, None, None, None, warnings=["No content was supplied for extraction."])
    if isinstance(html_or_text, bytes):
        html_or_text = html_or_text.decode("utf-8", errors="replace")
    if not isinstance(html_or_text, str):
        html_or_text = str(html_or_text)
    if not html_or_text.strip():
        return ExtractedAdvertisement(None, None, "", None, None, None, None, warnings=["The supplied content was empty."])
    structured_json = None
    if is_html:
        soup = BeautifulSoup(html_or_text, "html.parser")
        records = _json_ld(soup)
        text = _main_text(soup)
    else:
        try:
            structured_json = json.loads(html_or_text)
        except (TypeError, json.JSONDecodeError):
            structured_json = None
        structured_record = _structured_ats_record(structured_json) if structured_json is not None else None
        if structured_record:
            records = [structured_record]
            description_text = structured_record.get("description") or ""
            text = BeautifulSoup(description_text, "html.parser").get_text(" | ", strip=True)
            soup = BeautifulSoup(f"<main>{html.escape(text)}</main>", "html.parser")
        else:
            text = " ".join(html_or_text.split())
            soup = BeautifulSoup(f"<main>{html_or_text}</main>", "html.parser")
            records = []
    job = _job_posting(records)
    warnings: list[str] = []
    conflicts: dict[str, list[str]] = {}
    evidence: dict[str, str] = {}

    page_meta_title = _first_meta(soup, "og:title", "twitter:title")
    metadata_parts = re.split(r"\s+(?:-|at|\|)\s+", page_meta_title or "", maxsplit=2, flags=re.I)
    organization = job.get("hiringOrganization")
    org_name = organization.get("name") if isinstance(organization, dict) else None
    employer_match = re.search(r"(?:company|employer|organization)\s*[:\-]\s*([^|.;]+)", text, re.I)
    platform_employer = re.search(r"Job Application for .+?\s+at\s+([^|]+)", text, re.I)
    employer_values = _unique([org_name, employer_match.group(1) if employer_match else None, platform_employer.group(1) if platform_employer else None, metadata_parts[1] if len(metadata_parts) >= 2 and metadata_parts[1].lower() not in {"linkedin", "indeed"} else None])
    employer = employer_values[0] if employer_values else None
    if employer:
        evidence["employer"] = "JobPosting structured metadata" if org_name else "Labeled vacancy text"

    title_match = re.search(r"(?:job title|role|position|title)\s*[:\-]\s*([^|.;]+)", text, re.I)
    metadata_title = metadata_parts[0] if metadata_parts else None
    title_values = _unique([job.get("title"), metadata_title or page_meta_title, title_match.group(1) if title_match else None])
    title = title_values[0] if title_values else None
    if len(title_values) > 1:
        conflicts["title_candidates"] = title_values
        warnings.append("Multiple title candidates were found; the structured candidate was preferred.")
    if title:
        evidence["title"] = "JobPosting or page metadata"

    locations = _location_values(job, text)
    if title:
        platform_location = re.search(re.escape(title) + r"\s*\|\s*([^|]+?)\s*\|\s*Apply\b", text, re.I)
        if platform_location:
            locations = _unique(locations + [platform_location.group(1)])
    location = locations[0] if len(locations) == 1 else None
    if len(locations) > 1:
        conflicts["location"] = locations
        warnings.append("Conflicting location values were found; location was left unknown.")

    salary = job.get("baseSalary")
    if isinstance(salary, dict):
        salary_currency = _clean(salary.get("currency"))
        salary_value = salary.get("value")
        salary_unit = None
        if isinstance(salary_value, dict):
            salary_unit = _clean(salary_value.get("unitText"))
            minimum, maximum, single = salary_value.get("minValue"), salary_value.get("maxValue"), salary_value.get("value")
            if minimum is not None and maximum is not None:
                salary_value = f"{minimum}–{maximum}"
            else:
                salary_value = single if single is not None else minimum if minimum is not None else maximum
        salary = " ".join(str(value) for value in (salary_currency, salary_value, salary_unit) if value not in (None, "")) or None
    salary_match = re.search(r"(?:salary|compensation|pay)\s*[:\-]\s*([^|.;]+)", text, re.I)
    salary = _clean(salary or (salary_match.group(1) if salary_match else None))
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    contact = email_match.group(0) if email_match else None
    application_url = _clean(job.get("url") or job.get("directApply"))
    if isinstance(application_url, bool):
        application_url = None
    if not application_url:
        for link in soup.find_all("a", href=True):
            if any(term in link.get_text(" ", strip=True).lower() for term in ("apply", "careers", "application")):
                application_url = link["href"]
                break
    if not application_url:
        for form in soup.find_all("form", action=True):
            action = str(form.get("action") or "").strip()
            if action.startswith(("http://", "https://")):
                application_url = action
                break
    links = [str(link["href"]) for link in soup.find_all("a", href=True) if str(link["href"]).startswith(("http://", "https://"))]
    if not records:
        warnings.append("No JobPosting structured metadata was available; fields were inferred from visible/labeled content only.")
    description = _clean(job.get("description")) or text
    if not description or not description.strip():
        warnings.append("No meaningful job-description text was found after page cleanup.")
    # identifiers and posting metadata (best-effort, no fabrication)
    job_id = _clean(job.get("identifier") if not isinstance(job.get("identifier"), dict) else (job.get("identifier") or {}).get("value") or (job.get("identifier") or {}).get("name"))
    if not job_id:
        id_match = re.search(r"(?:job\s*id|requisition\s*(?:id|number)|req(?:uisition)?\s*#?|position\s*id)\s*[:#\-]?\s*([A-Za-z0-9][A-Za-z0-9._/-]{1,40})", text, re.I)
        job_id = _clean(id_match.group(1)) if id_match else None
        if job_id:
            job_id = job_id.rstrip(".,;") or None
    date_posted = _clean(job.get("datePosted"))
    date_modified = _clean(job.get("dateModified"))
    valid_through = _clean(job.get("validThrough"))
    if not date_posted:
        date_match = re.search(r"(?:posted|published|posting\s*date|date\s*posted)\s*[:\-]\s*([A-Za-z0-9,./\- ]{4,40})", text, re.I)
        date_posted = _clean(date_match.group(1)) if date_match else date_posted
    posting_date = date_posted  # legacy field; deliberately excludes modified/expiry dates.
    recruiter_match = re.search(r"(?:recruiter|hiring\s*manager|contact\s*person)\s*[:\-]\s*([^|.;\n]{2,80})", text, re.I)
    recruiter = _clean(recruiter_match.group(1)) if recruiter_match else (contact or None)
    employment_type_value = job.get("employmentType")
    if isinstance(employment_type_value, list):
        employment_type_value = ", ".join(str(v) for v in employment_type_value)
    employment_type = _clean(employment_type_value)
    if not employment_type:
        employment_match = re.search(r"(?:employment\s*type|job\s*type)\s*[:\-]\s*([^|.;\n]+)", text, re.I)
        employment_type = _clean(employment_match.group(1)) if employment_match else None
    if job_id:
        evidence["job_id"] = "Structured metadata or labeled text"
    if date_posted:
        evidence["posting_date"] = "Structured metadata or labeled text"
    if recruiter:
        evidence["recruiter"] = "Labeled text or contact"
    return ExtractedAdvertisement(employer=employer, title=title, description=description or "", location=location, salary=salary, contact=contact, application_url=application_url, job_id=job_id, posting_date=posting_date, recruiter=recruiter, employment_type=employment_type, warnings=_unique(warnings), conflicts=conflicts, evidence=evidence, candidate_source_urls=_unique(links), date_posted=date_posted, date_modified=date_modified, valid_through=valid_through)
