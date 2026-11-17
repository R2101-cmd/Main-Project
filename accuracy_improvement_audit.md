# TrustHire Accuracy Improvement Audit
**Project:** Beyond Fake-Job Classification: Lineage-Aware Evidence for Vacancy Authorization Verification  
**Phase:** 1 — Complete repository audit (no implementation changes made)  
**Date:** 2026-11-14  
**Scope audited:** `app.py`, `src/ingestion/`, `src/evidence/`, `src/lineage/`, `src/aggregation/`, `src/evaluation/`, `src/decision/`, `src/database/`, `src/datasets/`, `src/ml/`, `tests/`, `scripts/`, `research-data/`, `final_completion_package/`, `DatasetCollection/` outputs, and automated-mode artifacts.

---

## 1. Existing system inventory

### 1.1 Verification / evidence-matching algorithms
- **Public retrieval:** `src/ingestion/url_fetcher.py` validates public `http/https` URLs, blocks localhost/private/reserved/link-local/multicast destinations, resolves DNS, follows at most one redirect with revalidation, enforces timeout/size/content-type checks, and returns decoded content with `http_status`, `content_type`, and provenance fields.
- **Content extraction:** `src/ingestion/content_extractor.py` parses HTML/plain text, extracts JobPosting JSON-LD/meta/labeled text, infers employer/title/location/salary/contact/application URL/candidate links, removes noisy UI regions, and records warnings/conflicts/evidence hints.
- **Vacancy evidence collection:** `src/evidence/collector.py` fetches explicitly supplied public source URLs (no search scraping/bypass), extracts candidate vacancy content, compares advertised vs source fields, and emits per-source `EvidenceObservation` records (`source_url/type`, `observed_at`, `retrieval_status`, `evidence_state`, `summary`, `rationale`, `details`).
- **Comparison logic:** `_compare()` matches normalized employer, title, location, and application URL; marks contradiction when employer matches but title differs; assigns `supported` only when vacancy matches and source-domain relationship is `verified_source_domain` or `employer_name_matches_source_domain`; otherwise matching public vacancy becomes `unverified` due to unresolved authorization basis. Details include matched/contradicted fields, advertised/evidence values, vacancy_match, source_scope, authorization_basis, excerpt, and extraction warnings.
- **Candidate source selection:** `candidate_official_sources()` collects explicit URLs, original URL (excluding LinkedIn), extracted vacancy-like links, and application URL; filters to likely job/career/vacancy paths.
- **Automated state mapping (artifacts):** `03_stage4_verification` and `automated_mode` map collected Stage 4E evidence to conservative states (`snapshot_match_only`, `independently_unresolved`, `inaccessible`, with `independently_supported/contradicted/not_comparable` reserved) without claiming human-adjudicated verification.

### 1.2 Lineage detection algorithms
- **Pairwise similarity:** `src/lineage/similarity.py` normalizes text, computes exact match and character TF-IDF (3–5 ngram) cosine similarity, and detects shared contact/application URL. `candidate_relationship()` uses threshold 0.72 (and shared metadata) to suggest `copied_derived`, 0.40–0.72 as `unknown`, else `independent`, with note that manual review is still required.
- **Automated analysis (new mode):** `scripts/automated_mode_analysis.py` processes all 687 candidates (21 original + 459 Stage 4F + 207 Stripe pairs) using existing similarity/signal/metadata fields and assigns `confirmed_by_direct_machine_verifiable_provenance` only if evidenced, else `likely_dependent` / `possible_dependency` / `unknown_relationship`; produces conservative independence estimates. No similarity-based confirmation and unknown not assumed independent.
- **Historical/collection outputs:** DatasetCollection contains lineage candidate CSVs, pair reviews, and similarity-based groupings from staged collection; no human-confirmed lineage in current artifacts.

