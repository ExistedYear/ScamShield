# =============================================================================
# ScamShield — Multilingual Smishing Detector (XLM-RoBERTa)
# Kaggle Notebook — copy each CELL block into a separate notebook cell
#
# SETUP:
#   1. Upload the KaggleTraining/ folder as a Kaggle Dataset
#      (name it e.g. "scamshield-training")
#   2. Attach it to this notebook under "Add data" → "Your datasets"
#   3. Enable GPU (T4 x2) and Internet in notebook settings
#   4. Copy each CELL below into a new cell in order and run
# =============================================================================


# ── CELL 1: Install dependencies ─────────────────────────────────────────────

import subprocess
subprocess.run([
    "pip", "install", "-q",
    "transformers>=4.35.0",
    "datasets>=2.14.0",
    "sentencepiece>=0.1.99",
    "protobuf>=3.20.0",
    "kagglehub>=0.2.0",
    "tldextract>=3.4.0",
    "scikit-learn>=1.3.0",
])
print("Dependencies installed.")


# ── CELL 2: GPU check + path setup ───────────────────────────────────────────

import sys, os, torch

print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# Point Python to the uploaded dataset files
# Change 'scamshield-training' to whatever you named the dataset
DATASET_PATH = "/kaggle/input/scamshield-training"
sys.path.insert(0, DATASET_PATH)
print(f"Dataset path added: {DATASET_PATH}")
print(f"Files found: {os.listdir(DATASET_PATH)}")


# ── CELL 3: Hyperparameters ───────────────────────────────────────────────────

EPOCHS             = 10
BATCH_SIZE         = 16       # XLM-RoBERTa is heavier than DistilBERT
LR                 = 1e-5
WEIGHT_DECAY       = 0.01
THRESHOLD          = 0.55
LABEL_SMOOTHING    = 0.05
CHECKPOINT         = "/kaggle/working/best_model.pt"
FREEZE_BERT_LAYERS = 0        # Full fine-tuning — needed for multilingual
DROPOUT            = 0.3
EARLY_STOPPING     = 4
DEVICE             = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"Device: {DEVICE}")
print(f"Batch size: {BATCH_SIZE}, LR: {LR}, Epochs: {EPOCHS}")


# ── CELL 4: Load dataset ──────────────────────────────────────────────────────

from data_loader import load_dataset, split_dataset

print("Loading all datasets (UCI + Deysi + Gaurav + Indian legit + dbarbedillo + rajnathpatel)...")
df = load_dataset()

train_df, val_df, test_df = split_dataset(df)
print(f"\nSplit → Train: {len(train_df)}  Val: {len(val_df)}  Test: {len(test_df)}")
print(f"Train spam: {int(train_df['label'].sum())}  ham: {len(train_df) - int(train_df['label'].sum())}")


# ── CELL 5: Build model ───────────────────────────────────────────────────────

from model import SmishingDetector, get_tokenizer

print("Loading XLM-RoBERTa tokenizer (downloads ~1.1 GB on first run)...")
tokenizer = get_tokenizer()

print("Initializing SmishingDetector...")
model = SmishingDetector(
    num_handcrafted=17,
    dropout=DROPOUT,
    freeze_bert_layers=FREEZE_BERT_LAYERS,
).to(DEVICE)

total_params = sum(p.numel() for p in model.parameters())
trainable    = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"Total params:     {total_params:,}")
print(f"Trainable params: {trainable:,}")


# ── CELL 6: Build dataloaders ─────────────────────────────────────────────────

from dataset import build_dataloaders

train_loader, val_loader, test_loader, norm_stats = build_dataloaders(
    train_df, val_df, test_df, tokenizer, BATCH_SIZE
)
print(f"Train batches: {len(train_loader)}")
print(f"Val   batches: {len(val_loader)}")
print(f"Test  batches: {len(test_loader)}")


# ── CELL 7: Loss + training functions ────────────────────────────────────────

import torch.nn as nn
from torch.optim import AdamW
from transformers import get_linear_schedule_with_warmup
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


class LabelSmoothingBCELoss(nn.Module):
    def __init__(self, pos_weight, smoothing=0.05):
        super().__init__()
        self.smoothing = smoothing
        self.pos_weight = pos_weight

    def forward(self, logits, targets):
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
    return (total_loss/n,
            accuracy_score(all_labels, all_preds),
            precision_score(all_labels, all_preds, zero_division=0),
            recall_score(all_labels, all_preds, zero_division=0),
            f1_score(all_labels, all_preds, zero_division=0))


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
    return (total_loss/n,
            accuracy_score(all_labels, all_preds),
            precision_score(all_labels, all_preds, zero_division=0),
            recall_score(all_labels, all_preds, zero_division=0),
            f1_score(all_labels, all_preds, zero_division=0),
            all_preds, all_labels)

print("Loss and training functions defined.")


# ── CELL 8: Optimizer + scheduler setup ──────────────────────────────────────

spam_count = int(train_df['label'].sum())
ham_count  = len(train_df) - spam_count
pos_weight = torch.tensor([ham_count / spam_count], dtype=torch.float32).to(DEVICE)
print(f"pos_weight: {pos_weight.item():.3f}  (spam: {spam_count}, ham: {ham_count})")

criterion = LabelSmoothingBCELoss(pos_weight, smoothing=LABEL_SMOOTHING)

trainable_params = [p for p in model.parameters() if p.requires_grad]
optimizer = AdamW(trainable_params, lr=LR, weight_decay=WEIGHT_DECAY)

total_steps  = len(train_loader) * EPOCHS
warmup_steps = total_steps // 10
scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

print(f"Total training steps: {total_steps}  Warmup steps: {warmup_steps}")


# ── CELL 9: Training loop ─────────────────────────────────────────────────────

best_val_f1 = 0.0
patience    = 0

print(f"Training for up to {EPOCHS} epochs (early stopping patience={EARLY_STOPPING})...\n")

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
        print(f"  ✓ Best model saved  (Val F1={best_val_f1:.4f})\n")
    else:
        patience += 1
        print(f"  No improvement ({patience}/{EARLY_STOPPING})\n")
        if patience >= EARLY_STOPPING:
            print(f"Early stopping at epoch {epoch+1}.")
            break

print(f"\nTraining complete. Best Val F1: {best_val_f1:.4f}")


# ── CELL 10: Final evaluation on test set ─────────────────────────────────────

from sklearn.metrics import classification_report, confusion_matrix

print("Loading best checkpoint...")
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


# ── CELL 11: Download checkpoint ─────────────────────────────────────────────

# best_model.pt is saved to /kaggle/working/ — download it from
# the Kaggle notebook output panel (right side → Output → best_model.pt)
# Then drop it into:  smishing_detector/best_model.pt

import os
size_mb = os.path.getsize(CHECKPOINT) / 1e6
print(f"Checkpoint saved: {CHECKPOINT}  ({size_mb:.1f} MB)")
print("Download it from the Kaggle Output panel on the right.")
print("Then replace smishing_detector/best_model.pt with the downloaded file.")
