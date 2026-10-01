"""
Evaluate ScamShield on your own messages.

Examples:
    python evaluate_custom.py --input my_sms.csv
    python evaluate_custom.py --input my_sms.csv --output predictions.csv

Input can be:
    - CSV/TSV with a "message" column and optional "label" column
    - TXT with one SMS per line

Labels, when present, may be: spam/ham, 1/0, scam/safe.
"""

import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


LABEL_MAP = {
    "spam": "spam",
    "scam": "spam",
    "phishing": "spam",
    "smishing": "spam",
    "1": "spam",
    "true": "spam",
    "ham": "ham",
    "safe": "ham",
    "legit": "ham",
    "legitimate": "ham",
    "0": "ham",
    "false": "ham",
}


def normalize_label(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    return LABEL_MAP.get(text)


def sniff_delimiter(path):
    suffix = path.suffix.lower()
    if suffix == ".tsv":
        return "\t"
    return ","


def load_rows(input_path):
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if path.suffix.lower() == ".txt":
        rows = []
        with path.open("r", encoding="utf-8-sig") as f:
            for line in f:
                message = line.strip()
                if message:
                    rows.append({"message": message, "label": None})
        return rows

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=sniff_delimiter(path))
        if not reader.fieldnames or "message" not in reader.fieldnames:
            raise ValueError('CSV/TSV input must contain a "message" column.')

        rows = []
        for row in reader:
            message = (row.get("message") or "").strip()
            if not message:
                continue
            rows.append({
                "message": message,
                "label": normalize_label(row.get("label")),
            })
        return rows


def evaluate(rows, checkpoint):
    from predictor import SmishingPredictor

    predictor = SmishingPredictor(checkpoint)
    results = []

    for row in rows:
        pred = predictor.predict(row["message"])
        expected = row.get("label")
        got = pred["label"]
        correct = None if expected is None else expected == got
        results.append({
            "expected": expected or "",
            "predicted": got,
            "correct": "" if correct is None else str(correct).lower(),
            "confidence": pred["confidence"],
            "risk_level": pred["risk_level"],
            "language": pred.get("language", ""),
            "neural_score": pred.get("_neural_score", ""),
            "rule_score": pred.get("_rule_score", ""),
            "ham_rule_score": pred.get("_ham_rule_score", ""),
            "rule_weight": pred.get("_rule_weight", ""),
            "message": row["message"],
        })

    return results


def print_summary(results):
    labelled = [r for r in results if r["expected"]]
    print(f"\nEvaluated {len(results)} messages")

    if labelled:
        correct = sum(1 for r in labelled if r["correct"] == "true")
        spam_total = sum(1 for r in labelled if r["expected"] == "spam")
        ham_total = sum(1 for r in labelled if r["expected"] == "ham")
        false_pos = sum(1 for r in labelled if r["expected"] == "ham" and r["predicted"] == "spam")
        false_neg = sum(1 for r in labelled if r["expected"] == "spam" and r["predicted"] == "ham")

        print(f"Labelled accuracy: {correct}/{len(labelled)} ({correct / len(labelled):.1%})")
        print(f"Ham labelled: {ham_total}, spam labelled: {spam_total}")
        print(f"False positives: {false_pos}, false negatives: {false_neg}")

    print("\nTop misses / borderline cases:")
    misses = [r for r in results if r["correct"] == "false"]
    borderline = sorted(
        results,
        key=lambda r: abs(float(r["confidence"]) - 0.55),
    )[:10]
    for r in (misses[:10] or borderline[:10]):
        expected = r["expected"] or "?"
        print(
            f"- exp={expected:<4} got={r['predicted']:<4} "
            f"conf={float(r['confidence']):.2f} "
            f"neural={r['neural_score']} rule={r['rule_score']} ham_rule={r['ham_rule_score']} "
            f"lang={r['language']} :: {r['message'][:120]}"
        )


def write_results(results, output_path):
    fields = [
        "expected", "predicted", "correct", "confidence", "risk_level",
        "language", "neural_score", "rule_score", "ham_rule_score", "rule_weight", "message",
    ]
    with Path(output_path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV/TSV/TXT file of messages")
    parser.add_argument("--output", help="Optional CSV path for detailed predictions")
    parser.add_argument(
        "--checkpoint",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "best_model.pt"),
        help="Path to best_model.pt",
    )
    args = parser.parse_args()

    rows = load_rows(args.input)
    results = evaluate(rows, args.checkpoint)
    print_summary(results)

    if args.output:
        write_results(results, args.output)
        print(f"\nSaved detailed predictions to {args.output}")


if __name__ == "__main__":
    main()
