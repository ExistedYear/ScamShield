"""
evaluate_multilingual.py
------------------------
Multilingual evaluation script.
Tests the smishing detector on Hindi and Hinglish messages.

Run:
    python evaluate_multilingual.py
"""

import torch
import numpy as np
from sklearn.metrics import (
    classification_report, confusion_matrix,
    f1_score, accuracy_score
)
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from predictor import SmishingPredictor
from utils.multilingual_loader import load_all_multilingual_test_data

CHECKPOINT = "best_model.pt"
THRESHOLD  = 0.5


def evaluate_language_subset(predictor, df, language_name: str):
    """Run evaluation on a single language subset."""
    if len(df) == 0:
        print(f"  No {language_name} data available")
        return None

    messages = df['message'].tolist()
    true_labels = df['label'].tolist()

    predictions = []
    confidences = []

    for msg in messages:
        result = predictor.predict(msg)
        predictions.append(1 if result['label'] == 'spam' else 0)
        confidences.append(result['confidence'])

    acc = accuracy_score(true_labels, predictions)
    f1  = f1_score(true_labels, predictions, zero_division=0)
    cm  = confusion_matrix(true_labels, predictions)

    fpr = 0.0
    fnr = 0.0
    if cm.shape == (2, 2):
        fpr = cm[0][1] / (cm[0][0] + cm[0][1]) if (cm[0][0] + cm[0][1]) > 0 else 0
        fnr = cm[1][0] / (cm[1][0] + cm[1][1]) if (cm[1][0] + cm[1][1]) > 0 else 0

    return {
        'language': language_name,
        'total': len(df),
        'spam': int(df['label'].sum()),
        'ham': len(df) - int(df['label'].sum()),
        'accuracy': acc,
        'f1': f1,
        'fpr': fpr,
        'fnr': fnr,
        'confusion_matrix': cm,
        'predictions': predictions,
        'true_labels': true_labels
    }


def main():
    if not os.path.exists(CHECKPOINT):
        print(f"Error: '{CHECKPOINT}' not found. Run train.py first.")
        return

    print("Loading model...")
    predictor = SmishingPredictor(CHECKPOINT)

    print("\nLoading multilingual test data...")
    lang_data = load_all_multilingual_test_data()

    results = {}
    for lang_name, df in lang_data.items():
        results[lang_name] = evaluate_language_subset(predictor, df, lang_name)

    # ── Print results ──────────────────────────────────────────────────────
    print("\n" + "="*65)
    print(" MULTILINGUAL EVALUATION RESULTS")
    print(" Model tested on:  Hindi + Hinglish messages")
    print("="*65)

    print(f"\n{'Language':<15} {'Messages':<10} {'Accuracy':<12} {'F1':<10} {'FPR':<10} {'FNR':<10}")
    print("-"*65)

    for lang, result in results.items():
        if result:
            print(f"{result['language']:<15} "
                  f"{result['total']:<10} "
                  f"{result['accuracy']*100:<12.2f} "
                  f"{result['f1']:<10.4f} "
                  f"{result['fpr']*100:<10.2f} "
                  f"{result['fnr']*100:<10.2f}")

    print("\n" + "="*65)
    print(" TARGET F1 CHECK")
    print("="*65)
    print(f"{'Language':<15} {'F1 Score':<12} {'Beats 0.85 target?':<20}")
    print("-"*45)
    for lang, result in results.items():
        if result:
            beats = "✓ YES" if result['f1'] >= 0.85 else "✗ NO"
            print(f"{result['language']:<15} {result['f1']:<12.4f} {beats:<20}")

    print("\n" + "="*65)
    print(" DETAILED CLASSIFICATION REPORTS")
    print("="*65)

    for lang, result in results.items():
        if result:
            print(f"\n--- {result['language'].upper()} ---")
            print(classification_report(
                result['true_labels'],
                result['predictions'],
                target_names=['ham', 'spam']
            ))
            print(f"Confusion Matrix:\n{result['confusion_matrix']}")

    print("\n" + "="*65)
    print(" F1 VERIFICATION")
    print("="*65)
    combined = results.get('combined')
    if combined:
        print(f"\nCombined Hindi+Hinglish F1 = {combined['f1']:.4f}")
        print(f"Target (>0.85): {'MET ✓' if combined['f1'] >= 0.85 else 'NOT MET ✗'}")

    print("\nZero-shot evaluation complete!")


if __name__ == "__main__":
    main()
