"""Pre-collection configuration and freeze checks.

This module deliberately validates configuration only.  It does not collect
sources, create records, or assign authorization labels.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REQUIRED_SCHEMA_VERSIONS = {
    "collection_config": "collection-config-v1",
    "advertisement": "advertisement-record-v1",
    "evidence": "evidence-item-v1",
    "annotation": "annotation-form-v1",
    "lineage": "lineage-review-v1",
    "collection_log": "collection-log-v1",
}

PLACEHOLDER_WORDS = {
    "",
    "pending",
    "pending_assignment",
    "pending_decision",
    "placeholder",
    "example",
    "todo",
    "tbd",
    "unassigned",
}

STRICT_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")


def _status(name: str, state: str, reason: str, corrective_action: str) -> dict[str, str]:
    return {
        "requirement": name,
        "status": state,
        "reason": reason,
        "corrective_action": corrective_action,
    }


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip().lower()
    return text in PLACEHOLDER_WORDS or any(word in text for word in ("placeholder", "pending_", "example_"))


def _is_real_identity(value: Any) -> bool:
    return isinstance(value, str) and not _is_placeholder(value)


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp is unset")
    value = value.strip()
    if not STRICT_TIMESTAMP.fullmatch(value):
        raise ValueError("timestamp must use strict ISO 8601 form YYYY-MM-DDTHH:MM:SS[.ffffff](Z|±HH:MM)")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include an explicit timezone offset or Z")
    return parsed


def _check_schema_versions(config: dict[str, Any]) -> dict[str, str]:
    supplied = config.get("schema_versions")
    if not isinstance(supplied, dict):
        return _status(
            "Required schema/configuration versions",
            "blocked",
            "schema_versions is missing or is not an object.",
            "Add every required version from collection-config-v1.",
        )
    missing = [key for key, value in REQUIRED_SCHEMA_VERSIONS.items() if supplied.get(key) != value]
    if missing:
        return _status(
            "Required schema/configuration versions",
            "blocked",
            f"Missing or mismatched versions: {', '.join(missing)}.",
            "Use the version identifiers in schemas/ and do not start collection until they match.",
        )
    return _status("Required schema/configuration versions", "ready", "All required versions are explicit.", "")


def _check_protocol_version(config: dict[str, Any]) -> dict[str, str]:
    if config.get("annotation_protocol_version") != "independent-annotation-protocol-v2":
        return _status(
            "Annotation protocol version",
            "blocked",
            "The required independent annotation protocol version is missing or mismatched.",
            "Set annotation_protocol_version to independent-annotation-protocol-v2.",
        )
    return _status("Annotation protocol version", "ready", "Independent annotation protocol v2 is explicit.", "")


def _check_window(config: dict[str, Any]) -> dict[str, str]:
    window = config.get("collection_window") or {}
    if not isinstance(window, dict):
        return _status("Fixed 30-day collection window", "blocked", "collection_window must be an object.", "Provide a collection_window object with duration, timestamps, and timezone.")
    start = window.get("start")
    end = window.get("end")
    timezone_name = window.get("timezone")
    if window.get("duration_days") != 30:
        return _status(
            "Fixed 30-day collection window",
            "blocked",
            "duration_days is missing or is not 30.",
            "Set duration_days to 30 and provide timestamps exactly 30 days apart.",
        )
    if start is None or end is None or _is_placeholder(timezone_name):
        return _status(
            "Fixed 30-day collection window",
            "pending",
            "Start/end timestamps or the named timezone are unset.",
            "Set explicit ISO 8601 start and end timestamps with timezone, exactly 30 days apart.",
        )
    try:
        zone = ZoneInfo(timezone_name)
        start_dt = _parse_timestamp(start)
        end_dt = _parse_timestamp(end)
        if start_dt.astimezone(zone).utcoffset() != start_dt.utcoffset() or end_dt.astimezone(zone).utcoffset() != end_dt.utcoffset():
            raise ValueError("timestamp offset does not match the configured named timezone")
    except (ValueError, TypeError, KeyError) as exc:
        return _status(
            "Fixed 30-day collection window",
            "blocked",
            str(exc),
            "Use parseable ISO 8601 timestamps with an explicit offset or Z.",
        )
    if end_dt <= start_dt:
        return _status(
            "Fixed 30-day collection window",
            "blocked",
            "The end timestamp is not after the start timestamp.",
            "Correct the collection window before collection.",
        )
    if end_dt - start_dt != timedelta(days=30):
        return _status(
            "Fixed 30-day collection window",
            "blocked",
            f"Window duration is {end_dt - start_dt}, not exactly 30 days.",
            "Set the end timestamp to exactly 30 days after the start timestamp.",
        )
    return _status(
        "Fixed 30-day collection window",
        "ready",
        f"Valid ISO 8601 window in {timezone_name}.",
        "",
    )


def _check_sampling(config: dict[str, Any]) -> list[dict[str, str]]:
    scope = config.get("sampling_frame") or {}
    if not isinstance(scope, dict):
        return [_status("Sampling frame", "blocked", "sampling_frame must be an object.", "Provide the geography, role scope, strata, selection procedure, seed, and target.")]
    results: list[dict[str, str]] = []
    geography = scope.get("geography")
    roles = scope.get("role_scope")
    if _is_placeholder(geography) or _is_placeholder(roles):
        results.append(_status("Geography and role scope", "blocked", "Geography or role scope is missing.", "Define India/remote eligibility and the data/analytics role scope."))
    else:
        results.append(_status("Geography and role scope", "ready", "India and the defined related-role scope are explicit.", ""))

    strata = scope.get("source_strata")
    selection = scope.get("selection_procedure")
    if not isinstance(strata, list) or not strata:
        results.append(_status("Source strata and selection procedure", "pending", "No source strata are configured.", "Define source strata and a selection procedure before collection."))
    elif (
        not isinstance(selection, str)
        or _is_placeholder(selection)
        or any(not isinstance(item, dict) or not isinstance(item.get("id"), str) or _is_placeholder(item.get("id")) or not isinstance(item.get("selection_procedure"), str) or _is_placeholder(item.get("selection_procedure")) for item in strata)
        or len({item.get("id") for item in strata if isinstance(item, dict)}) != len(strata)
    ):
        results.append(_status("Source strata and selection procedure", "blocked", "At least one stratum lacks a selection procedure.", "Document how records will be selected within every stratum."))
    else:
        results.append(_status("Source strata and selection procedure", "ready", f"{len(strata)} strata have documented selection procedures.", ""))

    policy = scope.get("selection_policy") or {}
    if policy.get("artificial_class_balancing") is not False or policy.get("model_prediction_selection") is not False:
        results.append(_status("Non-biased selection policy", "blocked", "Artificial class balancing or model-prediction selection is not explicitly disabled.", "Set both policy flags to false and record the sampling seed/procedure."))
    else:
        results.append(_status("Non-biased selection policy", "ready", "Selection is not based on artificial class balancing or model predictions.", ""))

    if scope.get("sampling_seed") is None or _is_placeholder(scope.get("sampling_seed")):
        results.append(_status("Sampling seed", "pending", "The source-frame sampling seed is unset.", "Freeze the sampling seed before collection, or document why a deterministic non-random procedure is used."))
    else:
        results.append(_status("Sampling seed", "ready", f"Sampling seed is {scope['sampling_seed']}.", ""))

    target = scope.get("vacancy_group_target")
    if not isinstance(target, dict) or target.get("is_feasibility_target") is not True:
        results.append(_status("100–200 vacancy-group target", "blocked", "The target is not explicitly marked as a feasibility target.", "Mark the target as feasibility-only and do not present it as statistical power."))
    else:
        results.append(_status("100–200 vacancy-group target", "ready", "The target is explicitly feasibility-only.", ""))
    return results


def _check_reviewers(config: dict[str, Any]) -> dict[str, str]:
    reviewers = config.get("reviewers") or {}
    if not isinstance(reviewers, dict):
        return _status("Reviewer and adjudicator setup", "blocked", "reviewers must be an object.", "Provide reviewer setup with actual assigned identifiers.")
    ids = reviewers.get("reviewer_ids")
    adjudicator = reviewers.get("adjudicator_id")
    if reviewers.get("setup_status") != "assigned" or reviewers.get("operational_authorization") is not True:
        return _status("Reviewer and adjudicator setup", "pending", "Reviewer setup is not operationally authorized.", "Assign two distinct reviewers and an adjudicator, then explicitly authorize the setup." )
    if not isinstance(ids, list) or len(ids) < 2 or any(not _is_real_identity(item) for item in ids) or len(set(ids)) != len(ids):
        return _status("Reviewer and adjudicator setup", "blocked", "Reviewer IDs are missing, duplicated, or placeholders.", "Use actual distinct reviewer identifiers; do not use placeholder IDs." )
    if not _is_real_identity(adjudicator) or adjudicator in ids:
        return _status("Reviewer and adjudicator setup", "blocked", "The adjudicator is missing, a placeholder, or also a reviewer.", "Assign a distinct non-placeholder adjudicator identifier." )
    return _status("Reviewer and adjudicator setup", "ready", "Two reviewers and a distinct adjudicator are assigned.", "")


def _check_privacy(config: dict[str, Any]) -> dict[str, str]:
    policy = config.get("privacy_and_retention") or {}
    if not isinstance(policy, dict):
        return _status("Privacy, access, and evidence-retention decisions", "blocked", "privacy_and_retention must be an object.", "Provide explicit privacy, redaction, snapshot, retention, and access decisions.")
    required = ("privacy_decision", "redaction_policy", "snapshot_policy", "retention_decision", "access_control")
    missing = [key for key in required if _is_placeholder(policy.get(key))]
    if policy.get("status") != "approved" or missing:
        state = "blocked" if policy.get("status") == "approved" and missing else "pending"
        return _status(
            "Privacy, access, and evidence-retention decisions",
            state,
            "Required privacy or retention decisions are not complete: " + (", ".join(missing) or "approval status is pending") + ".",
            "Document minimization, redaction, permitted snapshots, retention, and access controls before collection.",
        )
    return _status("Privacy, access, and evidence-retention decisions", "ready", "Privacy and retention decisions are approved and explicit.", "")


def _check_collection_log(config: dict[str, Any]) -> dict[str, str]:
    log = config.get("collection_log") or {}
    if not isinstance(log, dict):
        return _status("Collection log", "blocked", "collection_log must be an object.", "Configure a collection-log path and schema version.")
    if _is_placeholder(log.get("path")) or log.get("schema_version") != REQUIRED_SCHEMA_VERSIONS["collection_log"]:
        return _status("Collection log", "blocked", "A valid collection-log path and schema version are not configured.", "Configure the collection log before collecting any records." )
    return _status("Collection log", "ready", f"Collection events will be recorded at {log['path']}.", "")


def _check_operational_authorization(config: dict[str, Any]) -> dict[str, str]:
    auth = config.get("operational_authorization") or {}
    if not isinstance(auth, dict):
        return _status("Operational collection authorization", "blocked", "operational_authorization must be an object.", "Provide explicit operator authorization fields.")
    if auth.get("status") != "approved":
        return _status("Operational collection authorization", "pending", "Collection has not been explicitly authorized by a named operator.", "After all safeguards are complete, record a real approver and timestamp.")
    if not _is_real_identity(auth.get("approved_by")):
        return _status("Operational collection authorization", "blocked", "The approving operator identifier is missing or a placeholder.", "Record the real approving operator identifier.")
    try:
        _parse_timestamp(auth.get("approved_at"))
    except ValueError as exc:
        return _status("Operational collection authorization", "blocked", f"Approval timestamp is invalid: {exc}", "Record approval time as strict ISO 8601 with timezone.")
    return _status("Operational collection authorization", "ready", "A named operator authorized collection with a valid timestamp.", "")


def verify_frozen_snapshot(root: str | Path) -> dict[str, Any]:
    """Verify the existing frozen snapshot without writing to it."""
    directory = Path(root)
    manifest_path = directory / "FREEZE_MANIFEST.json"
    if not manifest_path.exists():
        return {"status": "blocked", "reason": "FREEZE_MANIFEST.json is missing.", "files": []}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    results = []
    for entry in manifest.get("files", []):
        path = directory / entry["file"]
        if not path.exists():
            results.append({"file": entry["file"], "status": "blocked", "reason": "file is missing"})
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        size_ok = path.stat().st_size == entry.get("bytes")
        hash_ok = digest == entry.get("sha256", "").upper()
        results.append({"file": entry["file"], "status": "ready" if size_ok and hash_ok else "blocked", "sha256": digest, "bytes": path.stat().st_size, "reason": "hash and byte count match" if size_ok and hash_ok else "hash or byte count mismatch"})
    status = "ready" if results and all(item["status"] == "ready" for item in results) else "blocked"
    return {"status": status, "reason": "Frozen artifacts match their manifest." if status == "ready" else "Frozen artifact verification failed.", "files": results}


def configuration_fingerprint(config: dict[str, Any]) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def evaluate_config(config: dict[str, Any], frozen_root: str | Path | None = None) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {"collection_ready": False, "configuration_fingerprint": configuration_fingerprint(config), "checks": [_status("Configuration object", "blocked", "The collection configuration must be a JSON object.", "Replace the malformed configuration with config/collection_config_v1.json and complete it safely.")], "required_schema_versions": REQUIRED_SCHEMA_VERSIONS}
    checks = [_check_schema_versions(config), _check_protocol_version(config), _check_window(config), *_check_sampling(config), _check_reviewers(config), _check_privacy(config), _check_collection_log(config)]
    if frozen_root is not None:
        frozen = verify_frozen_snapshot(frozen_root)
        checks.append(_status("Frozen baseline integrity", frozen["status"], frozen["reason"], "Restore the frozen snapshot from a trusted copy before proceeding." if frozen["status"] != "ready" else ""))
    checks.append(_check_operational_authorization(config))
    collection_ready = all(item["status"] == "ready" for item in checks)
    return {"collection_ready": collection_ready, "configuration_fingerprint": configuration_fingerprint(config), "checks": checks, "required_schema_versions": REQUIRED_SCHEMA_VERSIONS}

