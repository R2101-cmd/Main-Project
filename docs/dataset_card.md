# Dataset card

Status: small reviewed pilot collected on 2026-10-16 from public job pages and indexed public job pages. It contains 4 non-synthetic records covering 4 vacancy groups: 2 supported observations and 2 unresolved/stale observations. The pilot is not a representative sample and is not large enough for publication claims. The records and source URLs are in `data/annotations/pilot.jsonl`.

Sampling plan: purposive feasibility sample of public Data Analyst/Data Analytics internship listings found through public search, restricted to pages that exposed a role, employer, location, and/or application context. Official Greenhouse employer recruitment pages were prioritized. Third-party indexes were retained only as provenance observations and were not treated as independent authorization. A direct page that redirected to a current board without the exact vacancy was labeled unresolved, not fraudulent.

Label quality: single-reviewer pilot annotations with written rationales; no inter-annotator agreement is claimed. Source pages may change and some indexed pages were no longer individually retrievable at observation. Licensing/access: URLs are retained as provenance; descriptions are short factual summaries, not a bulk copy of page content. Known biases include internship-heavy sampling, Greenhouse-heavy sources, English-language search, and selection toward publicly indexed pages.

## Imported public job-posting dataset

The uploaded `data/raw/fake_job_postings.csv` contains 17,880 records and 18 columns. It has 0 duplicate `job_id` values and 281 exact duplicate rows when `job_id` is excluded; those duplicates are removed from the processed output but preserved in the original CSV. In the raw input, the source `fraudulent` field contains 17,014 values of `0` and 866 values of `1`; after exact-duplicate removal, the processed output contains 16,743 values of `0` and 856 values of `1`. These are source fraud labels and are not vacancy-authorization labels. The importer reports conservative potential repost pairs. Imported records remain unreviewed and have `authorization_label: unresolved`.

The dataset contains no source URLs, requisition IDs, official evidence, or verified employer-domain relationships. It cannot by itself establish vacancy authorization. See `data/processed/fake_job_postings_import_report.json` for the generated report.
