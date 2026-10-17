from src.database.repository import Repository

def test_database_persists_traceable_evidence(tmp_path):
    repo = Repository(tmp_path / "test.sqlite3")
    repo.initialize()
    ad = repo.add_advertisement(input_type="text", source_url=None, raw_text="Company: Example", retrieval_status="available", synthetic=True)
    repo.add_evidence(ad, claim_type="vacancy_authorization", source_url=None, source_type="manual", retrieval_status="available", summary="No listing found", evidence_state="unavailable", rationale="Official page inaccessible")
    assert repo.list_evidence(ad)[0]["evidence_state"] == "unavailable"
    source_id = repo.add_source_record(advertisement_id=ad, source_type="poster_image", source_url=None, content_hash="abc", raw_content=b"image", extracted_text="Title: Analyst", retrieval_status="available", warnings=["ocr warning"])
    row = repo.connection.execute("SELECT * FROM source_records WHERE id=?", (source_id,)).fetchone()
    assert row["content_hash"] == "abc"
    assert "ocr warning" in row["warnings_json"]
    repo.close()
