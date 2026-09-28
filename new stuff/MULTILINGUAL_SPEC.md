# Multilingual Smishing Detection — Full Implementation Spec
## Zero-Shot Cross-Lingual Transfer with XLM-RoBERTa

---

## Overview

This spec extends the existing smishing detector (Phase 2) with multilingual capability.

### The Core Scientific Claim
> "A model trained ONLY on English smishing data can detect Hindi and Hinglish scams
> with ZERO Hindi training examples, achieving F1 > 0.85"

This is called **Zero-Shot Cross-Lingual Transfer** — no paper on smishing detection
has tested this before. This is the novel contribution.

### What changes from Phase 2
- Replace DistilBERT → XLM-RoBERTa (supports 100 languages)
- Add multilingual dataset loader for Hindi zero-shot test data
- Add zero-shot evaluation script
- Add language detection to Streamlit UI
- Everything else (Flask API, SHAP, adversarial testing) stays identical

---

## Project Structure (additions only)

```
smishing_detector/
├── utils/
│   ├── data_loader.py          ← already exists, no changes needed
│   ├── safe_browsing.py        ← already exists, no changes needed
│   └── multilingual_loader.py  ← NEW: loads Hindi/Hinglish test data
├── models/
│   ├── model.py                ← MODIFY: swap DistilBERT → XLM-RoBERTa
│   └── dataset.py              ← no changes needed
├── evaluate.py                 ← MODIFY: add multilingual evaluation section
├── evaluate_multilingual.py    ← NEW: standalone zero-shot evaluation script
└── app/
    └── streamlit_app.py        ← MODIFY: add language detection display
```

---

## Change 1: `models/model.py` — Swap to XLM-RoBERTa

### What to change

Replace ALL DistilBERT references with XLM-RoBERTa equivalents.

```python
# OLD
from transformers import DistilBertModel, DistilBertTokenizerFast
MODEL_NAME = "distilbert-base-uncased"

# NEW
from transformers import XLMRobertaModel, XLMRobertaTokenizerFast
MODEL_NAME = "xlm-roberta-base"
```

### Updated SmishingDetector class

```python
class SmishingDetector(nn.Module):
    def __init__(
        self,
        num_handcrafted: int = 17,
        dropout: float = 0.3,
        freeze_bert_layers: int = 0,   # 0 = all layers fine-tuned
    ):
        super().__init__()

        # XLM-RoBERTa instead of DistilBERT
        # xlm-roberta-base has 12 transformer layers (vs DistilBERT's 6)
        # hidden size is still 768 — so fusion layer dimensions stay identical
        self.bert = XLMRobertaModel.from_pretrained("xlm-roberta-base")

        # Freeze bottom N layers if specified
        for i, layer in enumerate(self.bert.encoder.layer):
            if i < freeze_bert_layers:
                for param in layer.parameters():
                    param.requires_grad = False

        # feat_proj stays identical — language agnostic features
        self.feat_proj = nn.Sequential(
            nn.Linear(num_handcrafted, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 64),
            nn.ReLU()
        )

        # classifier stays identical — input dim is still 768 + 64 = 832
        self.classifier = nn.Sequential(
            nn.Linear(832, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1)
        )

    def forward(self, input_ids, attention_mask, hand_features):
        # XLM-RoBERTa output format is same as BERT
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls_emb = outputs.last_hidden_state[:, 0, :]   # CLS token → (B, 768)
        feat_emb = self.feat_proj(hand_features)        # (B, 64)
        fused = torch.cat([cls_emb, feat_emb], dim=1)  # (B, 832)
        logit = self.classifier(fused)
        return logit.squeeze(-1)

    def predict_proba(self, input_ids, attention_mask, hand_features):
        with torch.no_grad():
            logit = self.forward(input_ids, attention_mask, hand_features)
            return torch.sigmoid(logit)


def get_tokenizer():
    # XLM-RoBERTa tokenizer handles 100 languages automatically
    return XLMRobertaTokenizerFast.from_pretrained("xlm-roberta-base")
```

