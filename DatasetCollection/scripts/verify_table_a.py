
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

file_path = ROOT / "processed" / "table_A_advertisements.csv"

df = pd.read_csv(file_path)

print("TOTAL RECORDS:", len(df))
print("\nCOLUMNS:")
print(df.columns.tolist())

print("\nDUPLICATE CASE IDs:", df["case_id"].duplicated().sum())

print("\nMISSING VALUES:")
print(df.isnull().sum())

print("\nFIRST 3 RECORDS:")
print(df[["case_id", "job_title", "location", "employer_id"]].head(3).to_string(index=False))