### 1.3 Aggregation approaches A, B, C
- **A. Text-only:** `src/ml/text_classifier.py` TF-IDF (1–2 word ngrams) + Logistic Regression trained on provided labeled texts; predicts authorization label with warning that text risk ≠ vacancy authorization. Used in `src/evaluation/runner.py` when train/test text labels are available.
- **B. Ordinary aggregation:** `src/aggregation/rules.py::naive()` counts each evidence appearance independently: contradiction dominates, else supported if any supported, else unresolved; effective sources = all items.
- **C. Lineage-aware aggregation:** `lineage_aware()` consolidates only evidence items whose `lineage_group` (or fallback key) is in supplied `dependent_group_keys`, keeping first per seen key, then applies naive aggregation on effective set. Unknown relationships are not auto-merged/confirmed.
- **UI/demo usage:** `app.py` computes naive and lineage-aware from collected evidence (dependent keys inferred from evidence lineage groups in synthetic demo; live assessment passes collected evidence). `scripts/run_synthetic_three_way.py` and `scripts/run_extended_synthetic_three_way.py` evaluate A/B/C on controlled synthetic data.

### 1.4 Confidence / scoring calculations
- **Text model:** returns predicted label and `predict_proba` list when available, plus warning (not calibrated vacancy-authorization probability).
- **Aggregation:** rule-based `AggregateAssessment` (state, supporting/contradicting/effective counts, explanation); no calibrated confidence score, no weighted reliability/freshness/provenance scoring.
- **Evidence comparison:** binary/heuristic field matches and vacancy_match/authorization_basis flags; no continuous match score.
- **Lineage similarity:** cosine score in [0,1], exact/shared-contact/shared-URL booleans; automated lineage uses coarse score bands.

### 1.5 Abstention policies
- **Decision policy (`src/decision/policy.py`):** contradiction → affirmative contradiction; supported with evidence available → evidence-supported assessment; unavailable/failed/no evidence → insufficient evidence/abstain; else unresolved. Missing evidence explicitly not proof of fraud.
- **Aggregation:** returns `unresolved` when no supported/contradicted evidence dominates.
- **Evaluation:** selective metrics track coverage, abstention rate, selective risk, and false assurance (abstained cases remain in eligible denominator where applicable).

### 1.6 Dataset schemas
- **SQLite app schema:** `src/database/schema.sql` (`advertisements`, `claims`, `evidence`, `lineage_relationships`, `annotations`, `model_runs`, `source_records`).
- **JSON schemas:** `schemas/*.schema.json` (advertisement_record, evidence_item, annotation/adjudication forms, collection config/log, lineage review) and `research-data/phase2_v1/schemas/*`.
- **Annotation/eval records:** JSONL records in `data/annotations/` and synthetic benchmarks include ids, vacancy groups/partitions, text/claims, authorization/employer labels (synthetic/provisional contexts), and evidence objects with states/retrieval/lineage fields.
- **DatasetCollection/proposed package:** `table_A/B/C/D`, stage outputs, and `final_research_package` unified CSV schema (cohort/case/employer/source/retrieval/provenance/evidence/lineage/label fields) with data dictionary and manifest.

### 1.7 Existing evaluation methodology
- **Runner:** `src/evaluation/runner.py` validates records/splits/leakage, requires reviewed/non-import labels, checks group leakage and optional frozen manifests/fingerprints, evaluates naive and lineage-aware evidence on test partition and text-only baseline when feasible; reports classification/selective metrics, evidence summaries, warnings, provenance/circularity indicators.
- **Metrics:** `src/evaluation/metrics.py` computes per-class/macro/weighted classification metrics and selective metrics including false assurance (supported prediction for non-supported eligible reference cases, with abstention in coverage not denominator).
- **Automated-mode experiments:** `scripts/run_synthetic_three_way.py`, `scripts/run_extended_synthetic_three_way.py` run A/B/C on controlled synthetic benchmarks with deterministic splits/seeds and per-case/confusion/FA/unresolved outputs; real-world reporting limited to descriptive outputs (no GT metrics) in `automated_mode`.

### 1.8 Existing test coverage
- **73 tests passing (2 warnings):** ingestion/content/image/url safety (`test_extraction.py`, `test_image_extractor.py`, `test_url_fetcher.py`), evidence collection (`test_evidence_collection.py`), aggregation/decision/core (`test_core.py`), DB (`test_database.py`), dataset import (`test_dataset_importer.py`, `test_import_missing_id.py`), metrics/runner (`test_metrics.py`, `test_metrics_extended.py`, `test_runner.py`), collection readiness (`test_collection_readiness.py`), UI support (`test_ui_support.py`), and automated-mode behaviors/non-fabrication/benchmark separation (`test_automated_mode.py`).
- **App smoke:** Streamlit AppTest script passed in automated mode.

