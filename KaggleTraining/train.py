"""
train.py — ScamShield multilingual smishing detector training script
Designed to run on Kaggle (GPU P100/T4).

Phase 3 changes vs Phase 2:
  • Model: XLM-RoBERTa (was DistilBERT) — multilingual, 100 languages
  • Data: +dbarbedillo (English+Hindi) +rajnathpatel (Hindi/Hinglish)
  • freeze_bert_layers: 0 (XLM-RoBERTa needs full fine-tuning for multilingual)
  • Dropout: 0.3 (was 0.4 — larger model, less aggressive dropout needed)
  • LR: 1e-5 (unchanged)
  • Threshold: 0.55 (unchanged)
  • Label smoothing: 0.05 (unchanged)
  • Early stopping patience: 4 (unchanged)
"""

import os
import torch
import torch.nn as nn
from torch.optim import AdamW
from transformers import get_linear_schedule_with_warmup
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, classification_report, confusion_matrix,
)

from data_loader import load_dataset, split_dataset
from model import SmishingDetector, get_tokenizer
from dataset import build_dataloaders

# ── Hyperparameters ───────────────────────────────────────────────────────────
EPOCHS               = 10
BATCH_SIZE           = 16          # smaller batch — XLM-RoBERTa is heavier than DistilBERT
LR                   = 1e-5
WEIGHT_DECAY         = 0.01
THRESHOLD            = 0.55
LABEL_SMOOTHING      = 0.05
CHECKPOINT           = "best_model.pt"
FREEZE_BERT_LAYERS   = 0           # XLM-RoBERTa: unfreeze all for multilingual fine-tuning
DROPOUT              = 0.3
EARLY_STOPPING       = 4
DEVICE               = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class LabelSmoothingBCELoss(nn.Module):
    """BCE with logits + label smoothing + class weighting."""
    def __init__(self, pos_weight: torch.Tensor, smoothing: float = 0.05):
        super().__init__()
        self.smoothing = smoothing
        self.pos_weight = pos_weight

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # Smooth: 1 → 1-ε, 0 → ε
        targets_smooth = targets * (1 - self.smoothing) + self.smoothing * 0.5
        return nn.functional.binary_cross_entropy_with_logits(
            logits, targets_smooth, pos_weight=self.pos_weight
        )


def train_epoch(model, loader, criterion, optimizer, scheduler):
    model.train()
    total_loss, all_preds, all_labels = 0.0, [], []

    for batch in loader:
        ids   = batch['input_ids'].to(DEVICE)
        mask  = batch['attention_mask'].to(DEVICE)
        feats = batch['hand_features'].to(DEVICE)
        lbls  = batch['label'].to(DEVICE)

        optimizer.zero_grad()
        logits = model(ids, mask, feats)
        loss   = criterion(logits, lbls)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()
        preds = (torch.sigmoid(logits) >= THRESHOLD).long().cpu().tolist()
        all_preds.extend(preds)
        all_labels.extend(lbls.long().cpu().tolist())

    n = len(loader)
    return (
        total_loss / n,
        accuracy_score(all_labels, all_preds),
        precision_score(all_labels, all_preds, zero_division=0),
        recall_score(all_labels, all_preds, zero_division=0),
        f1_score(all_labels, all_preds, zero_division=0),
    )


def evaluate(model, loader, criterion):
    model.eval()
    total_loss, all_preds, all_labels = 0.0, [], []

    with torch.no_grad():
        for batch in loader:
            ids   = batch['input_ids'].to(DEVICE)
            mask  = batch['attention_mask'].to(DEVICE)
            feats = batch['hand_features'].to(DEVICE)
            lbls  = batch['label'].to(DEVICE)

            logits = model(ids, mask, feats)
            total_loss += criterion(logits, lbls).item()

            preds = (torch.sigmoid(logits) >= THRESHOLD).long().cpu().tolist()
            all_preds.extend(preds)
            all_labels.extend(lbls.long().cpu().tolist())

    n = len(loader)
    return (
        total_loss / n,
        accuracy_score(all_labels, all_preds),
        precision_score(all_labels, all_preds, zero_division=0),
        recall_score(all_labels, all_preds, zero_division=0),
        f1_score(all_labels, all_preds, zero_division=0),
        all_preds,
        all_labels,
    )


