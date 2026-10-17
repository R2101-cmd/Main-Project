from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "recruitment_verification.sqlite3"
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