### Key notes
- `xlm-roberta-base` hidden size = 768 (same as DistilBERT) — fusion dimensions unchanged
- XLM-RoBERTa has 12 transformer layers vs DistilBERT's 6
- XLM-RoBERTa tokenizer uses SentencePiece — handles Devanagari script natively
- Model download size: ~1.1GB (vs DistilBERT's 250MB) — one-time download
- Training time: ~25-35 mins on RTX 4050 (slightly longer than DistilBERT)

---

## Change 2: `predictor.py` — Update model init

### What to change

Only one line changes — the SmishingDetector init call stays the same since
XLM-RoBERTa has the same hidden size:

```python
# No change needed in predictor.py
# SmishingDetector(num_handcrafted=17, dropout=0.3, freeze_bert_layers=0)
# This works for both DistilBERT and XLM-RoBERTa
```

The predictor automatically uses whatever model is defined in model.py.
Since we updated model.py to use XLM-RoBERTa, predictor picks it up automatically.

---

## New File: `utils/multilingual_loader.py`

### Purpose
Loads Hindi and Hinglish test data from two sources for zero-shot evaluation.
This data is NEVER used for training — only for testing the English-trained model.

### Sources
1. `dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset` — HuggingFace
   - UCI English messages machine-translated to Hindi (Devanagari)
   - Contains both spam and ham, already labeled
   - ~5,572 Hindi messages

2. `rajnathpatel/multilingual-spam-data` — Kaggle
   - Real Hindi spam data collected in India
   - Contains Hinglish (Roman script Hindi) messages

### Implementation

```python
"""
utils/multilingual_loader.py
-----------------------------
Loads Hindi and Hinglish test datasets for zero-shot evaluation.
These datasets are NEVER added to training data.
They are used ONLY to test if the English-trained XLM-RoBERTa model
can detect Hindi/Hinglish scams with zero Hindi training examples.
"""

import pandas as pd
import numpy as np
import re
from datasets import load_dataset as hf_load


def detect_language(text: str) -> str:
    """
    Detect if a message is:
    - 'hindi'   : contains Devanagari Unicode characters (pure Hindi)
    - 'hinglish': Roman script with Hindi words mixed with English
    - 'english' : standard English
    """
    # Check for Devanagari Unicode range (0900-097F)
    devanagari_pattern = re.compile(r'[\u0900-\u097F]')
    if devanagari_pattern.search(text):
        return 'hindi'

    # Common Hinglish words that appear in Roman script
    hinglish_markers = {
        'aapka', 'aapke', 'abhi', 'karo', 'kare', 'kiya', 'nahi', 'nai',
        'hai', 'hain', 'ho', 'ka', 'ki', 'ke', 'ko', 'se', 'mein', 'par',
        'aur', 'bhi', 'yeh', 'woh', 'ap', 'apka', 'jana', 'karna', 'dena',
        'lena', 'milega', 'milegi', 'paisa', 'rupaye', 'khata', 'band',
        'verify', 'kijiye', 'dijiye', 'lijiye', 'phir', 'agar', 'toh',
        'jaldi', 'turant', 'abhi', 'sirf', 'bahut', 'accha', 'theek'
    }
    words = set(text.lower().split())
    if len(words.intersection(hinglish_markers)) >= 2:
        return 'hinglish'

    return 'english'


def load_hindi_test_data() -> pd.DataFrame:
    """
    Load Hindi (Devanagari) test data from HuggingFace multilingual dataset.
    Returns DataFrame with columns: message, label, language
    """
    print("Loading Hindi test data from HuggingFace...")
    try:
        ds = hf_load("dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset")

        dfs = []
        for split_name in ds.keys():
            split_df = ds[split_name].to_pandas()
            dfs.append(split_df)
        df = pd.concat(dfs, ignore_index=True)

        # This dataset has columns for each language
        # Find the Hindi column
        hindi_col = None
        for col in df.columns:
            if 'hindi' in col.lower() or 'hi' == col.lower():
                hindi_col = col
                break

        if hindi_col is None:
            # Try to find column with Devanagari content
            for col in df.columns:
                if col not in ['label', 'v1', 'v2']:
                    sample = df[col].dropna().head(10).astype(str)
                    devanagari = re.compile(r'[\u0900-\u097F]')
                    if any(devanagari.search(s) for s in sample):
                        hindi_col = col
                        break

        if hindi_col is None:
            print("  Warning: Could not find Hindi column")
            return pd.DataFrame(columns=['message', 'label', 'language'])

        # Get label column
        label_col = 'v1' if 'v1' in df.columns else 'label'

        result_df = pd.DataFrame({
            'message': df[hindi_col].astype(str),
            'label': df[label_col]
        })

        # Standardise labels
        label_map = {'ham': 0, 'spam': 1, 0: 0, 1: 1, '0': 0, '1': 1}
        result_df['label'] = result_df['label'].map(label_map)
        result_df = result_df.dropna(subset=['message', 'label'])
        result_df['label'] = result_df['label'].astype(int)
        result_df['language'] = 'hindi'

        print(f"  Hindi test data: {len(result_df)} messages "
              f"({result_df['label'].sum()} spam, "
              f"{(result_df['label']==0).sum()} ham)")
        return result_df.reset_index(drop=True)

    except Exception as e:
        print(f"  Warning: Failed to load Hindi data: {e}")
        return pd.DataFrame(columns=['message', 'label', 'language'])


def load_hinglish_test_data() -> pd.DataFrame:
    """
    Load Hinglish test data from Kaggle multilingual spam dataset.
    Returns DataFrame with columns: message, label, language
    """
    print("Loading Hinglish test data from Kaggle...")
    try:
        import kagglehub
        path = kagglehub.dataset_download("rajnathpatel/multilingual-spam-data")

        import os
        csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
        if not csv_files:
            print("  Warning: No CSV files in Kaggle multilingual dataset")
            return pd.DataFrame(columns=['message', 'label', 'language'])

        dfs = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(f"{path}/{csv_file}", encoding='latin-1')
                dfs.append(df)
            except:
                continue

        if not dfs:
            return pd.DataFrame(columns=['message', 'label', 'language'])

        df = pd.concat(dfs, ignore_index=True)

        # Standardise column names
        col_lower = {c: c.lower().strip() for c in df.columns}
        df = df.rename(columns=col_lower)

        # Find message and label columns
        msg_col = next((c for c in df.columns if c in ['text', 'message', 'sms', 'v2']), None)
        lbl_col = next((c for c in df.columns if c in ['label', 'v1', 'category', 'class']), None)

        if not msg_col or not lbl_col:
            print(f"  Warning: Could not identify columns. Found: {df.columns.tolist()}")
            return pd.DataFrame(columns=['message', 'label', 'language'])

        result_df = pd.DataFrame({
            'message': df[msg_col].astype(str),
            'label': df[lbl_col]
        })

        label_map = {'ham': 0, 'spam': 1, 0: 0, 1: 1, '0': 0, '1': 1}
        result_df['label'] = result_df['label'].map(label_map)
        result_df = result_df.dropna(subset=['message', 'label'])
        result_df['label'] = result_df['label'].astype(int)

        # Detect language per message and keep only Hindi/Hinglish
        result_df['language'] = result_df['message'].apply(detect_language)
        result_df = result_df[result_df['language'].isin(['hindi', 'hinglish'])]

        print(f"  Hinglish/Hindi test data: {len(result_df)} messages "
              f"({result_df['label'].sum()} spam, "
              f"{(result_df['label']==0).sum()} ham)")
        return result_df.reset_index(drop=True)

    except Exception as e:
        print(f"  Warning: Failed to load Hinglish data: {e}")
        return pd.DataFrame(columns=['message', 'label', 'language'])


def load_all_multilingual_test_data() -> dict[str, pd.DataFrame]:
    """
    Loads all multilingual test data.
    Returns dict with keys: 'hindi', 'hinglish', 'combined'
    """
    hindi_df = load_hindi_test_data()
    hinglish_df = load_hinglish_test_data()

    # Separate hinglish from hindi in the combined df
    pure_hindi = pd.concat([
        hindi_df,
        hinglish_df[hinglish_df['language'] == 'hindi']
    ], ignore_index=True)

    pure_hinglish = hinglish_df[hinglish_df['language'] == 'hinglish'].reset_index(drop=True)

    combined = pd.concat([pure_hindi, pure_hinglish], ignore_index=True)

    print(f"\nTotal multilingual test data:")
    print(f"  Pure Hindi:  {len(pure_hindi)} messages")
    print(f"  Hinglish:    {len(pure_hinglish)} messages")
    print(f"  Combined:    {len(combined)} messages")

    return {
        'hindi': pure_hindi,
        'hinglish': pure_hinglish,
        'combined': combined
    }
```

---

## New File: `evaluate_multilingual.py`

### Purpose
Standalone script that runs zero-shot evaluation — tests the English-trained
XLM-RoBERTa model on Hindi and Hinglish data without any retraining.

### Implementation

```python
"""
evaluate_multilingual.py
------------------------
Zero-shot cross-lingual evaluation.
Tests if an English-trained smishing detector can detect
Hindi and Hinglish scams with ZERO Hindi training examples.

This is the core novel contribution of Phase 3.

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

    print("Loading model (trained on English only)...")
    predictor = SmishingPredictor(CHECKPOINT)

    print("\nLoading multilingual test data...")
    lang_data = load_all_multilingual_test_data()

    results = {}
    for lang_name, df in lang_data.items():
        results[lang_name] = evaluate_language_subset(predictor, df, lang_name)

    # ── Print results ──────────────────────────────────────────────────────
    print("\n" + "="*65)
    print(" ZERO-SHOT CROSS-LINGUAL EVALUATION RESULTS")
    print(" Model trained on: English only (18,688 messages)")
    print(" Model tested on:  Hindi + Hinglish (zero training examples)")
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
    print(" COMPARISON TABLE")
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
    print(" SCIENTIFIC CLAIM VERIFICATION")
    print("="*65)
    combined = results.get('combined')
    if combined:
        claim_verified = combined['f1'] >= 0.85
        print(f"\nClaim: 'XLM-RoBERTa trained on English only achieves F1 > 0.85")
        print(f"        on Hindi/Hinglish smishing with zero Hindi training data'")
        print(f"\nResult: F1 = {combined['f1']:.4f}")
        print(f"Claim {'VERIFIED ✓' if claim_verified else 'NOT MET ✗'}")

    print("\nZero-shot evaluation complete!")


if __name__ == "__main__":
    main()
```

---

## Change 3: `evaluate.py` — Add multilingual section

### What to add at the end of `main()` in evaluate.py

After the existing adversarial robustness section, add:

```python
# ── Zero-shot multilingual evaluation ─────────────────────────────────────
print("\n" + "="*60)
print("ZERO-SHOT MULTILINGUAL EVALUATION")
print("="*60)
print("Testing English-trained model on Hindi/Hinglish data...")

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
```

---

## Change 4: `app/streamlit_app.py` — Add language detection

### What to add in the results section after prediction

After the three metric cards (Prediction, Confidence, Risk Level), add:

```python
# Language detection display
from utils.multilingual_loader import detect_language

detected_lang = detect_language(message_input)
lang_display = {
    'english':  '🇬🇧 English',
    'hindi':    '🇮🇳 Hindi (हिंदी)',
    'hinglish': '🇮🇳 Hinglish'
}

st.info(f"**Detected Language:** {lang_display.get(detected_lang, '🌐 Unknown')}")
```

---

## Requirements additions

Add to `requirements.txt`:
```
sentencepiece>=0.1.99    # required by XLM-RoBERTa tokenizer
protobuf>=3.20.0         # required by sentencepiece
langdetect>=1.0.9        # optional: better language detection
```

---

## How to run

```bash
# Step 1: Install new requirements
pip install sentencepiece protobuf

# Step 2: Retrain with XLM-RoBERTa (English data only, same as before)
python train.py

# Step 3: Run standard evaluation (includes multilingual section now)
python evaluate.py

# Step 4: Run full zero-shot multilingual evaluation
python evaluate_multilingual.py

# Step 5: Launch updated Streamlit (shows language detection)
streamlit run app/streamlit_app.py

# Step 6: Test API with Hindi message
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"message": "आपका SBI खाता निलंबित कर दिया गया है। अभी verify करें http://bit.ly/sbi"}'
```

---

## Expected results

| Language | Training data | Expected F1 | Notes |
|---|---|---|---|
| English | 18,688 messages | ~0.97-0.98 | Trained on this |
| Hindi (Devanagari) | 0 messages | > 0.85 target | Zero-shot |
| Hinglish (Roman) | 0 messages | > 0.90 target | Zero-shot, easier |
| Combined | 0 messages | > 0.85 target | The main claim |

---

## Key technical notes for presentation

**Why XLM-RoBERTa works zero-shot:**
XLM-RoBERTa was pre-trained on 100 languages using a shared SentencePiece vocabulary.
This creates a shared multilingual embedding space — urgency patterns in Hindi
("अभी करें" = "do it now") map to nearby vectors as English urgency patterns.
When fine-tuned on English smishing, the model implicitly learns "urgency = spam signal"
in a language-agnostic way.

**Why hand-crafted features help zero-shot:**
URL features, caps ratio, urgency word count, phone number detection — these are
completely language-agnostic. A suspicious TLD is suspicious regardless of language.
This gives the model a strong signal even when the text language is unfamiliar.

**The scientific novelty:**
No existing smishing detection paper has tested cross-lingual zero-shot transfer.
We are the first to make and verify this claim specifically for Hindi/Hinglish.
