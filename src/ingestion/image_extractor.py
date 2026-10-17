"""Optional recruitment-poster OCR support."""

from datetime import datetime, timezone
import hashlib


def extract_image_text(image_bytes: bytes, filename: str | None = None) -> dict:
    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content_hash = hashlib.sha256(image_bytes).hexdigest()
    base = {"source_type": "poster_image", "filename": filename, "content_hash": content_hash, "observed_at": observed_at}
    if not image_bytes:
        return {**base, "text": "", "status": "unavailable", "warnings": ["The uploaded image was empty."]}
    try:
        from io import BytesIO
        from PIL import Image
        import pytesseract
        text = pytesseract.image_to_string(Image.open(BytesIO(image_bytes))).strip()
    except ImportError:
        return {**base, "text": "", "status": "unavailable", "warnings": ["Poster OCR requires Pillow, pytesseract and the Tesseract OCR engine; no text was fabricated."]}
    except Exception as exc:
        return {**base, "text": "", "status": "failed", "warnings": [f"Poster OCR failed: {type(exc).__name__}: {exc}"]}
    return {**base, "text": text, "status": "available", "warnings": [] if text else ["OCR completed but no meaningful text was detected in the image."]}
