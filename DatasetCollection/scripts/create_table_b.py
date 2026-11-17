
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = ROOT / "processed" / "table_A_advertisements.csv"
OUTPUT_FILE = ROOT / "processed" / "table_B_ground_truth.csv"

advertisements = pd.read_csv(INPUT_FILE)

columns = [
    "case_id",
    "employer_identity_label",
    "vacancy_authorization_label",
    "fraud_outcome_label",
    "label_rationale",
    "label_evidence_refs",
    "annotator_id",
    "adjudication_status",
]

ground_truth = pd.DataFrame({
    "case_id": advertisements["case_id"],
    "employer_identity_label": "unresolved",
    "vacancy_authorization_label": "unresolved",
    "fraud_outcome_label": "unresolved",
    "label_rationale": "Not yet independently reviewed.",
    "label_evidence_refs": "",
    "annotator_id": "",
    "adjudication_status": "pending",
})

ground_truth = ground_truth[columns]

ground_truth.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print("Table B created successfully!")
print("Total records:", len(ground_truth))
print("\nInitial label distribution:")
print(ground_truth["fraud_outcome_label"].value_counts())
print("Output:", OUTPUT_FILE)