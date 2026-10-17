import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

class Repository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row

    def initialize(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        self.connection.executescript(schema)
        self.connection.commit()

    def add_advertisement(self, *, input_type: str, source_url: str | None, raw_text: str | None, retrieval_status: str, synthetic: bool = False) -> str:
        if input_type not in {"text", "url", "poster"}:
            raise ValueError("input_type must be text, url, or poster")
        identifier = str(uuid.uuid4())
        self.connection.execute("INSERT INTO advertisements VALUES (?, ?, ?, ?, ?, ?, ?)", (identifier, input_type, source_url, raw_text, retrieval_status, now_utc(), int(synthetic)))
        self.connection.commit()
        return identifier

    def add_evidence(self, advertisement_id: str, *, claim_type: str, source_url: str | None, source_type: str, retrieval_status: str, summary: str, evidence_state: str, rationale: str, source_timestamp: str | None = None) -> str:
        if evidence_state not in {"supported", "contradicted", "unverified", "unavailable"}:
            raise ValueError("invalid evidence state")
        identifier = str(uuid.uuid4())
        self.connection.execute("INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (identifier, advertisement_id, claim_type, source_url, source_type, now_utc(), source_timestamp, retrieval_status, summary, evidence_state, rationale))
        self.connection.commit()
        return identifier

    def add_lineage_relationship(self, left: str, right: str, relationship: str, similarity: float, rationale: str, reviewer_decision: str = "pending") -> str:
        if relationship not in {"original", "independent", "copied_derived", "unknown"}:
            raise ValueError("invalid relationship")
        identifier = str(uuid.uuid4())
        self.connection.execute("INSERT INTO lineage_relationships VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (identifier, left, right, relationship, similarity, rationale, reviewer_decision, now_utc()))
        self.connection.commit()
        return identifier

    def add_claim(self, advertisement_id: str, claim_type: str, value: str | None, extraction_state: str = "extracted") -> str:
        identifier = str(uuid.uuid4())
        self.connection.execute("INSERT INTO claims VALUES (?, ?, ?, ?, ?)", (identifier, advertisement_id, claim_type, value, extraction_state))
        self.connection.commit()
        return identifier

    def add_source_record(self, *, advertisement_id: str | None, source_type: str, source_url: str | None, content_hash: str | None, raw_content: bytes | None, extracted_text: str | None, retrieval_status: str, warnings: list[str] | None = None) -> str:
        identifier = str(uuid.uuid4())
        self.connection.execute("INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (identifier, advertisement_id, source_type, source_url, content_hash, raw_content, extracted_text, retrieval_status, now_utc(), json.dumps(warnings or [])))
        self.connection.commit()
        return identifier

    def list_evidence(self, advertisement_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute("SELECT * FROM evidence WHERE advertisement_id=?", (advertisement_id,))]

    def close(self) -> None:
        self.connection.close()
