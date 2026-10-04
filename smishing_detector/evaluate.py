import torch
import os
import sys
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.data_loader import load_dataset, split_dataset
from predictor import SmishingPredictor
from adversarial.evasion import run_adversarial_evaluation


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CHECKPOINT = "best_model.pt"


def main():
    if not os.path.exists(CHECKPOINT):
        print(f"Error: Model checkpoint '{CHECKPOINT}' not found. Run train.py first.")
        return

    print("Loading dataset...")
    df = load_dataset()

    train_df, val_df, test_df = split_dataset(df)

    print("Loading model...")
    predictor = SmishingPredictor(CHECKPOINT)

    print("Evaluating on test set...")
    test_messages = test_df['message'].tolist()
    test_labels = test_df['label'].tolist()

    predictions = []
    for msg in test_messages:
        result = predictor.predict(msg)
        predictions.append(1 if result['label'] == 'spam' else 0)

    print("\n" + "="*60)
    print("TEST SET RESULTS — SmishingDetector (XLM-RoBERTa + URL Fusion)")
    print("="*60)

    print("\nClassification Report:")
    print(classification_report(test_labels, predictions, target_names=['ham', 'spam']))

    cm = confusion_matrix(test_labels, predictions)
    print("Confusion Matrix:")
    print(cm)

    fpr = cm[0][1] / (cm[0][0] + cm[0][1]) if (cm[0][0] + cm[0][1]) > 0 else 0
    fnr = cm[1][0] / (cm[1][0] + cm[1][1]) if (cm[1][0] + cm[1][1]) > 0 else 0

    print(f"False Positive Rate: {fpr:.4f}  (ham flagged as spam)")
    print(f"False Negative Rate: {fnr:.4f}  (spam missed)")

    test_acc = (sum(1 for p, t in zip(predictions, test_labels) if p == t) / len(test_labels))
    test_f1 = f1_score(test_labels, predictions, zero_division=0)

    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    print(f"{'Metric':<25} {'Value':<20}")
    print("-"*45)
    print(f"{'Accuracy':<25} {f'{test_acc*100:.2f}%':<20}")
    print(f"{'F1 (spam)':<25} {f'{test_f1:.4f}':<20}")
    print(f"{'False Positive Rate':<25} {f'{fpr*100:.2f}%':<20}")

    print("\n" + "="*60)
    print("ADVERSARIAL ROBUSTNESS")
    print("="*60)

    adversarial_results = run_adversarial_evaluation(predictor, test_df, spam_only=True)

    print(f"{'Attack':<15} {'Original F1':<15} {'Attacked F1':<15} {'Drop':<10}")
    print("-"*55)
    for _, row in adversarial_results.iterrows():
        print(f"{row['attack_type']:<15} {row['original_f1']:<15.2f} {row['attacked_f1']:<15.2f} {row['accuracy_drop']:<10.2f}")

    # ── Multilingual evaluation ───────────────────────────────────────────────
    print("\n" + "="*60)
    print("MULTILINGUAL EVALUATION")
    print("="*60)
    print("Evaluating model on Hindi/Hinglish held-out test data...")

    try:
        from utils.multilingual_loader import load_all_multilingual_test_data

        lang_data = load_all_multilingual_test_data()

        print(f"\n{'Language':<12} {'Accuracy':<12} {'F1':<10} {'FPR':<10}")
        print("-"*45)

        for lang_name, lang_df in lang_data.items():
            if len(lang_df) == 0:
                continue
            lang_messages = lang_df['message'].tolist()
            lang_labels   = lang_df['label'].tolist()
            lang_preds    = [1 if predictor.predict(m)['label'] == 'spam' else 0
                             for m in lang_messages]

            lang_acc = accuracy_score(lang_labels, lang_preds)
            lang_f1  = f1_score(lang_labels, lang_preds, zero_division=0)
            lang_cm  = confusion_matrix(lang_labels, lang_preds)
            lang_fpr = lang_cm[0][1] / (lang_cm[0][0] + lang_cm[0][1]) \
                       if (lang_cm[0][0] + lang_cm[0][1]) > 0 else 0

            print(f"{lang_name:<12} {lang_acc*100:<12.2f} {lang_f1:<10.4f} {lang_fpr*100:<10.2f}")

    except Exception as e:
        print(f"Multilingual evaluation failed: {e}")

    print("\nEvaluation complete!")


if __name__ == "__main__":
    main()