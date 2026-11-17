# Isolated schema compatibility test

Run the standalone generator from the research workspace. It reads only the 780-row reconciliation CSV and the existing candidate worksheet, creates disposable_staging.sqlite3 in this folder, and never opens the production database, scrapes, imports other cohorts, generates labels, or modifies source files.