### 1.9 Duplicated / overlapping functionality
- Multiple lineage candidate representations and pipelines (historical DatasetCollection outputs, `src/lineage/similarity.py`, automated scoring script, package/review artifacts) with overlapping but non-unified scoring logic.
- Evidence-state/verification-state mappings appear in collector, aggregation, decision, evaluation, and artifact scripts with slightly different vocabularies/proxies.
- Similarity/normalization helpers are implemented in more than one place (e.g. normalization in collector/lineage/extraction contexts) without a single canonical field-comparison service.

---

## 2. Weaknesses, limitations, and proposed improvements

### W1. Vacancy matching uses coarse field equality and limited contradiction logic
- **Existing implementation:** `src/evidence/collector.py::_compare()` compares only normalized employer/title/location/application URL equality, derives vacancy_match and authorization_basis, and flags contradiction mainly when employer matches but title differs.
- **Identified limitation:** No job/requisition ID exact matching, no description similarity, no posting-date consistency, no recruiter/contact comparison, no fuzzy title/location normalization beyond alnum stripping, no application-domain/ATS-employer validation beyond hostname heuristics, and limited contradiction detection (e.g. same job ID different employer/details, expired/removed status, mismatched location/date not handled).
- **Proposed improvement:** Introduce a structured attribute matcher producing per-field outcomes (exact/fuzzy/missing/conflicting/not-comparable), use exact matching for identifiers/URLs where available, fuzzy similarity for title/description/location, date consistency checks, official-domain/ATS-employer relationship validation, and transparent evidence-support scoring with explicit reasons; keep `snapshot_match_only` distinct from independent support.
- **Expected research benefit:** Higher-quality evidence alignment, fewer false supports/contradictions from superficial matches, better inputs for A/B/C comparisons and descriptive verification analysis.
- **Files that would need modification:** `src/evidence/collector.py`, `src/ingestion/content_extractor.py` (field normalization/extraction), possibly new `src/evidence/matching.py`, `app.py` (display), `tests/test_evidence_collection.py`, new matching tests.
- **Risks of data leakage or overfitting:** Low leakage risk if rules/similarity are unsupervised; overfitting risk if thresholds/weights tuned on test or on synthetic labels then generalized as real performance. Mitigation: fixed/documented heuristics or train/validation-only tuning.

### W2. Official-source/ATS authority and verification states are heuristic and partly artifact-derived
- **Existing implementation:** Source type/authorization basis inferred from hostname heuristics and employer-name tokens; automated verification states for Stage 4E generated from collected artifact fields/proxies; live verification depends on caller-supplied URLs and fetch success.
- **Identified limitation:** Cannot reliably establish employer-careers vs authorized ATS relationships, distinguish first-party publication provenance, or confirm independent authorization; `independently_supported/contradicted` remain largely unpopulated in automated runs; snapshot/retrieval evidence may be over-interpreted without stronger authority checks.
- **Proposed improvement:** Add official-domain allow/relationship resolution logic (configured/observed mappings), ATS-employer linkage checks, explicit provenance classification, and stricter criteria separating `snapshot_match_only`, `not_comparable`, and unresolved states; preserve all retrieval/provenance metadata.
- **Expected research benefit:** More defensible verification-state distributions and clearer separation between retrieval success and authorization evidence.
- **Files that would need modification:** `src/evidence/collector.py`, `src/ingestion/url_fetcher.py` (metadata), new authority/provenance module, `scripts/*verification*`, `app.py`, `tests/test_url_fetcher.py`, `tests/test_evidence_collection.py`.
- **Risks of data leakage or overfitting:** Minimal leakage; risk of encoding dataset-specific employer mappings (overfitting to known cohorts). Mitigation: keep mappings explicit, versioned, and reported.

