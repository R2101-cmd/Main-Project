from src.ingestion.image_extractor import extract_image_text


def test_empty_poster_is_unavailable_without_fabricating_text():
    result = extract_image_text(b"", "poster.png")
    assert result["text"] == ""
    assert result["status"] == "unavailable"
    assert result["content_hash"]


def test_poster_has_provenance_even_when_ocr_dependency_is_unavailable():
    result = extract_image_text(b"not-a-real-image", "poster.png")
    assert result["source_type"] == "poster_image"
    assert result["filename"] == "poster.png"
    assert result["observed_at"]
    assert result["warnings"] or result["text"]
