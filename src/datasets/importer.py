import csv
import hashlib
import html
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


REQUIRED_PRESERVED_COLUMNS = {
    "job_id", "title", "location", "department", "salary_range", "company_profile",
    "description", "requirements", "benefits", "telecommuting", "fraudulent",
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    value = html.unescape(str(value))
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)).strip()


def _tokens(value: str) -> set[str]:
    return {token for token in normalize_text(value).split() if len(token) > 1}


def _jaccard(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def _hash_bucket(value: str) -> str:
    number = int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:8], 16) % 100
    return "train" if number < 70 else "validation" if number < 85 else "test"


def _source_label(value: str) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned if cleaned else None


@dataclass
class ImportReport:
    input_path: str
    output_path: str
    total_rows: int
    output_rows: int
    columns: list[str]
    missing_values: dict[str, int]
    duplicate_job_ids: int
    exact_duplicate_rows: int
    potential_repost_pairs: int
    potential_repost_components: int
    source_fraud_label_counts: dict[str, int]
    authorization_label_counts: dict[str, int]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        rows = [dict(row) for row in reader]
    return list(reader.fieldnames), rows


def _find_repost_candidates(records: list[dict[str, Any]]) -> tuple[list[tuple[int, int, float]], list[str]]:
    blocks: defaultdict[tuple[str, str], list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        title, location = record["normalized_title"], record["normalized_location"]
        if title and location:
            blocks[(title, location)].append(index)
    candidates: list[tuple[int, int, float]] = []
    for indices in blocks.values():
        for offset, left_index in enumerate(indices):
            for right_index in indices[offset + 1:]:
                left = records[left_index]
                right = records[right_index]
                left_text = left["combined_text"]
                right_text = right["combined_text"]
                score = _jaccard(left_text, right_text)
                if score >= 0.75:
                    candidates.append((left_index, right_index, score))
    parent = list(range(len(records)))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: int, right: int) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for left, right, _score in candidates:
        union(left, right)
    groups = [find(index) for index in range(len(records))]
    root_sizes = Counter(groups)
    component_ids: dict[int, str] = {}
    split_groups: list[str] = []
    for index, root in enumerate(groups):
        if root_sizes[root] > 1:
            component_ids.setdefault(root, f"repost-candidate-{len(component_ids) + 1:05d}")
            split_groups.append(component_ids[root])
        else:
            split_groups.append(f"record-{index:05d}")
    return candidates, split_groups


def import_csv(input_path: str | Path, output_path: str | Path) -> ImportReport:
    source = Path(input_path)
    destination = Path(output_path)
    columns, rows = _read_csv(source)
    missing = Counter()
    job_ids = Counter()
    exact_fingerprints = Counter()
    records: list[dict[str, Any]] = []
    fingerprints_for_records: list[str] = []
    for row in rows:
        for column in columns:
            if not str(row.get(column) or "").strip():
                missing[column] += 1
        source_id = str(row.get("job_id") or "").strip() or None
        if source_id is not None:
            job_ids[source_id] += 1
        exact_basis = {column: row.get(column, "") for column in columns if column != "job_id"}
        exact_fingerprints[json.dumps(exact_basis, sort_keys=True, ensure_ascii=False)] += 1
        description = row.get("description", "") or ""
        requirements = row.get("requirements", "") or ""
        benefits = row.get("benefits", "") or ""
        profile = row.get("company_profile", "") or ""
        records.append({
            "record_id": f"imported-{source_id}" if source_id else f"imported-row-{len(records) + 1}",
            "source_record_id": source_id,
            "source_dataset": source.name,
            "original": row,
            "original_title": row.get("title") or None,
            "normalized_title": normalize_text(row.get("title")),
            "original_location": row.get("location") or None,
            "normalized_location": normalize_text(row.get("location")),
            "department": row.get("department") or None,
            "salary_range": row.get("salary_range") or None,
            "company_profile": profile or None,
            "normalized_company_matching_text": normalize_text(profile),
            "description": description or None,
            "requirements": requirements or None,
            "benefits": benefits or None,
            "combined_text": " ".join(part for part in (row.get("title"), profile, description, requirements, benefits) if part),
            "telecommuting": row.get("telecommuting") or None,
            "source_fraud_label": _source_label(row.get("fraudulent")),
            "source_urls": [],
            "requisition_id": None,
            "authorization_label": "unresolved",
            "employer_identity": "unresolved",
            "evidence": [],
            "annotation_status": "unreviewed_import",
            "synthetic": False,
        })
        fingerprints_for_records.append(json.dumps(exact_basis, sort_keys=True, ensure_ascii=False))
    deduplicated: list[dict[str, Any]] = []
    first_by_fingerprint: dict[str, dict[str, Any]] = {}
    for record, fingerprint in zip(records, fingerprints_for_records):
        existing = first_by_fingerprint.get(fingerprint)
        if existing is not None:
            existing["duplicate_source_record_ids"].append(record["source_record_id"])
            continue
        record["duplicate_source_record_ids"] = []
        first_by_fingerprint[fingerprint] = record
        deduplicated.append(record)
    records = deduplicated
    candidates, split_groups = _find_repost_candidates(records)
    for index, record in enumerate(records):
        record["potential_repost_candidate_ids"] = []
        record["potential_repost_similarity"] = {}
        record["lineage_review_status"] = "candidate_unreviewed" if split_groups[index].startswith("repost-candidate") else "no_candidate_found"
        record["split_group"] = split_groups[index]
    for left, right, score in candidates:
        records[left]["potential_repost_candidate_ids"].append(records[right]["record_id"])
        records[right]["potential_repost_candidate_ids"].append(records[left]["record_id"])
        records[left]["potential_repost_similarity"][records[right]["record_id"]] = round(score, 6)
        records[right]["potential_repost_similarity"][records[left]["record_id"]] = round(score, 6)
    for record in records:
        record["partition"] = _hash_bucket(record["split_group"])
        record.pop("combined_text", None)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")
    fraud_counts = Counter(str(record["source_fraud_label"]) for record in records if record["source_fraud_label"] is not None)
    return ImportReport(str(source), str(destination), len(rows), len(records), columns, dict(missing), sum(count - 1 for count in job_ids.values() if count > 1), sum(count - 1 for count in exact_fingerprints.values() if count > 1), len(candidates), len({group for group in split_groups if group.startswith("repost-candidate")}), dict(fraud_counts), {"unresolved": len(records)}, ["Exact duplicate rows were removed from the processed output and retained in the original CSV.", "Imported records are not manually reviewed authorization labels.", "The source fraudulent field is preserved separately and is not used as vacancy authorization.", "Potential repost components are conservative split groups, not confirmed lineage merges.", "No source URLs, requisition IDs, official evidence, or employer verification were invented."])
