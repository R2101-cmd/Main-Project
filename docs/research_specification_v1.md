# Research specification v1

## Research question

Does lineage-aware aggregation of external evidence improve vacancy authorization verification compared with text-only and ordinary evidence aggregation methods, particularly when job advertisements are reposted and evidence is incomplete?

## Scope and targets

The unit of analysis is one advertised vacancy. Employer identity, vacancy authorization, and text-based fraud risk are separate targets. This project evaluates vacancy authorization only; the available source fraud labels are not authorization labels.

## Authorization labels

- `supported`: admissible evidence supports authorization of the specific vacancy.
- `contradicted`: admissible evidence directly contradicts a material authorization claim.
- `unresolved`: evidence is insufficient to establish either state.

Evidence state is separate: `supported`, `contradicted`, `unverified`, or `unavailable`. A missing careers listing or inaccessible page is not contradiction. A third-party posting establishes neither employer authorization nor fraud by itself.

## Hypotheses

H1: lineage-aware aggregation reduces false assurance relative to counting dependent source appearances independently.

H2: lineage-aware aggregation preserves or improves decision quality while exposing more unresolved cases when evidence is dependent or incomplete.

H3: a text-only baseline is weaker for vacancy authorization when authorization depends on source provenance rather than wording alone.

## Evaluation plan

Use independently reviewed labels where available, split by underlying vacancy/lineage group, fit supervised preprocessing on training data only, and evaluate E1 text-only, E2 text plus metadata, E3 employer context, E4 naive evidence, and E5 lineage-aware evidence on identical eligible test cases. Report accuracy, per-class precision/recall/F1, macro and weighted F1, balanced accuracy, confusion matrices, evidence coverage, decision coverage, abstention, false assurance, and case-level E4/E5 changes.

## Limitations

The current repository has a provisional single-reviewer subset, no adjudicated multi-reviewer labels, no confirmed fraud outcomes, no reliable contradiction class, and limited reviewed lineage references. Results are exploratory until these gaps are repaired.