### W3. Lineage detection is threshold-fragile and not fully multi-signal/unified
- **Existing implementation:** `src/lineage/similarity.py` uses a single 0.72 cosine threshold plus shared contact/URL/exact match and coarse bands; automated analysis scores 687 candidates post-hoc but does not integrate all signals (job ID, posting date, recruiter/contact, canonical URL, repeated phrases, source metadata) into one transparent weighted method across 687 + 2,200 expansion records.
- **Identified limitation:** Vulnerable to false merges/splits, paraphrase misses, and inconsistent categories; no unified per-pair/per-cluster explanation artifact over full relevant corpora; source-family estimation is heuristic.
- **Proposed improvement:** Build a transparent multi-signal lineage scorer (canonical URL, exact/normalized duplicates, TF-IDF/char/token/text similarities, title/employer/job ID/recruiter/date/phrase/metadata signals) with documented weights/bands, produce per-candidate scores, feature contributions, and categories (`confirmed_by_direct_machine_verifiable_provenance` only with direct provenance, else likely/possible/unknown), cluster into conservative source families, and generate validation/unknown statistics.
- **Expected research benefit:** Core novelty strengthened; better control of copied-evidence inflation and clearer B vs C comparison inputs.
- **Files that would need modification:** `src/lineage/similarity.py`, new `src/lineage/scoring.py`/`clustering.py`, `scripts/automated_mode_analysis.py` or new lineage scripts, `app.py`, lineage/evaluation tests.
- **Risks of data leakage or overfitting:** High if weights/thresholds tuned on test labels or adjusted after observing outcomes. Mitigation: unsupervised/fixed transparent weights, or tune on train/validation synthetic/held-out partitions only; document all choices.

### W4. Approach C consolidation is limited to supplied lineage groups and lacks reliability/freshness weighting
- **Existing implementation:** `lineage_aware()` deduplicates only by keys in `dependent_group_keys` (or item keys) and otherwise applies naive counting; no source reliability, evidence freshness, contradiction strength, evidence completeness, provenance quality, or unknown-lineage weighting.
- **Identified limitation:** Dependent evidence can still inflate support if groups not identified; independent but weak/stale sources treated equally to strong authoritative recent evidence; contradiction strength and completeness not represented; unknown lineage handled conservatively but not explicitly scored.
- **Proposed improvement:** Define C as consolidation within known/estimated source families plus weighted evidence assessment (authority, retrieval/provenance quality, freshness/recency, field completeness, contradiction specificity, independence confidence/unknown penalty) with documented math and conservative thresholds; keep B as appearance-based aggregation without lineage consolidation.
- **Expected research benefit:** Fairer and more defensible test of lineage-aware aggregation’s ability to reduce false assurance under dependence and uncertainty.
- **Files that would need modification:** `src/aggregation/rules.py`, `src/decision/policy.py`, possibly `src/aggregation/scoring.py`, `app.py`, evaluation scripts/tests (`tests/test_core.py`, `tests/test_automated_mode.py`, runner/metrics usage).
- **Risks of data leakage or overfitting:** Significant if weights/thresholds optimized on final test or to force C>B. Mitigation: pre-register/fix weights, or tune on train/validation only; keep B definition unchanged; report null/negative findings honestly.

### W5. Abstention, confidence, and output calibration are simplistic
- **Existing implementation:** Binary-like state transitions and abstain on unavailable/failed/insufficient evidence; text probabilities uncalibrated and not authorization confidence; no sufficiency score or calibrated uncertainty.
- **Identified limitation:** Cannot express graded evidence sufficiency, conflicting weak evidence, or calibrated confidence; may abstain or decide too coarsely in borderline cases.
- **Proposed improvement:** Add explicit sufficiency/completeness scoring, contradiction/uncertainty indicators, and (if used) calibration evaluated on validation data; present as machine-generated non-adjudicated assessments with clear confidence caveats.
- **Expected research benefit:** Better uncertainty handling and more interpretable decisions, especially for unresolved/inaccessible cases.
- **Files that would need modification:** `src/decision/policy.py`, `src/aggregation/*`, `src/ml/text_classifier.py` (optional calibration), `app.py`, `tests/*`.
- **Risks of data leakage or overfitting:** Calibration/threshold fitting on test data would leak. Mitigation: validation-only calibration, or avoid calibrated claims.

