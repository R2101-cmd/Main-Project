# Known Limitations

1. The 2,980-record real dataset has no independently adjudicated authorization ground truth.
2. The 207 lineage candidates have no completed human decisions.
3. No verified employer-domain or ATS authority mappings are populated.
4. The provisional benchmark has circularity risk and lacks a contradicted test class.
5. OCR cannot run in this environment because `pytesseract` and the Tesseract engine are not installed; the application degrades safely.
6. Freshness and aggregation thresholds remain policy-based, not calibrated on independent validation data.
7. Greenhouse and Lever dominate the collected source distribution.
8. The reported provisional metrics must not be presented as real-world accuracy.
