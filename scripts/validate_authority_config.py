"""Validate employer-domain/ATS authority mappings without adding mappings."""
import argparse, json
from pathlib import Path

REQUIRED = {"employer_id", "employer_name", "authorized_domain", "relationship_type", "verification_status", "provenance", "last_verified_at"}
RELATIONSHIPS = {"employer_owned_official", "verified_employer_associated_ats"}

def main():
    p = argparse.ArgumentParser(); p.add_argument("path", nargs="?", default="config/employer_sources_v1.json"); args = p.parse_args()
    data = json.loads(Path(args.path).read_text(encoding="utf-8")); errors=[]
    for i, mapping in enumerate(data.get("mappings", []), 1):
        missing = REQUIRED - mapping.keys()
        if missing: errors.append(f"mapping {i}: missing {sorted(missing)}")
        if mapping.get("verification_status") != "verified": errors.append(f"mapping {i}: verification_status must be verified")
        if mapping.get("relationship_type") not in RELATIONSHIPS: errors.append(f"mapping {i}: relationship_type is not an authoritative relationship")
    print(json.dumps({"mappings": len(data.get("mappings", [])), "valid": not errors, "errors": errors}, indent=2))
    raise SystemExit(1 if errors else 0)
if __name__ == "__main__": main()
