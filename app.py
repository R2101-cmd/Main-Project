"""Streamlit interface for vacancy-authorization evidence review."""

from __future__ import annotations

import html
import logging
from collections import Counter
from datetime import datetime, timezone

import streamlit as st

from src.aggregation.rules import lineage_aware, naive
from src.config import DEFAULT_DATABASE
from src.database.repository import Repository
from src.decision.policy import assess, qualifying_independent_source_count
from src.evidence.collector import EvidenceObservation, candidate_official_sources, collect_vacancy_evidence
from src.evidence.authority_config import load_authority_config, authority_for_employer
from src.ingestion.content_extractor import extract_text
from src.ingestion.image_extractor import extract_image_text
from src.ingestion.url_fetcher import FetchError, UnsafeURL, fetch_public_page
from src.ui_support import aggregation_summary, comparison_rows, evidence_ledger_rows, evidence_stats


logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="TrustHire | Safer job checks",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --vg-ink: #10233f;
            --vg-muted: #667085;
            --vg-border: #e5eaf1;
            --vg-surface: #ffffff;
            --vg-blue: #2563eb;
            --vg-green: #16805d;
            --vg-amber: #b7791f;
            --vg-red: #c2413c;
        }
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"], body { background: #f6f8fb; color: #111827 !important; }
        [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li, label, legend, [data-testid="stWidgetLabel"] *, [data-baseweb="tab"], [data-testid="stExpander"] * { color: #111827 !important; }
        [data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stMetricDelta"] { color: #111827 !important; }
        [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea { color: #111827 !important; background: #ffffff !important; }
        [data-testid="stTextInput"] input::placeholder, [data-testid="stTextArea"] textarea::placeholder { color: #667085 !important; opacity: 1; }
        [data-baseweb="tab-list"] { border-bottom-color: #d9e1ec !important; }
        [data-baseweb="tab-highlight"] { background-color: #2563eb !important; }
        [data-testid="stHeader"] { background: rgba(246,248,251,.92); }
        section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div, section[data-testid="stSidebar"] > div > div, section[data-testid="stSidebar"] [data-testid="stSidebarContent"], section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"], [data-testid="stSidebarCollapsedControl"] { background: #0d2342 !important; }
        section[data-testid="stSidebar"] * { background-color: transparent !important; }
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"], section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { background-color: #0d2342 !important; }
        [data-testid="stSidebar"] { border-right: 1px solid #173a67; }
        [data-testid="stSidebar"] * { color: #f7fbff !important; }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * { color: #ffffff !important; }
        [data-testid="stSidebar"] .stCaption { color: #c6d6ea !important; }
        [data-testid="stSidebar"] hr { border-color: rgba(198,214,234,.22); }
        .vg-brand { display:flex; gap:12px; align-items:center; padding: 8px 0 26px; }
        .vg-brand-mark { width:42px; height:42px; border-radius:13px; display:flex; align-items:center; justify-content:center; background:linear-gradient(135deg,#4f8cff,#7dd3fc) !important; color:#10233f !important; font-size:22px; box-shadow:0 8px 22px rgba(0,0,0,.18); }
        .vg-brand-title { font-weight:800; letter-spacing:-.02em; font-size:18px; }
        .vg-brand-sub { font-size:11px; color:#c6d6ea; margin-top:2px; }
        .vg-hero { padding: 18px 0 28px; max-width: 920px; }
        .vg-eyebrow { color:#2563eb; font-weight:800; text-transform:uppercase; letter-spacing:.12em; font-size:11px; }
        .vg-hero h1 { font-size: clamp(34px, 5vw, 58px); line-height:1.02; letter-spacing:-.055em; color:#10233f; margin:6px 0 14px; }
        .vg-hero p { color:#475467; max-width:680px; font-size:17px; line-height:1.55; margin:0; }
        .vg-card { background:var(--vg-surface); border:1px solid var(--vg-border); border-radius:20px; padding:22px; box-shadow:0 10px 32px rgba(16,35,63,.055); }
        .vg-card-title { font-weight:750; color:#10233f; font-size:16px; margin-bottom:4px; }
        .vg-card-sub { color:#475467; font-size:13px; }
        .vg-mini-card { background:#fbfcfe; border:1px solid #e6ebf2; border-radius:16px; padding:14px 16px; margin:4px 0 10px; min-height:58px; }
        .vg-mini-label { color:#667085; font-size:11px; font-weight:750; text-transform:uppercase; letter-spacing:.08em; }
        .vg-mini-value { color:#10233f; font-size:15px; font-weight:700; margin-top:5px; overflow-wrap:anywhere; }
        .vg-pill { display:inline-flex; align-items:center; gap:6px; border-radius:999px; padding:5px 10px; font-size:12px; font-weight:750; text-transform:uppercase; letter-spacing:.05em; }
        .vg-pill-supported, .vg-pill-ready { background:#e5f7ef; color:#137653; }
        .vg-pill-unresolved, .vg-pill-pending { background:#fff3d8; color:#9a6819; }
        .vg-pill-contradicted, .vg-pill-blocked { background:#fde8e7; color:#b33631; }
        .vg-pill-unavailable, .vg-pill-neutral { background:#edf1f6; color:#596579; }
        .vg-decision { border-radius:18px; padding:18px 20px; border:1px solid var(--vg-border); background:#fff; }
        .vg-decision-supported { border-left:5px solid var(--vg-green); }
        .vg-decision-unresolved { border-left:5px solid var(--vg-amber); }
        .vg-decision-contradicted { border-left:5px solid var(--vg-red); }
        .vg-decision-title { font-size:20px; font-weight:800; color:#10233f; }
        .vg-small { color:#475467; font-size:12px; }
        .vg-section { margin: 30px 0 10px; color:#10233f; font-size:21px; font-weight:800; letter-spacing:-.025em; }
        .vg-footnote { border-top:1px solid var(--vg-border); margin-top:28px; padding-top:14px; color:#7a8798; font-size:12px; }
        div[data-testid="stMetric"] { background:#fff; border:1px solid var(--vg-border); border-radius:16px; padding:12px 14px; box-shadow:0 5px 18px rgba(16,35,63,.035); }
        div[data-testid="stMetricLabel"] { color:#475467 !important; }
        .stButton > button[kind="primary"] { border-radius:12px; font-weight:750; min-height:44px; }
        .stTextInput input, .stTextArea textarea { border-radius:12px; }
        [data-testid="stForm"] { background:#fff; border:1px solid #e5eaf1; border-radius:20px; padding:22px 22px 10px; box-shadow:0 10px 32px rgba(16,35,63,.055); }
        [data-testid="stFileUploader"] section { border-radius:14px; border-color:#cfd9e8; background:#fbfcfe; }
        [data-baseweb="tab-list"] { gap:22px; }
        [data-baseweb="tab"] { padding-left:0 !important; padding-right:0 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _status_pill(label: str, status: str) -> str:
    safe_status = str(status or "neutral").lower().replace(" ", "-")
    return f'<span class="vg-pill vg-pill-{html.escape(safe_status)}">{html.escape(label)}</span>'


def _host(url: str | None) -> str:
    if not url:
        return "No source URL"
    return url.split("//", 1)[-1].split("/", 1)[0]


def _unavailable_url_review(url: str, error: Exception) -> dict:
    """Return a conservative review when the submitted page cannot be retrieved."""
    extracted = extract_text("")
    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    evidence = EvidenceObservation(
        source_url=url,
        source_type="public_source_unknown_control",
        observed_at=observed_at,
        retrieval_status="failed",
        evidence_state="unavailable",
        summary="The submitted public page could not be retrieved.",
        rationale=f"Retrieval failed without asserting anything about authorization: {type(error).__name__}: {error}",
        details={"submitted_url": url, "retrieval_error": type(error).__name__, "error": str(error), "http_status": None, "extraction_status": "not_attempted"},
    ).to_dict()
    naive_result = naive([evidence])
    lineage_result = lineage_aware([evidence])
    decision = assess(employer_identity="unresolved", vacancy_evidence_state=lineage_result.state, evidence_available=0, retrieval_failures=1, vacancy_correspondence=False, source_authoritative=False, freshness_status="unresolved", independent_evidence_count=0)
    return {
        "extracted": extracted,
        "retrieval": {"status": "failed", "url": url},
        "warnings": ["The submitted page was unreachable or blocked. Authorization remains unresolved; this is not evidence of fraud."],
        "evidence": [evidence],
        "naive": naive_result,
        "lineage": lineage_result,
        "decision": decision,
        "retrieval_failures": 1,
    }


def _assess_input(input_mode: str, input_value: str, uploaded_file, official_sources: str, poster_text_override: str | None = None, poster_ocr_result: dict | None = None) -> dict:
    warnings: list[str] = []
    if not str(input_value or "").strip():
        raise ValueError("Provide pasted text, a public URL, or a poster image.")

    if input_mode == "Public URL":
        try:
            page = fetch_public_page(input_value)
        except (FetchError, OSError) as exc:
            return _unavailable_url_review(input_value, exc)
        content_type = str(page.get("content_type") or "").lower()
        extracted = extract_text(page.get("content"), is_html="html" in content_type or "xhtml" in content_type)
        retrieval = {"status": page.get("status", "unknown"), "url": page.get("url", input_value), "content_type": content_type}
    elif input_mode == "Poster image":
        if uploaded_file is None:
            raise ValueError("Upload a PNG, JPG, JPEG, or WEBP poster first.")
        image_result = poster_ocr_result or extract_image_text(uploaded_file.getvalue(), uploaded_file.name)
        warnings.extend(image_result["warnings"])
        poster_text = poster_text_override if poster_text_override is not None else image_result.get("text", "")
        if not poster_text.strip():
            raise ValueError("No OCR text is available. Correct the OCR text manually or install/configure Tesseract before assessment.")
        extracted = extract_text(poster_text)
        retrieval = {"status": image_result["status"], "source": "poster image", "content_hash": image_result["content_hash"], "observed_at": image_result["observed_at"], "raw_ocr_text": image_result.get("raw_text", image_result.get("text", "")), "ocr_metadata": {key: image_result.get(key) for key in ("engine_path", "orientation_degrees", "preprocessing", "selected_attempt", "attempts", "error_code")}}
        repo = Repository(DEFAULT_DATABASE)
        try:
            repo.initialize()
            advertisement_id = repo.add_advertisement(input_type="poster", source_url=None, raw_text=image_result["text"], retrieval_status=image_result["status"])
            repo.add_source_record(advertisement_id=advertisement_id, source_type="poster_image", source_url=None, content_hash=image_result["content_hash"], raw_content=uploaded_file.getvalue(), extracted_text=poster_text, retrieval_status=image_result["status"], warnings=image_result["warnings"] + (["OCR text was manually corrected before assessment."] if poster_text_override is not None else []))
        finally:
            repo.close()
    else:
        extracted = extract_text(input_value)
        retrieval = {"status": "available", "source": "user-pasted text"}

    if not extracted.description.strip():
        raise ValueError("No meaningful job-advertisement text could be extracted. Authorization remains unresolved.")
    warnings.extend(extracted.warnings)
    explicit_urls = [line.strip() for line in official_sources.splitlines() if line.strip()]
    source_urls = candidate_official_sources(extracted, retrieval.get("url"), explicit_urls)
    authority_config = load_authority_config()
    authorized_domains, authority_mappings = authority_for_employer(extracted.employer, authority_config)
    evidence = collect_vacancy_evidence(extracted, source_urls, fetch_public_page, authorized_domains=authorized_domains, authority_mappings=authority_mappings, max_current_posting_age_days=authority_config["max_current_posting_age_days"])
    naive_result = naive(evidence)
    lineage_result = lineage_aware(evidence)
    failures = sum(item.get("retrieval_status") in {"failed", "unavailable"} for item in evidence)
    identity_states = [((item.get("details") or {}).get("matching_explanation") or {}).get("employer_identity_status") for item in evidence]
    employer_identity = "verified" if "verified" in identity_states else "contradicted" if "contradicted" in identity_states else "unresolved"
    qualifying = [item for item in evidence if item.get("source_relationship") in {"independent", "copied_derived"} and item.get("lineage_review_status") == "adjudicated" and item.get("verification_status") in {"independently_supported", "independently_contradicted"}]
    source_authoritative = bool(qualifying) and all(((item.get("details") or {}).get("authority_assessment") or {}).get("authority_level") == "employer_authoritative" for item in qualifying)
    vacancy_correspondence = bool(qualifying) and all(((item.get("details") or {}).get("vacancy_match") is True) for item in qualifying)
    freshness_values = [(((item.get("details") or {}).get("matching_explanation") or {}).get("freshness") or {}).get("status") for item in qualifying]
    freshness_status = "current" if freshness_values and all(value == "current" for value in freshness_values) else "unresolved"
    conflicts = sorted({value for item in qualifying for value in ((item.get("details") or {}).get("matching_explanation") or {}).get("material_conflicts", [])})
    decision = assess(employer_identity=employer_identity, vacancy_evidence_state=lineage_result.state, evidence_available=lineage_result.effective_sources, retrieval_failures=failures,
        vacancy_correspondence=vacancy_correspondence, source_authoritative=source_authoritative, freshness_status=freshness_status,
        independent_evidence_count=qualifying_independent_source_count(evidence), supporting_evidence_count=lineage_result.supporting_sources,
        contradicting_evidence_count=lineage_result.contradicting_sources, material_conflicts=conflicts)
    return {"extracted": extracted, "retrieval": retrieval, "warnings": warnings, "evidence": evidence, "naive": naive_result, "lineage": lineage_result, "decision": decision, "retrieval_failures": failures, "authority_configuration": {"matched_mappings": authority_mappings, "max_current_posting_age_days": authority_config["max_current_posting_age_days"]}}


def _render_clean_assessment(result: dict) -> None:
    """Applicant-facing assessment view; research details remain available below."""
    extracted = result["extracted"]
    evidence = result.get("evidence", [])
    decision = result["decision"]
    state = decision.get("vacancy_authorization", "unresolved")
    state_label = {"supported": "Potentially supported", "contradicted": "Contradiction identified", "unresolved": "Authorization could not be verified"}.get(state, "Authorization could not be verified")
    if state == "unresolved":
        reason = "An external source could not be accessed, so this check remains incomplete." if result.get("retrieval_failures") else "Available public evidence was insufficient to confirm that this specific vacancy is authorized."
    elif state == "contradicted":
        reason = "A public source contains vacancy details that conflict with the advertisement."
    else:
        reason = "Available public evidence matches the vacancy details, but verify the application route yourself."
    state_class = "supported" if state == "supported" else "contradicted" if state == "contradicted" else "unresolved"

    st.markdown('<div class="vg-section">Assessment result</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="vg-decision vg-decision-{state_class}"><div class="vg-small">VACANCY REVIEW</div><div class="vg-decision-title">{html.escape(state_label)}</div><div class="vg-card-sub" style="margin-top:8px">{html.escape(reason)}</div></div>', unsafe_allow_html=True)
    status_cols = st.columns(3)
    status_cols[0].metric("Employer identity", str(decision.get("employer_identity", "unresolved")).replace("_", " ").title())
    status_cols[1].metric("Vacancy authorization", state.title())
    status_cols[2].metric("Fraud outcome", str(decision.get("fraud_outcome", "unresolved")).replace("_", " ").title())
    st.caption("An unresolved result is not a finding of fraud. Confirm the employer and application details independently.")
    if result.get("warnings"):
        with st.expander("Review notes"):
            for warning in result["warnings"]:
                st.warning(warning)

    fields = extracted.to_dict()
    display_fields = [("💼", "Job title", fields.get("title")), ("🏢", "Employer", fields.get("employer")), ("📍", "Location", fields.get("location")), ("📅", "Interview dates", fields.get("posting_date") or fields.get("date_posted") or fields.get("valid_through")), ("💰", "Salary or stipend", fields.get("salary")), ("✉️", "Application or contact", fields.get("application_url") or fields.get("contact") or fields.get("recruiter")), ("🎓", "Qualification / employment", fields.get("employment_type")), ("🔖", "Job ID", fields.get("job_id"))]
    available_fields = [(icon, label, value) for icon, label, value in display_fields if value not in (None, "")]
    if available_fields or fields.get("description"):
        st.markdown('<div class="vg-section">Vacancy details</div>', unsafe_allow_html=True)
        if available_fields:
            cols = st.columns(2)
            for index, (icon, label, value) in enumerate(available_fields):
                with cols[index % 2]:
                    st.markdown(f'<div class="vg-mini-card"><div class="vg-mini-label">{icon} &nbsp; {html.escape(label)}</div><div class="vg-mini-value">{html.escape(str(value))}</div></div>', unsafe_allow_html=True)
        if fields.get("description"):
            st.markdown("**Description**")
            st.write(fields["description"])

    stats = evidence_stats(evidence)
    meaningful = stats["relevant_evidence_sources"]
    if meaningful or stats["retrieval_failures"]:
        st.markdown('<div class="vg-section">Evidence summary</div>', unsafe_allow_html=True)
        if meaningful:
            st.info(f"{meaningful} relevant public source(s) were reviewed.")
        if stats["retrieval_failures"]:
            st.warning("An external source could not be accessed, so this check remains incomplete.")

    with st.expander("Advanced diagnostics"):
        evidence_rows = evidence_ledger_rows(evidence)
        if evidence_rows:
            st.markdown("**Evidence ledger**")
            st.dataframe(evidence_rows, hide_index=True, use_container_width=True)
        comparison = comparison_rows(extracted, evidence)
        if comparison:
            st.markdown("**Source comparison**")
            st.dataframe(comparison, hide_index=True, use_container_width=True)
        lineage = result.get("lineage")
        naive_result = result.get("naive")
        if lineage or naive_result:
            st.markdown("**Lineage-aware aggregation**")
            st.json({"ordinary_state": getattr(naive_result, "state", None), "lineage_aware_state": getattr(lineage, "state", None), "ordinary_effective_sources": getattr(naive_result, "effective_sources", None), "lineage_effective_sources": getattr(lineage, "effective_sources", None)})
        retrieval = result.get("retrieval", {})
        ocr_metadata = retrieval.get("ocr_metadata") if isinstance(retrieval, dict) else None
        if ocr_metadata:
            st.markdown("**OCR diagnostics**")
            st.json(ocr_metadata)
            if retrieval.get("raw_ocr_text"):
                st.text(retrieval["raw_ocr_text"])
        technical = {"extraction_warnings": fields.get("warnings", []), "extraction_conflicts": fields.get("conflicts", {}), "candidate_source_urls": fields.get("candidate_source_urls", []), "retrieval": retrieval}
        if any(technical.values()):
            st.markdown("**Technical extraction and retrieval details**")
            st.json(technical)


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="vg-brand"><div class="vg-brand-mark">🛡️</div><div><div class="vg-brand-title">TrustHire</div><div class="vg-brand-sub">Authorization evidence workspace</div></div></div>', unsafe_allow_html=True)
        st.markdown("### A clearer way to check a job ad")
        st.caption("Review a vacancy against publicly available recruitment information before you apply.")
        st.divider()
        st.markdown("### What you can do")
        st.markdown("• Check public vacancy sources\n\n• Compare role-specific details\n\n• Review evidence availability\n\n• Keep uncertain cases visible")
        st.divider()
        st.caption("Missing information is shown as unresolved — never treated as proof that a job is fraudulent.")


def _render_input_panel() -> None:
    st.markdown('<div class="vg-section">Check a job vacancy</div>', unsafe_allow_html=True)
    st.markdown('<div class="vg-card-sub">Choose the format you have. For the most useful review, include the complete job title, employer, location, and application details.</div>', unsafe_allow_html=True)
    input_mode = st.radio("Source format", ["Pasted text", "Public URL", "Poster image"], horizontal=True, key="input_mode")
    with st.form("verification_form", clear_on_submit=False):
        if input_mode == "Pasted text":
            input_value = st.text_area("Advertisement text", height=190, placeholder="Paste the complete job advertisement, including employer, title, location, and application route…")
            uploaded_file = None
        elif input_mode == "Public URL":
            input_value = st.text_input("Public HTTP/HTTPS vacancy URL", placeholder="https://careers.example.com/jobs/…")
            uploaded_file = None
        else:
            uploaded_file = st.file_uploader("Recruitment poster", type=["png", "jpg", "jpeg", "webp"])
            input_value = uploaded_file.name if uploaded_file else ""
        official_sources = st.text_area("Official careers or recruitment URLs (optional)", height=90, placeholder="One URL per line\nhttps://careers.example.com/jobs/…")
        submitted = st.form_submit_button("Assess vacancy evidence", type="primary", use_container_width=True)
    if submitted:
        try:
            with st.spinner("Extracting fields and checking permitted public sources…"):
                st.session_state["verification_result"] = _assess_input(input_mode, input_value, uploaded_file, official_sources)
            st.success("Review completed. Inspect the evidence ledger before making a decision.")
        except (UnsafeURL, FetchError, ValueError, OSError) as exc:
            logger.exception("Verification input failed")
            st.session_state.pop("verification_result", None)
            st.error(f"The advertisement could not be retrieved or processed: {exc}")
            st.info("This is a retrieval or extraction limitation, not evidence of fraud.")


def _render_assessment(result: dict) -> None:
    extracted = result["extracted"]
    evidence = result["evidence"]
    lineage = result["lineage"]
    decision = result["decision"]
    state = decision.get("vacancy_authorization", "unresolved")
    state_label = {"supported": "Potentially supported", "contradicted": "Contradiction identified", "unresolved": "Authorization unresolved"}.get(state, state.title())
    stats = evidence_stats(evidence)
    source_states = Counter(item.get("evidence_state", "unavailable") for item in evidence if isinstance(item, dict))
    aggregation = aggregation_summary(evidence, result["naive"], lineage)
    decision_class = "supported" if state == "supported" else "contradicted" if state == "contradicted" else "unresolved"

    st.markdown('<div class="vg-section">Assessment overview</div>', unsafe_allow_html=True)
    st.caption("Use this review as a helpful signal alongside your own checks.")
    st.markdown(f'<div class="vg-decision vg-decision-{decision_class}"><div class="vg-small">VACANCY AUTHORIZATION SIGNAL</div><div class="vg-decision-title">{html.escape(state_label)} &nbsp; {_status_pill(state, state)}</div><div class="vg-card-sub" style="margin-top:8px">{html.escape(decision["reason"])}</div></div>', unsafe_allow_html=True)
    if result["warnings"]:
        with st.expander(f"Extraction and retrieval notes ({len(result['warnings'])})"):
            for warning in result["warnings"]:
                st.warning(warning)

    summary_cols = st.columns(5)
    summary_cols[0].metric("Employer identity", str(decision.get("employer_identity", "unresolved")).title())
    summary_cols[1].metric("Vacancy authorization", state.title())
    summary_cols[2].metric("Fraud outcome", str(decision.get("fraud_outcome", "unresolved")).replace("_", " ").title())
    summary_cols[3].metric("Evidence availability", f"{stats['successfully_retrieved']}/{stats['availability_denominator']}")
    summary_cols[4].metric("Retrieval status", "Complete" if stats["retrieval_failures"] == 0 else f"{stats['retrieval_failures']} gap(s)")
    st.caption(f"The live policy requires {decision.get('minimum_independent_sources', 2)} adjudicated independent source groups; current count: {decision.get('independent_evidence_count', 0)}. Fraud outcome remains separate from authorization.")
    st.caption(f"Availability coverage: {stats['successfully_retrieved']}/{stats['availability_denominator']} source records retrieved ({stats['availability_coverage']:.0%}). Availability is not authorization.")
    st.progress(stats["availability_coverage"], text="Retrieved source coverage")

    stats_cols = st.columns(6)
    stats_cols[0].metric("Source records", stats["total_source_records"])
    stats_cols[1].metric("Relevant evidence", stats["relevant_evidence_sources"])
    stats_cols[2].metric("Supporting", stats["supporting_items"])
    stats_cols[3].metric("Contradicting", stats["contradicting_items"])
    stats_cols[4].metric("Unverified", stats["unverified_items"])
    stats_cols[5].metric("Retrieval failures", stats["retrieval_failures"])

    overview_tab, evidence_tab, fields_tab = st.tabs(["Summary", "Evidence ledger", "Extracted fields"])
    with overview_tab:
        left, right = st.columns([1, 1])
        with left:
            st.markdown('<div class="vg-card"><div class="vg-card-title">Public source signal</div><div class="vg-card-sub">What the available sources suggest about this vacancy.</div>', unsafe_allow_html=True)
            st.metric("Signal", result["naive"].state.title())
            st.caption(result["naive"].explanation)
            st.markdown("</div>", unsafe_allow_html=True)
        with right:
            st.markdown('<div class="vg-card"><div class="vg-card-title">Lineage-aware aggregation (C)</div><div class="vg-card-sub">Adjudicated independent evidence only; unknown lineage remains unresolved.</div>', unsafe_allow_html=True)
            st.metric("Signal", lineage.state.title())
            st.caption(lineage.explanation)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="vg-section">Source comparison</div>', unsafe_allow_html=True)
        comparison_cols = st.columns(3)
        comparison_cols[0].metric("Sources reviewed", aggregation["naive_effective_sources"])
        comparison_cols[1].metric("Consistent sources", aggregation["lineage_effective_sources"])
        comparison_cols[2].metric("Records compared", aggregation["consolidated_records"])
        st.caption(aggregation["lineage_review_note"])
        st.caption("A source match helps build evidence, but it does not replace verification of the employer relationship and vacancy-specific authorization.")
        st.info("A verified employer does not automatically confirm every vacancy. Check the application route carefully and avoid sharing sensitive information until you are comfortable.")
    with evidence_tab:
        rows = evidence_ledger_rows(evidence)
        st.dataframe(rows, hide_index=True, use_container_width=True)
        chart = {"Supported": [source_states.get("supported", 0)], "Contradicted": [source_states.get("contradicted", 0)], "Unverified": [source_states.get("unverified", 0)], "Unavailable": [source_states.get("unavailable", 0)]}
        st.bar_chart(chart, height=190)
        for index, item in enumerate(evidence, start=1):
            with st.expander(f"Evidence {index} · {item.get('evidence_state', 'unavailable').title()} · {_host(item.get('source_url'))}"):
                st.write(item.get("rationale", "No rationale recorded."))
                details = item.get("details") if isinstance(item.get("details"), dict) else {}
                st.json({
                    "source_url": item.get("source_url"),
                    "source_type": item.get("source_type"),
                    "retrieval_status": item.get("retrieval_status"),
                    "observed_at": item.get("observed_at"),
                    "http_status": details.get("http_status"),
                    "extraction_status": details.get("extraction_status"),
                    "summary": item.get("summary"),
                    "failure_reason": details.get("error") or details.get("retrieval_error"),
                    "extraction_warnings": details.get("extraction_warnings") or details.get("candidate_warnings"),
                    "details": details,
                })
                st.caption(f"Lineage: {item.get('source_relationship', 'unknown')} · {item.get('lineage_review_status', 'not_assessed')}. Similarity findings, when present, are candidates only and are not used as adjudicated relationships.")
        st.markdown('<div class="vg-section">Field-by-field comparison</div>', unsafe_allow_html=True)
        field_rows = comparison_rows(extracted, evidence)
        if field_rows:
            st.dataframe(field_rows, hide_index=True, use_container_width=True)
            st.caption("A matched field helps compare the advertisement with a source; it does not by itself prove vacancy authorization.")
        else:
            st.info("No source comparison fields are available. This is not evidence of fraud.")
    with fields_tab:
        fields = extracted.to_dict()
        field_cols = st.columns(2)
        visible_index = 0
        for key, value in fields.items():
            if key in {"description", "warnings", "conflicts", "evidence", "candidate_source_urls"}:
                continue
            with field_cols[visible_index % 2]:
                st.markdown(f"**{key.replace('_', ' ').title()}**")
                st.write(value or "Not extracted")
            visible_index += 1
        with st.expander("Description and extracted source links"):
            st.write(fields.get("description") or "No description extracted.")
            if fields.get("candidate_source_urls"):
                st.write(fields["candidate_source_urls"])
        st.caption("Dates distinguish original posting, last modification, validity end and retrieval time. A missing field is shown as not extracted; it is not treated as a contradiction.")
def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="vg-brand"><div class="vg-brand-mark">🛡️</div><div><div class="vg-brand-title">TrustHire</div><div class="vg-brand-sub">Make every application count</div></div></div>', unsafe_allow_html=True)
        st.markdown("### A clearer way to check a job ad")
        st.caption("Review a vacancy against publicly available recruitment information before you apply.")
        st.divider()
        st.markdown("### How it works")
        st.markdown("1. Share the job ad\n\n2. We compare its details with public sources\n\n3. You get a clear review summary")
        st.divider()
        st.caption("Missing information is shown as unresolved — never treated as proof that a job is fraudulent.")


def _render_input_panel() -> None:
    st.markdown('<div class="vg-section">Check a job vacancy</div>', unsafe_allow_html=True)
    st.markdown('<div class="vg-card-sub">Choose the format you have. For the most useful review, include the complete job title, employer, location, and application details.</div>', unsafe_allow_html=True)
    input_mode = st.radio("Source format", ["Pasted text", "Public URL", "Poster image"], horizontal=True, key="input_mode")
    with st.form("verification_form", clear_on_submit=False):
        if input_mode == "Pasted text":
            input_value = st.text_area("Job advertisement", height=190, placeholder="Paste the complete job advertisement here")
            uploaded_file = None
        elif input_mode == "Public URL":
            input_value = st.text_input("Job advertisement URL", placeholder="https://careers.example.com/jobs/…")
            uploaded_file = None
        else:
            uploaded_file = st.file_uploader("Upload a recruitment poster", type=["png", "jpg", "jpeg", "webp"])
            input_value = uploaded_file.name if uploaded_file else ""
        official_sources = st.text_area("Official company or careers links (optional)", height=90, placeholder="Add one link per line")
        submit_label = "Extract poster text" if input_mode == "Poster image" else "Review this vacancy"
        submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)
    if submitted:
        try:
            if input_mode == "Poster image":
                if uploaded_file is None:
                    raise ValueError("Upload a PNG, JPG, JPEG, or WEBP poster first.")
                with st.spinner("Preprocessing poster and extracting text…"):
                    ocr_result = extract_image_text(uploaded_file.getvalue(), uploaded_file.name)
                st.session_state["poster_ocr_preview"] = ocr_result
                preview_fields = extract_text(ocr_result.get("text", "")) if ocr_result.get("text", "").strip() else extract_text("")
                st.session_state["poster_extracted_fields"] = preview_fields.to_dict()
                for field_name in ("title", "employer", "location", "salary", "contact", "application_url", "employment_type", "job_id", "posting_date", "description"):
                    st.session_state[f"poster_edit_{field_name}"] = preview_fields.to_dict().get(field_name) or ""
                st.session_state["poster_official_sources"] = official_sources
                st.session_state.pop("verification_result", None)
                if ocr_result.get("text", "").strip():
                    st.success("OCR completed. Review and correct the text below before assessment.")
                else:
                    for warning in ocr_result.get("warnings", []):
                        st.warning(warning)
            else:
                with st.spinner("Reviewing the vacancy details…"):
                    st.session_state["verification_result"] = _assess_input(input_mode, input_value, uploaded_file, official_sources)
                st.success("Review complete. Scroll down to see what was found.")
        except (UnsafeURL, FetchError, ValueError, OSError) as exc:
            logger.exception("Verification input failed")
            st.session_state.pop("verification_result", None)
            st.error(f"The advertisement could not be retrieved or processed: {exc}")
            st.info("This is a retrieval or extraction limitation, not evidence of fraud.")
    if input_mode == "Poster image" and st.session_state.get("poster_ocr_preview") and not st.session_state.get("verification_result"):
        preview = st.session_state["poster_ocr_preview"]
        draft = st.session_state.get("poster_extracted_fields", {})
        st.markdown('<div class="vg-section">Extracted vacancy preview</div>', unsafe_allow_html=True)
        preview_fields = [("Job title", draft.get("title")), ("Employer", draft.get("employer")), ("Location", draft.get("location")), ("Salary or stipend", draft.get("salary")), ("Application or contact", draft.get("application_url") or draft.get("contact")), ("Qualification / employment", draft.get("employment_type"))]
        available_preview = [(label, value) for label, value in preview_fields if value]
        if available_preview:
            cols = st.columns(2)
            for index, (label, value) in enumerate(available_preview):
                with cols[index % 2]:
                    st.markdown(f'<div class="vg-mini-card"><div class="vg-mini-label">{html.escape(label)}</div><div class="vg-mini-value">{html.escape(str(value))}</div></div>', unsafe_allow_html=True)
        else:
            st.info("We could not identify the main vacancy details yet. You can add them below.")
        with st.expander("Edit extracted details"):
            edit_cols = st.columns(2)
            edit_specs = [("Job title", "title"), ("Employer", "employer"), ("Location", "location"), ("Salary or stipend", "salary"), ("Application or contact", "contact"), ("Qualification / employment", "employment_type"), ("Job ID", "job_id"), ("Posting date", "posting_date")]
            for index, (label, field_name) in enumerate(edit_specs):
                with edit_cols[index % 2]:
                    st.text_input(label, key=f"poster_edit_{field_name}")
            st.text_area("Description and responsibilities", key="poster_edit_description", height=140)
        corrected_parts = []
        for label, field_name in (("Job title", "title"), ("Employer", "employer"), ("Location", "location"), ("Salary", "salary"), ("Application", "contact"), ("Qualification", "employment_type"), ("Job ID", "job_id"), ("Posting date", "posting_date")):
            value = st.session_state.get(f"poster_edit_{field_name}", "").strip()
            if value:
                corrected_parts.append(f"{label}: {value}")
        description = st.session_state.get("poster_edit_description", "").strip()
        if description:
            corrected_parts.append(description)
        corrected = "\n".join(corrected_parts)
        if st.button("Assess vacancy", type="primary"):
            try:
                with st.spinner("Assessing the corrected poster text…"):
                    st.session_state["verification_result"] = _assess_input("Poster image", input_value, uploaded_file, st.session_state.get("poster_official_sources", ""), poster_text_override=corrected, poster_ocr_result=preview)
                st.success("Poster assessment complete. Scroll down to see the extracted fields and decision.")
            except (UnsafeURL, FetchError, ValueError, OSError) as exc:
                logger.exception("Poster assessment failed")
                st.error(f"The poster could not be assessed: {exc}")
                st.info("Correct the OCR text or configure a working Tesseract engine, then try again.")


def main() -> None:
    _inject_styles()
    _render_sidebar()
    st.markdown('<div class="vg-hero"><div class="vg-eyebrow">Make your next application safer</div><h1>Verify the vacancy,<br>not just the employer.</h1><p>Compare a specific job advertisement with public recruitment information, spot missing details, and apply with more confidence.</p></div>', unsafe_allow_html=True)
    _render_input_panel()
    result = st.session_state.get("verification_result")
    if result:
        _render_clean_assessment(result)
    else:
        st.markdown('<div class="vg-card" style="margin-top:26px"><div class="vg-card-title">What you will receive</div><div class="vg-card-sub">A clear summary of the vacancy details found, the public sources reviewed, and any points that still need your attention.</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="vg-footnote">TrustHire reviews publicly available information to help you make more informed decisions. Always verify the employer and application details yourself.</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