### W6. Schema and vocabulary fragmentation across app, datasets, and artifacts
- **Existing implementation:** Multiple schemas/vocabularies (SQLite, JSON schemas, annotation JSONL, DatasetCollection tables, unified package, verification-state artifacts) with overlapping but not fully aligned field names/states.
- **Identified limitation:** Hard to compare records, compute consistent descriptive metrics, trace provenance end-to-end, and integrate 687/2,200/2,980 datasets for analysis without ad-hoc mapping.
- **Proposed improvement:** Define canonical analysis schema/mapping layer and validators, normalize state vocabularies in analysis outputs, and generate dataset-quality/provenance-completeness reports without mutating originals.
- **Expected research benefit:** Reproducible audits/evaluations and reduced integration errors.
- **Files that would need modification:** new `src/datasets/schema_mapping.py` or scripts, validators, `scripts/*`, docs; originals untouched.
- **Risks of data leakage or overfitting:** None directly; risk of incorrect mappings biasing analysis. Mitigation: explicit mapping tables and checksums/row counts.

### W7. Evaluation methodology lacks challenging leakage-safe scenario coverage and calibration analysis
- **Existing implementation:** Runner enforces basic group-leakage/fingerprint checks and computes classification/selective metrics; synthetic experiments exist but scenarios are limited (original 60, extended 30) and some controlled cases yield ceiling effects for B/C.
- **Identified limitation:** Insufficient difficult scenarios (many copied sources vs one original, conflicting independent sources, expired/removed/old evidence, same employer multiple vacancies, similar descriptions different IDs/employers, incomplete/misleading info) to stress A/B/C differences; no calibration reporting where probabilities used; real-data analysis correctly descriptive but could be more comprehensive.
- **Proposed improvement:** Create a new separately versioned difficult synthetic benchmark with controlled (synthetic-only) labels, group-aware splits, fixed seeds, train/validation-only tuning, untouched test partition, and per-scenario metrics including B vs C false-assurance on dependent-evidence cases; add calibration/error analysis where applicable.
- **Expected research benefit:** Fair, discriminative test of whether C reduces false assurance without overclaiming real-world superiority.
- **Files that would need modification:** new benchmark generator/scripts, `scripts/run_*evaluation*`, `src/evaluation/*` (calibration/leakage utilities as needed), `tests/*`.
- **Risks of data leakage or overfitting:** High if scenarios designed to favor C, labels leak, duplicates cross splits, or tuning uses test. Mitigation: balanced/challenging design, group-aware partitioning, fixed seeds, documented protocol, honest reporting.

### W8. Real-data quality/provenance gaps limit automated verification strength
- **Existing implementation:** Datasets include rich collection artifacts but with missing/heterogeneous fields (URLs, job IDs, posting dates, authority/provenance indicators), source concentration (Stripe/Greenhouse/Lever heavy), and no adjudicated ground truth.
- **Identified limitation:** Automated official-source matching, ATS-employer validation, freshness checks, and lineage confirmation are constrained by available fields and public accessibility; many records remain snapshot-only/unresolved by necessity.
- **Proposed improvement:** Perform dataset quality audit (counts, IDs, missingness, duplicates, URL/ID/date/provenance completeness, overlaps) producing analysis-ready views/copies and usability-by-analysis reports; compute comprehensive descriptive metrics and abstention/independence distributions with clear caveats.
- **Expected research benefit:** Transparent evidence of what can/cannot be concluded automatically and more reliable descriptive findings.
- **Files that would need modification:** new audit scripts/reports, `final_completion_package/*` analysis outputs; no original dataset mutation.
- **Risks of data leakage or overfitting:** None if originals preserved and no labels inferred as truth.

