import logging

import streamlit as st

from src.aggregation.rules import lineage_aware, naive
from src.decision.policy import assess
from src.evidence.collector import candidate_official_sources, collect_vacancy_evidence
from src.ingestion.content_extractor import extract_text
from src.ingestion.image_extractor import extract_image_text
from src.ingestion.url_fetcher import FetchError, UnsafeURL, fetch_public_page
from src.config import DEFAULT_DATABASE
from src.database.repository import Repository

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Vacancy Authorization Verification", layout="wide")


def verification_page() -> None:
    st.title("Vacancy Authorization Verification")
    st.caption("Evidence for authorization of a specific vacancy; employer identity and fraud are separate questions.")
    input_mode = st.radio("Input type", ["Pasted text", "Public URL", "Poster image"], horizontal=True)
    if input_mode == "Pasted text":
        input_value = st.text_area("Job advertisement text", height=200)
        uploaded_file = None
    elif input_mode == "Public URL":
        input_value = st.text_input("Public HTTP/HTTPS URL")
        uploaded_file = None
    else:
        uploaded_file = st.file_uploader("Upload a recruitment poster", type=["png", "jpg", "jpeg", "webp"])
        input_value = uploaded_file.name if uploaded_file else ""
    official_sources = st.text_area("Official careers/recruitment URLs to check (optional, one per line)")
    if not st.button("Assess vacancy", type="primary"):
        return
    if not str(input_value or "").strip():
        st.warning("Provide pasted text or a public URL.")
        return
    try:
        if input_mode == "Public URL":
            page = fetch_public_page(input_value)
            content_type = str(page.get("content_type") or "").lower()
            extracted = extract_text(page.get("content"), is_html="html" in content_type or "xhtml" in content_type)
            retrieval = {"status": page.get("status", "unknown"), "url": page.get("url", input_value), "content_type": content_type}
        elif input_mode == "Poster image":
            image_result = extract_image_text(uploaded_file.getvalue(), uploaded_file.name)
            for warning in image_result["warnings"]:
                st.warning(warning)
            if not image_result["text"].strip():
                st.error("The poster could not be converted into meaningful text.")
                st.info("Authorization remains unresolved because OCR/extraction failed.")
                return
            extracted = extract_text(image_result["text"])
            retrieval = {"status": image_result["status"], "source": "poster image", "content_hash": image_result["content_hash"], "observed_at": image_result["observed_at"]}
            repo = Repository(DEFAULT_DATABASE)
            try:
                repo.initialize()
                advertisement_id = repo.add_advertisement(input_type="poster", source_url=None, raw_text=image_result["text"], retrieval_status=image_result["status"])
                repo.add_source_record(advertisement_id=advertisement_id, source_type="poster_image", source_url=None, content_hash=image_result["content_hash"], raw_content=uploaded_file.getvalue(), extracted_text=image_result["text"], retrieval_status=image_result["status"], warnings=image_result["warnings"])
            finally:
                repo.close()
        else:
            extracted = extract_text(input_value)
            retrieval = {"status": "available", "source": "user-pasted text"}
    except (UnsafeURL, FetchError, ValueError, OSError) as exc:
        logger.exception("Verification input failed")
        st.error(f"The advertisement could not be retrieved or processed: {exc}")
        st.info("This is a retrieval/extraction limitation, not evidence of fraud.")
        return
    if not extracted.description.strip():
        st.error("No meaningful job-advertisement text could be extracted.")
        st.info("Authorization remains unresolved because extraction failed.")
        return
    for warning in extracted.warnings:
        st.warning(warning)
    st.subheader("Extracted vacancy")
    st.json(extracted.to_dict())
    sources = [line.strip() for line in official_sources.splitlines() if line.strip()]
    evidence = collect_vacancy_evidence(extracted, candidate_official_sources(extracted, retrieval.get("url"), sources), fetch_public_page)
    st.subheader("Employer identity")
    st.info("Unresolved until an employer-domain relationship is supported. Employer existence alone does not authorize this vacancy.")
    st.subheader("Vacancy evidence")
    for item in evidence:
        st.write(f"{item['evidence_state'].upper()} — {item['source_url'] or 'No source URL'}")
        st.caption(f"{item['retrieval_status']}: {item['rationale']}")
        st.json({"source_type": item["source_type"], "observed_at": item["observed_at"], "summary": item["summary"], "details": item["details"]})
    naive_result = naive(evidence)
    lineage_result = lineage_aware(evidence)
    failures = sum(item["retrieval_status"] in {"failed", "unavailable"} for item in evidence)
    decision = assess(employer_identity="unresolved", vacancy_evidence_state=lineage_result.state, evidence_available=lineage_result.effective_sources, retrieval_failures=failures)
    st.subheader("Assessment")
    st.json({"naive": naive_result.__dict__, "lineage_aware": lineage_result.__dict__, "decision": decision})


verification_page()
