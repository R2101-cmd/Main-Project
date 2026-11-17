"""Poster OCR with Windows engine discovery and conservative preprocessing."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
import re
import shutil
from io import BytesIO


def _tesseract_command() -> str | None:
    configured = os.environ.get("TESSERACT_CMD")
    if configured and os.path.isfile(configured):
        return configured
    found = shutil.which("tesseract")
    if found:
        return found
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    return next((path for path in candidates if os.path.isfile(path)), None)


def _rotate(image, degrees: int):
    import cv2
    if degrees == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if degrees == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if degrees == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def _deskew(image):
    import cv2
    import numpy as np
    coords = np.column_stack(np.where(image < 200))
    if len(coords) < 20:
        return image, 0.0
    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.5 or abs(angle) > 15:
        return image, 0.0
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width // 2, height // 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE), float(angle)


def _preprocess(image):
    import cv2
    import numpy as np
    rgb = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    longest = max(gray.shape[:2])
    scale = max(1.0, min(3.0, 1800.0 / max(1, longest)))
    if scale != 1.0:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.fastNlMeansDenoising(gray, None, 7, 7, 21)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(denoised)
    deskewed, angle = _deskew(clahe)
    adaptive = cv2.adaptiveThreshold(deskewed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
    _, otsu = cv2.threshold(deskewed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return {"gray": deskewed, "contrast": clahe, "adaptive": adaptive, "otsu": otsu}, {"scale": round(scale, 3), "deskew_degrees": round(angle, 3)}


def _orientation(image, pytesseract) -> int:
    try:
        osd = pytesseract.image_to_osd(image, config="--psm 0")
        match = re.search(r"Rotate:\s*(\d+)", osd)
        return int(match.group(1)) % 360 if match else 0
    except Exception:
        return 0


def extract_image_text(image_bytes: bytes, filename: str | None = None) -> dict:
    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content_hash = hashlib.sha256(image_bytes).hexdigest()
    base = {"source_type": "poster_image", "filename": filename, "content_hash": content_hash, "observed_at": observed_at, "raw_text": "", "structured_fields": {}, "attempts": []}
    if not image_bytes:
        return {**base, "text": "", "status": "unavailable", "error_code": "empty_image", "warnings": ["The uploaded image was empty."]}
    try:
        from PIL import Image, ImageOps
        import pytesseract
    except ImportError as exc:
        return {**base, "text": "", "status": "unavailable", "error_code": "missing_python_dependency", "warnings": [f"Poster OCR requires Pillow and pytesseract. Missing: {exc.name or type(exc).__name__}."]}
    command = _tesseract_command()
    if not command:
        return {**base, "text": "", "status": "unavailable", "error_code": "tesseract_executable_missing", "warnings": ["The pytesseract Python wrapper is available, but tesseract.exe was not found. Install Tesseract OCR or set TESSERACT_CMD to its full Windows path."]}
    pytesseract.pytesseract.tesseract_cmd = command
    try:
        image = ImageOps.exif_transpose(Image.open(BytesIO(image_bytes))).convert("RGB")
        orientation = _orientation(image, pytesseract)
        variants, preprocessing = _preprocess(image)
        if orientation:
            variants = {name: _rotate(value, orientation) for name, value in variants.items()}
        best = None
        for variant_name, variant in variants.items():
            for psm in (6, 11, 3):
                config = f"--oem 3 --psm {psm}"
                data = pytesseract.image_to_data(variant, config=config, output_type=pytesseract.Output.DICT)
                confidences = [float(value) for value in data.get("conf", []) if str(value).strip() not in {"", "-1"}]
                confidence = sum(confidences) / len(confidences) if confidences else 0.0
                text = pytesseract.image_to_string(variant, config=config).strip()
                attempt = {"variant": variant_name, "psm": psm, "confidence": round(confidence, 2), "characters": len(text)}
                base["attempts"].append(attempt)
                score = confidence + min(len(text), 1000) / 1000
                if text and (best is None or score > best[0]):
                    best = (score, text, attempt)
        if best is None:
            return {**base, "text": "", "status": "available", "error_code": "no_text_detected", "orientation_degrees": orientation, "preprocessing": preprocessing, "engine_path": command, "warnings": ["OCR completed but no readable text was detected."]}
        return {**base, "text": best[1], "raw_text": best[1], "status": "available", "error_code": None, "orientation_degrees": orientation, "preprocessing": preprocessing, "selected_attempt": best[2], "engine_path": command, "warnings": []}
    except pytesseract.TesseractNotFoundError:
        return {**base, "text": "", "status": "unavailable", "error_code": "tesseract_executable_missing", "warnings": ["Tesseract could not be executed. Install Tesseract OCR or set TESSERACT_CMD to the full path of tesseract.exe."]}
    except Exception as exc:
        return {**base, "text": "", "status": "failed", "error_code": "ocr_runtime_error", "warnings": [f"Poster OCR failed: {type(exc).__name__}: {exc}"]}