def main():
    print(f"Device: {DEVICE}\n")

    # ── Data ────────────────────────────────────────────────────────────────
    df = load_dataset()
    train_df, val_df, test_df = split_dataset(df)
    print(f"Split → Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")

    tokenizer = get_tokenizer()
    train_loader, val_loader, test_loader, norm_stats = build_dataloaders(
        train_df, val_df, test_df, tokenizer, BATCH_SIZE
    )

    # ── Model ────────────────────────────────────────────────────────────────
    model = SmishingDetector(
        num_handcrafted=17,
        dropout=DROPOUT,
        freeze_bert_layers=FREEZE_BERT_LAYERS,
    ).to(DEVICE)

    spam_count = int(train_df['label'].sum())
    ham_count  = len(train_df) - spam_count
    # pos_weight = 1.0x ratio — no artificial boosting
    pos_weight = torch.tensor([ham_count / spam_count], dtype=torch.float32).to(DEVICE)
    print(f"pos_weight: {pos_weight.item():.3f}  (spam: {spam_count}, ham: {ham_count})")

    criterion = LabelSmoothingBCELoss(pos_weight, smoothing=LABEL_SMOOTHING)

    trainable = [p for p in model.parameters() if p.requires_grad]
    optimizer = AdamW(trainable, lr=LR, weight_decay=WEIGHT_DECAY)

    total_steps  = len(train_loader) * EPOCHS
    warmup_steps = total_steps // 10
    scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    # ── Training loop ────────────────────────────────────────────────────────
    best_val_f1 = 0.0
    patience    = 0

    print(f"\nTraining for up to {EPOCHS} epochs (patience={EARLY_STOPPING})...\n")
    for epoch in range(EPOCHS):
        tr = train_epoch(model, train_loader, criterion, optimizer, scheduler)
        vl = evaluate(model, val_loader, criterion)

        print(f"Epoch {epoch+1}/{EPOCHS}")
        print(f"  Train  loss={tr[0]:.4f}  acc={tr[1]:.4f}  prec={tr[2]:.4f}  rec={tr[3]:.4f}  F1={tr[4]:.4f}")
        print(f"  Val    loss={vl[0]:.4f}  acc={vl[1]:.4f}  prec={vl[2]:.4f}  rec={vl[3]:.4f}  F1={vl[4]:.4f}")

        if vl[4] > best_val_f1:
            best_val_f1 = vl[4]
            patience = 0
            torch.save({
                'epoch':          epoch,
                'model_state':    model.state_dict(),
                'val_f1':         best_val_f1,
                'threshold':      THRESHOLD,
                'feature_mins':   norm_stats['feature_mins'].tolist(),
                'feature_ranges': norm_stats['feature_ranges'].tolist(),
            }, CHECKPOINT)
            print(f"  ✓ Best model saved (Val F1={best_val_f1:.4f})\n")
        else:
            patience += 1
            print(f"  No improvement ({patience}/{EARLY_STOPPING})\n")
            if patience >= EARLY_STOPPING:
                print(f"Early stopping at epoch {epoch+1}.")
                break

    # ── Final evaluation ─────────────────────────────────────────────────────
    print("\nLoading best checkpoint for test evaluation...")
    ckpt = torch.load(CHECKPOINT, map_location=DEVICE, weights_only=False)
    model.load_state_dict(ckpt['model_state'])

    _, test_acc, test_prec, test_rec, test_f1, preds, labels = evaluate(
        model, test_loader, criterion
    )

    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    print(f"Accuracy : {test_acc:.4f}")
    print(f"Precision: {test_prec:.4f}   Recall: {test_rec:.4f}   F1: {test_f1:.4f}")
    print("\nClassification Report:")
    print(classification_report(labels, preds, target_names=['ham', 'spam']))

    cm = confusion_matrix(labels, preds)
    print("Confusion Matrix:")
    print(cm)

    fpr = cm[0][1] / cm[0].sum() if cm[0].sum() else 0
    fnr = cm[1][0] / cm[1].sum() if cm[1].sum() else 0
    print(f"\nFalse Positive Rate (ham → spam): {fpr*100:.2f}%")
    print(f"False Negative Rate (spam missed): {fnr*100:.2f}%")
    print("\nDone! Download best_model.pt from Kaggle output.")


if __name__ == "__main__":
    main()
