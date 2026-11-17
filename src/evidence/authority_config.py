"""Read-only authority mappings for live evidence collection.

Mappings are trusted only when an operator has recorded both verification
status and provenance. The shipped file intentionally contains no mappings.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from src.config import ROOT


DEFAULT_AUTHORITY_CONFIG = ROOT / "config" / "employer_sources_v1.json"


def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _domain(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value if "://" in value else "https://" + value)
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or "." not in host or ".." in host:
        return None
    return host


def load_authority_config(path: str | Path = DEFAULT_AUTHORITY_CONFIG) -> dict:
    """Return validated configuration; invalid/unverified rows are ignored."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": "employer-sources-v1", "max_current_posting_age_days": 180, "mappings": []}
    if not isinstance(raw, dict) or raw.get("schema_version") != "employer-sources-v1":
        return {"schema_version": "employer-sources-v1", "max_current_posting_age_days": 180, "mappings": []}
    mappings = []
    for row in raw.get("mappings", []):
        if not isinstance(row, dict):
            continue
        domain = _domain(row.get("authorized_domain"))
        provenance = str(row.get("verification_provenance") or "").strip()
        verified_at = str(row.get("last_verified_at") or "").strip()
        path_prefix = str(row.get("authorized_path_prefix") or "").strip()
        try:
            verified_date = date.fromisoformat(verified_at)
        except ValueError:
            verified_date = None
        if (row.get("verification_status") != "verified" or row.get("relationship_type") not in {"employer_owned_official", "verified_employer_associated_ats"} or not domain or not provenance
                or verified_date is None or verified_date > date.today() or not row.get("employer_id") or not row.get("canonical_employer_name")
                or (row.get("relationship_type") == "verified_employer_associated_ats" and not path_prefix.startswith("/"))):
            continue
        mappings.append({**row, "authorized_domain": domain, "authorized_path_prefix": path_prefix or None})
    max_age = raw.get("max_current_posting_age_days", 180)
    if not isinstance(max_age, int) or max_age < 1 or max_age > 3650:
        max_age = 180
    return {"schema_version": "employer-sources-v1", "max_current_posting_age_days": max_age, "mappings": mappings}


def authority_for_employer(advertised_employer: str | None, config: dict | None = None) -> tuple[set[str], list[dict]]:
    """Select explicitly verified mappings matching this advertised employer."""
    config = config or load_authority_config()
    needle = _norm(advertised_employer)
    matched = [row for row in config.get("mappings", []) if needle and _norm(row.get("canonical_employer_name")) == needle]
    return {row["authorized_domain"] for row in matched}, matched

