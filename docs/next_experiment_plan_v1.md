# Next experiment plan v1

The current evaluation is frozen before any new annotation or method tuning.

The operational pre-collection gate is [benchmark_collection_checklist_v1.md](benchmark_collection_checklist_v1.md). It must be completed before new records enter the benchmark.

The configuration template is `config/collection_config_v1.json`; it contains unset dates, reviewer assignments, privacy decisions, and operational authorization by design. Run `python scripts\validate_collection_readiness.py` before collection. A non-zero result means the project is not collection-ready.

## Milestone 1: frozen baseline

The frozen snapshot is `artifacts/experiments/research_v1_frozen/`. `FREEZE_MANIFEST.json` records SHA-256 hashes for the aggregate metrics, predictions, split manifest, and configuration. The frozen result remains provisional and single-reviewer.

## Milestone 2: annotation sample

Target 100–200 underlying vacancy groups, subject to collection feasibility. The proposed frame is India-focused data/analytics and closely related internships or entry-level roles collected during one fixed 30-day window from employer pages/ATS, public job portals, institutional pages, and lower-confidence public repost channels. Sample across supported, contradicted, unresolved, stale, inaccessible, third-party-only, reposted, copied/derived, and genuinely independent source situations. Do not balance classes artificially or create labels without evidence.

## Milestone 3: double annotation

Two reviewers independently label the same fixed records without model predictions. Record reviewer IDs, timestamps, rationale, evidence IDs, and disagreement reasons. Adjudicate disagreements after independent review. Report raw agreement and an agreement statistic only if class support makes it interpretable.

## Milestone 4: lineage reference standard

Review source relationships as original, independent, copied/derived, or unknown. Similarity produces candidates only; reviewers must document the observed signals and rationale. Keep all members of a reviewed vacancy family in one split.

## Milestone 5: frozen evaluation

Freeze a group-separated test set before tuning. Run E1, E4, and E5 on identical eligible records. Add E2 and E3 only when their structured features and reference labels are independently supported.

## Primary metric

False assurance is defined before collection as:

`unsupported cases predicted supported / all reference non-supported cases`

The numerator, denominator, definitive decision count, decision coverage, abstention rate, supported recall, macro F1, and uncertainty intervals must be reported together. A system that abstains on every record can have zero false assurance but zero useful decision coverage, so neither metric is sufficient alone.

## Current claim boundary

The current project can claim implementation of a provenance-aware vacancy-authorization pipeline, unresolved outcomes, group-aware splitting, and a reproducible comparison workflow. It cannot yet claim that lineage-aware aggregation improves accuracy or false assurance in real-world recruitment verification.

## Pre-collection operational details

The 100–200 vacancy-group target is a feasibility target, not a guarantee of statistical power. Use the India-focused scope and source strata in the configuration template, report the main sampling frame separately from targeted supplementary cases, and do not balance classes artificially or select records using model predictions.

Original decisions use `schemas/annotation_form_v1.schema.json`; adjudications use `schemas/adjudication_form_v1.schema.json` and reference both original annotation IDs. The originals remain immutable. Lineage reviews use `schemas/lineage_review_v1.schema.json` and record case groups, signals, relationship, reviewer, timestamp, rationale, confidence, and status.

The frozen evaluation manifest must record the random seed, vacancy-group and partition assignments, test identifiers, and configuration fingerprint. If test findings cause a method change, the old result becomes exploratory and a new confirmatory test set is required. E4 and E5 must use identical eligible groups, with paired outcomes reported as both correct, both wrong, E4 wrong/E5 correct, E4 correct/E5 wrong, and lineage-attributable decision changes.
