# TrustHire Poster OCR Verification Report

## 1. Root cause

The active Python environment originally had Pillow and OpenCV but did not have `pytesseract`. No `tesseract.exe` was available on PATH or in the standard Windows installation locations. The previous implementation sent the raw image directly to `image_to_string`, with no preprocessing, orientation handling, confidence selection, executable discovery, or editable OCR step.

## 2. Files modified

- `src/ingestion/image_extractor.py`
- `app.py`
- `requirements.txt`
- `.env.example`
- `tests/test_image_extractor.py`
- `scripts/test_poster_ocr.py`

Protected datasets, annotations, and research labels were not modified.

## 3. Dependencies

- `pytesseract 0.3.13` installed in the active Python environment.
- Native Windows Tesseract OCR `5.4.0.20240606` installed at `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- Pillow was already installed.
- OpenCV was already installed and is now declared explicitly in `requirements.txt`.
- `TESSERACT_CMD` is supported as an optional Windows override.

## 4. OCR improvements

The implementation now provides:

- Windows executable discovery through `TESSERACT_CMD`, PATH, and standard install paths.
- Explicit error codes and warnings when dependencies or the executable are unavailable.
- EXIF-aware image loading.
- Low-resolution upscaling.
- Grayscale conversion.
- Non-local-means denoising.
- CLAHE contrast enhancement.
- Adaptive and Otsu threshold variants.
- Practical deskewing.
- Tesseract orientation detection and rotation correction.
- PSM 6, 11, and 3 trials.
- Confidence-based result selection.
- Preservation of raw OCR text and diagnostics.
- Editable OCR text before submission to the existing verification pipeline.
- Existing structured extraction for employer, title, location, description, skills, qualifications, URLs, and email-like application routes remains separate from raw OCR text.

## 5. Five-poster test

No poster images were present in the repository. Five in-memory PNG fixtures were therefore generated specifically for the test harness; these are test fixtures, not claims about arbitrary real-world posters.

| Fixture | Result | Expected tokens recovered | Selected confidence |
|---|---|---:|---:|
| Clear poster | PASS | 5/5 | 95.56 |
| Low-resolution/noisy poster | PASS | 5/5 | 95.60 |
| Coloured-background poster | PASS | 5/5 | 95.40 |
| Multi-column poster | PASS | 5/5 | 95.52 |
| Rotated poster | PASS | 5/5 | 95.56 |

Expected tokens were company name, job title, location, skill, and email/domain. The rotated fixture was detected with a 90-degree orientation correction.

## 6. Final verification

- Full test suite: **166 passed, 7 warnings**.
- Python compilation: **passed**.
- Streamlit smoke workflow: **passed**.
- Pasted-text workflow: unchanged and passing.
- Public URL layout/workflow: unchanged and passing.
- Poster OCR backend: successful on five generated fixtures.
- Missing-engine behavior: explicit `tesseract_executable_missing` result tested.
- Protected-file hash manifest: unchanged.

## 7. Remaining limitations

1. OCR accuracy on real-world posters with stylized fonts, severe blur, shadows, handwriting, or complex graphics remains unvalidated.
2. Automatic orientation detection can fail when an image has too little text for Tesseract OSD.
3. Deskew is intentionally conservative and does not replace a full document-layout model.
4. The current structured extractor may merge adjacent label lines in unusual poster layouts; manual correction is available before assessment.
5. Tesseract language data is currently the default English installation; multilingual posters require additional trained data.
