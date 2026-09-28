import os
import torch
import torch.nn as nn
from torch.optim import AdamW
from transformers import get_linear_schedule_with_warmup
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.data_loader import load_dataset, split_dataset, get_feature_columns
from models.model import SmishingDetector, get_tokenizer
from models.dataset import build_dataloaders


EPOCHS = 10
BATCH_SIZE = 16
LR = 1e-5
WEIGHT_DECAY = 0.01
THRESHOLD = 0.55
CHECKPOINT = "best_model.pt"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
EARLY_STOPPING_PATIENCE = 4
FREEZE_BERT_LAYERS = 0  # Unfrozen all layers for deep fine-tuning on diverse data
LABEL_SMOOTHING = 0.05


class LabelSmoothingBCELoss(nn.Module):
    """BCE with logits, class weighting, and mild label smoothing."""
    def __init__(self, pos_weight: torch.Tensor, smoothing: float = 0.05):
        super().__init__()
        self.pos_weight = pos_weight
        self.smoothing = smoothing

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        targets_smooth = targets * (1 - self.smoothing) + self.smoothing * 0.5
        return nn.functional.binary_cross_entropy_with_logits(
            logits, targets_smooth, pos_weight=self.pos_weight
        )


def train_epoch(model, loader, criterion, optimizer, scheduler):
    model.train()
    total_loss = 0
    all_preds = []
    all_labels = []

    for batch in loader:
        input_ids = batch['input_ids'].to(DEVICE)
        attention_mask = batch['attention_mask'].to(DEVICE)
        hand_features = batch['hand_features'].to(DEVICE)
        labels = batch['label'].to(DEVICE)

        optimizer.zero_grad()
        logits = model(input_ids, attention_mask, hand_features)
        loss = criterion(logits, labels)
        loss.backward()

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()
        preds = (torch.sigmoid(logits) > THRESHOLD).long().cpu().tolist()
        all_preds.extend(preds)
        all_labels.extend(labels.long().cpu().tolist())

    avg_loss = total_loss / len(loader)
    acc = accuracy_score(all_labels, all_preds)
    prec = precision_score(all_labels, all_preds, zero_division=0)
    rec = recall_score(all_labels, all_preds, zero_division=0)
    f1 = f1_score(all_labels, all_preds, zero_division=0)

    return avg_loss, acc, prec, rec, f1


def evaluate(model, loader, criterion):
    model.eval()
    total_loss = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in loader:
            input_ids = batch['input_ids'].to(DEVICE)
            attention_mask = batch['attention_mask'].to(DEVICE)
            hand_features = batch['hand_features'].to(DEVICE)
            labels = batch['label'].to(DEVICE)

            logits = model(input_ids, attention_mask, hand_features)
            loss = criterion(logits, labels)

            total_loss += loss.item()
            preds = (torch.sigmoid(logits) > THRESHOLD).long().cpu().tolist()
            all_preds.extend(preds)
            all_labels.extend(labels.long().cpu().tolist())

    avg_loss = total_loss / len(loader)
    acc = accuracy_score(all_labels, all_preds)
    prec = precision_score(all_labels, all_preds, zero_division=0)
    rec = recall_score(all_labels, all_preds, zero_division=0)
    f1 = f1_score(all_labels, all_preds, zero_division=0)

    return avg_loss, acc, prec, rec, f1, all_preds, all_labels


def main():
    print(f"Using device: {DEVICE}")

    print("Loading dataset...")
    df = load_dataset()

    train_df, val_df, test_df = split_dataset(df)
    print(f"Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")

    print("Loading tokenizer and building dataloaders...")
    tokenizer = get_tokenizer()
    train_loader, val_loader, test_loader, norm_stats = build_dataloaders(train_df, val_df, test_df, tokenizer, BATCH_SIZE)

    print("Initializing model...")
    model = SmishingDetector(num_handcrafted=17, dropout=0.3, freeze_bert_layers=FREEZE_BERT_LAYERS).to(DEVICE)

    spam_count = train_df['label'].sum()
    ham_count = len(train_df) - spam_count
    pos_weight = torch.tensor([ham_count / spam_count]).to(DEVICE)
    print(f"Class imbalance - pos_weight: {pos_weight.item():.2f}")

    criterion = LabelSmoothingBCELoss(pos_weight=pos_weight, smoothing=LABEL_SMOOTHING)

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = AdamW(trainable_params, lr=LR, weight_decay=WEIGHT_DECAY)

    total_steps = len(train_loader) * EPOCHS
    warmup_steps = total_steps // 10
    scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    best_val_f1 = 0.0
    patience_counter = 0

    print(f"\nStarting training ({EPOCHS} epochs, early stopping patience={EARLY_STOPPING_PATIENCE})...")
    for epoch in range(EPOCHS):
        train_loss, train_acc, train_prec, train_rec, train_f1 = train_epoch(
            model, train_loader, criterion, optimizer, scheduler
        )

        val_loss, val_acc, val_prec, val_rec, val_f1, _, _ = evaluate(model, val_loader, criterion)

        print(f"Epoch {epoch+1}/{EPOCHS}")
        print(f"  Train - Loss: {train_loss:.4f}, Acc: {train_acc:.4f}, Prec: {train_prec:.4f}, Rec: {train_rec:.4f}, F1: {train_f1:.4f}")
        print(f"  Val   - Loss: {val_loss:.4f}, Acc: {val_acc:.4f}, Prec: {val_prec:.4f}, Rec: {val_rec:.4f}, F1: {val_f1:.4f}")

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            patience_counter = 0
            torch.save({
                'epoch': epoch,
                'model_state': model.state_dict(),
                'val_f1': best_val_f1,
                'threshold': THRESHOLD,
                'feature_mins': norm_stats['feature_mins'].tolist(),
                'feature_ranges': norm_stats['feature_ranges'].tolist(),
            }, CHECKPOINT)
            print(f"  -> New best model saved (F1: {best_val_f1:.4f})")
        else:
            patience_counter += 1
            print(f"  -> No improvement ({patience_counter}/{EARLY_STOPPING_PATIENCE})")
            if patience_counter >= EARLY_STOPPING_PATIENCE:
                print(f"\nEarly stopping triggered after {epoch+1} epochs")
                break

    print("\nLoading best model for test evaluation...")
    checkpoint = torch.load(CHECKPOINT, map_location=DEVICE, weights_only=False)
    model.load_state_dict(checkpoint['model_state'])

    test_loss, test_acc, test_prec, test_rec, test_f1, test_preds, test_labels = evaluate(model, test_loader, criterion)

    print("\n" + "="*60)
    print("TEST SET RESULTS")
    print("="*60)
    print(f"Loss: {test_loss:.4f}, Accuracy: {test_acc:.4f}")
    print(f"Precision: {test_prec:.4f}, Recall: {test_rec:.4f}, F1: {test_f1:.4f}")

    print("\nClassification Report:")
    print(classification_report(test_labels, test_preds, target_names=['ham', 'spam']))

    cm = confusion_matrix(test_labels, test_preds)
    print("Confusion Matrix:")
    print(cm)

    fpr = cm[0][1] / (cm[0][0] + cm[0][1]) if (cm[0][0] + cm[0][1]) > 0 else 0
    fnr = cm[1][0] / (cm[1][0] + cm[1][1]) if (cm[1][0] + cm[1][1]) > 0 else 0

    print(f"False Positive Rate: {fpr:.4f} (ham flagged as spam)")
    print(f"False Negative Rate: {fnr:.4f} (spam missed)")

    print("\nTraining complete!")


if __name__ == "__main__":
    main()
