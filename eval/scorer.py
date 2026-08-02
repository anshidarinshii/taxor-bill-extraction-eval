import json, csv
from pathlib import Path
from rapidfuzz import fuzz
import pandas as pd

with open("../results/raw_extractions.json") as f:
    results = json.load(f)

ground_truth = {}
with open("../dataset/ground_truth.csv") as f:
    for row in csv.DictReader(f):
        ground_truth[row["bill_id"]] = row

FIELDS = ["vendor", "invoice_number", "date", "amount", "currency", "gst_details"]

def normalize(val):
    if val is None:
        return ""
    return str(val).strip().lower().replace(",", "")

def score_field(field, predicted, truth):
    p, t = normalize(predicted), normalize(truth)
    if t == "" and p == "":
        return 1.0
    if t == "" or p == "":
        return 0.0
    if field == "amount":
        try:
            return 1.0 if abs(float(p) - float(t)) < 0.01 else 0.0
        except ValueError:
            return 0.0
    if field in ("currency", "date"):
        return 1.0 if p == t else 0.0
    similarity = fuzz.ratio(p, t) / 100
    return 1.0 if similarity >= 0.85 else similarity

rows = []
for bill_id, model_outputs in results.items():
    truth = ground_truth.get(bill_id, {})
    for model_name, output in model_outputs.items():
        parsed = output.get("parsed", {})
        for field in FIELDS:
            s = score_field(field, parsed.get(field), truth.get(field))
            rows.append({"bill_id": bill_id, "model": model_name, "field": field, "score": s})

df = pd.DataFrame(rows)
df.to_csv("../results/scored_long.csv", index=False)

pivot = df.groupby(["model", "field"])["score"].mean().unstack().round(2)
pivot.to_csv("../results/accuracy_by_model_field.csv")
print("Accuracy by model and field:\n", pivot)

overall = df.groupby("model")["score"].mean().round(3)
print("\nOverall accuracy per model:\n", overall)