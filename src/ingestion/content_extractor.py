import json
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
    warnings: list[str] = field(default_factory=list)
    conflicts: dict[str, list[str]] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)
    candidate_source_urls: list[str] = field(default_factory=list)

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
        return ExtractedAdvertisement(None, None, "", None, None, None, None, ["No content was supplied for extraction."])
    if isinstance(html_or_text, bytes):
        html_or_text = html_or_text.decode("utf-8", errors="replace")
    if not isinstance(html_or_text, str):
        html_or_text = str(html_or_text)
    if not html_or_text.strip():
        return ExtractedAdvertisement(None, None, "", None, None, None, None, ["The supplied content was empty."])
    if is_html:
        soup = BeautifulSoup(html_or_text, "html.parser")
        records = _json_ld(soup)
        text = _main_text(soup)
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
        salary = salary.get("value") or salary.get("currency")
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
    return ExtractedAdvertisement(employer, title, description or "", location, salary, contact, application_url, _unique(warnings), conflicts, evidence, _unique(links))
