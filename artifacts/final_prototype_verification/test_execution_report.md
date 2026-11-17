# Test Execution Report

- `python -m pytest -q`: **165 passed, 7 warnings**
- Python compilation: **passed**
- Streamlit AppTest: **passed**
- Live Streamlit startup: **passed**, HTTP 200 on localhost:8511
- Pasted-text workflow: **passed**, unresolved output produced without exception
- Public URL safety: **passed**, localhost/private destination rejected
- Poster OCR fallback: **passed**, unavailable warning returned without fabricating text
- Annotation validation: **passed**, 145 records with no structural errors
- Authority configuration validation: **passed**, zero mappings and no invalid entries
- Collected dataset loading: **passed**, 2,980 records and 18 employer IDs
- Group split validation: **passed**, no vacancy groups cross partitions

Warnings are from third-party dependencies and do not represent application failures.
