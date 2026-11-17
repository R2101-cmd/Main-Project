from __future__ import annotations

import hashlib
import json


VALID_AUTHORIZATION_LABELS = {"supported", "contradicted", "unresolved"}


def annotation_fingerprint(annotation: dict) -> str:
    canonical = json.dumps(annotation, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_annotation_bundle(original_annotations: list[dict], adjudications: list[dict]) -> list[str]:
    """Ensure adjudication references originals instead of replacing them."""
    errors: list[str] = []
    originals_by_id = {}
    for index, annotation in enumerate(original_annotations):
        annotation_id = annotation.get("annotation_id")
        if not annotation_id:
            errors.append(f"original annotation {index}: missing annotation_id")
        elif annotation_id in originals_by_id:
            errors.append(f"duplicate original annotation_id: {annotation_id}")
        else:
            originals_by_id[annotation_id] = annotation
        if annotation.get("annotation_type") != "independent_original":
            errors.append(f"original annotation {index}: must remain independent_original")
        if annotation.get("authorization_label") not in VALID_AUTHORIZATION_LABELS:
            errors.append(f"original annotation {index}: invalid authorization_label")
        if not annotation.get("reviewer_id"):
            errors.append(f"original annotation {index}: missing reviewer_id")

    adjudicated_ids: set[str] = set()
    for index, adjudication in enumerate(adjudications):
        adjudication_id = adjudication.get("adjudication_id")
        if not adjudication_id:
            errors.append(f"adjudication {index}: missing adjudication_id")
        elif adjudication_id in adjudicated_ids:
            errors.append(f"duplicate adjudication_id: {adjudication_id}")
        adjudicated_ids.add(adjudication_id)
        refs = adjudication.get("original_annotation_ids")
        if not isinstance(refs, list) or len(refs) < 2:
            errors.append(f"adjudication {index}: at least two original annotations are required")
        else:
            missing = [ref for ref in refs if ref not in originals_by_id]
            if missing:
                errors.append(f"adjudication {index}: unknown original annotations {missing}")
            fingerprints = adjudication.get("original_annotation_fingerprints")
            if not isinstance(fingerprints, dict):
                errors.append(f"adjudication {index}: original annotation fingerprints are required")
            else:
                for ref in refs:
                    expected = fingerprints.get(ref)
                    if expected != annotation_fingerprint(originals_by_id[ref]):
                        errors.append(f"adjudication {index}: original annotation changed or fingerprint is missing for {ref}")
        if adjudication.get("authorization_label") not in VALID_AUTHORIZATION_LABELS:
            errors.append(f"adjudication {index}: invalid authorization_label")
        if not adjudication.get("adjudicator_id"):
            errors.append(f"adjudication {index}: missing adjudicator_id")
    return errors