### W9. Application explainability for lineage impact and automated status can be clearer
- **Existing implementation:** Streamlit app shows extraction, evidence ledger, naive vs lineage-aware summaries, decision states, and synthetic three-way demo; recent labels note machine-generated assessments.
- **Identified limitation:** Limited explicit comparison of how repeated dependent evidence changes B vs C counts/outcomes, limited display of relationship categories/scores/provenance/authority reasons and why decisions are unresolved, and potential confusion between synthetic demo and real verification.
- **Proposed improvement:** Add comparison/explanation panels (dependent-source consolidation, source-family/independence estimates, field-match and authority/provenance reasons, freshness/availability notes) while preserving current functionality and clearly separating synthetic demos from real inputs.
- **Expected research benefit:** Better interpretability and research demonstration value.
- **Files that would need modification:** `app.py`, `src/ui_support.py`, possibly `src/report.py`, UI tests/smoke.
- **Risks of data leakage or overfitting:** None.

### W10. Test coverage gaps for difficult and safety-critical behaviors
- **Existing implementation:** 73 tests cover many core behaviors, but gaps remain around evidence freshness/expiry, multi-vacancy same-employer disambiguation, canonical URL/duplicate-URL lineage signals at integration level, calibration/leakage-prevention utilities (if added), and full B-vs-C scenario regressions.
- **Identified limitation:** Regressions in key research claims (false-assurance reduction under dependence, conservative unknown handling, snapshot vs independent distinction) may go undetected.
- **Proposed improvement:** Add targeted tests for exact/similar/wrong-employer cases, same-employer multiple vacancies, duplicate/copied/independent/unknown/contradictory/unavailable/expired evidence, freshness, abstention, unsafe URLs, leakage prevention, and preservation of original datasets/benchmarks; maintain existing tests.
- **Expected research benefit:** Higher confidence that improvements preserve definitions and do not introduce leakage or fabricated claims.
- **Files that would need modification:** `tests/*` (new files), possibly fixtures/helpers; no production behavior changed except via verified fixes.
- **Risks of data leakage or overfitting:** Tests must not encode test-set answers into training/tuning logic.

---

## 3. Priority order for subsequent phases (recommended, not yet implemented)
1. **P1 (Phase 5, 2):** Dataset quality/provenance audit and official-source attribute-matching/authority improvements — foundation for trustworthy evidence states.
2. **P1 (Phase 3):** Unified transparent multi-signal lineage scoring over 687 (+ relevant expansion) with conservative categories and source-family estimates.
3. **P1 (Phase 4):** Improve C weighting/consolidation and abstention while preserving A/B/C definitions and conservative decisions.
4. **P2 (Phase 6, 7):** New difficult synthetic benchmark and fair leakage-safe A/B/C evaluation with B-vs-C false-assurance focus.
5. **P2 (Phase 8, 9):** Comprehensive descriptive real-data analysis and clearer app comparison/explanations.
6. **P2 (Phase 10, 11):** Expanded tests, reproducibility manifest, before/after reports and honest conclusions.

## 4. Cross-cutting guardrails
- Preserve all original datasets, historical annotations/review artifacts, and existing benchmark labels; write versioned outputs/copies only.
- No fabricated human labels, official evidence, or confirmed lineage; no manual review requirement.
- No test/train leakage, no tuning on final test partitions, no forced C>B claims.
- Keep employer identity, vacancy authorization, and fraud outcome separate; missing/inaccessible evidence ≠ fraud; snapshot match ≠ independent authorization.

**Audit status:** COMPLETE. No production datasets or original artifacts were modified during this audit. Large-scale implementation should proceed only in small, testable stages per subsequent phases with before/after validation.

## 5. Follow-up implementation update (2026-11-16)

This audit is a phase-1 baseline snapshot; its limitations and priority list predate later implementation already present in this workspace. The current engineering and dataset status is tracked in [docs/accuracy_improvement_status.md](docs/accuracy_improvement_status.md). Since that snapshot, the project added structured job-ID/date/freshness matching, official-source mapping, OCR preprocessing, conservative group-aware lineage and evaluation, and a descriptive real-world corpus union. This follow-up additionally preserves vacancy IDs in application URL canonicalization, prevents conflicting requisition IDs from becoming copy candidates, changes low-similarity lineage results to unknown, requires an extracted employer/title match before support, and adds train-fitted feature selection to E2/E3. Independent real-world adjudication remains outstanding.
