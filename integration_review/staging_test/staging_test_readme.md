# Stripe staging validation

Run from any Python environment:

```powershell
python validate_stripe_staging.py
```

The validator is at `C:\Users\Admin\Desktop\Cleaned data\scripts\validate_stripe_staging.py` and writes only to this folder. It reads the final package manifest, dictionary, validation report, and package CSVs; it selects the unique 780-row Stripe-only file by actual case IDs. It does not import Streamlit modules, open SQLite, scrape URLs, assign labels, delete duplicates, or modify source data.

Outputs:
- `stripe_staging_preview.csv` — semantic copy of the selected 780 source rows.
- `staging_validation_report.md` — human-readable checks and warnings.
- `staging_validation_summary.json` — machine-readable results.

Existing application regression tests were inspected separately and run with bytecode/cache disabled in an isolated test mode; results are recorded in the final assistant handoff and were not required by this standalone validator.
