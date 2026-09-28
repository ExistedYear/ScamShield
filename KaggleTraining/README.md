# ScamShield — Kaggle Training Package (Phase 3)

Self-contained training code for the multilingual SmishingDetector model.
Upload this folder to a Kaggle notebook and run `train.py`.

## Files

| File | Purpose |
|---|---|
| `train.py` | Entry point — training loop, evaluation |
| `model.py` | SmishingDetector architecture (XLM-RoBERTa + MLP) |
| `dataset.py` | SMSDataset + DataLoader builder |
| `data_loader.py` | Feature engineering + multi-source dataset loading |
| `requirements.txt` | pip dependencies |

## How to run on Kaggle

1. Create a new **Kaggle Notebook** (GPU T4 x2 recommended)
2. Upload this entire folder as a **Dataset** attachment
3. In the notebook's first cell:

```python
import subprocess
subprocess.run(["pip", "install", "-q", "-r", "/kaggle/input/scamshield-training/requirements.txt"])
import sys
sys.path.insert(0, "/kaggle/input/scamshield-training")
```

4. Then run:
```python
exec(open("/kaggle/input/scamshield-training/train.py").read())
```

Or copy all `.py` files to `/kaggle/working/` and run:
```bash
python train.py
```

5. After training, download `best_model.pt` from Kaggle output and replace the one in `smishing_detector/`.

> **Note:** XLM-RoBERTa (`xlm-roberta-base`) will be downloaded automatically on first run (~1.1 GB). On Kaggle, this happens from HuggingFace Hub — make sure internet is enabled in notebook settings.

## What changed from Phase 2

| Setting | Phase 2 (DistilBERT) | Phase 3 (XLM-RoBERTa) |
|---|---|---|
| Model | DistilBERT-base-uncased | **xlm-roberta-base** |
| Languages | English only | **English + Hindi + Hinglish** |
| Frozen BERT layers | 3 | **0 (all fine-tuned)** |
| Dropout | 0.4 | **0.3** |
| Batch size | 32 | **16 (XLM-RoBERTa is heavier)** |
| LR | 1e-5 | 1e-5 (unchanged) |
| Threshold | 0.55 | 0.55 (unchanged) |
| Label smoothing | 0.05 | 0.05 (unchanged) |
| Early stop patience | 4 | 4 (unchanged) |

## Data sources (Phase 3)

| Source | Type | Messages |
|---|---|---|
| `uciml/sms-spam-collection-dataset` (Kaggle) | English | ~5,572 |
| `Deysi/spam-detection-dataset` (HuggingFace) | English | ~10,900 |
| `gauravduttakiit/sms-spam` (Kaggle) | English, Indian context | ~varies |
| Synthetic Indian legit SMS | English/Indian | 60 |
| `dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset` (HuggingFace) | **English + Hindi columns only** | ~11,144 |
| `rajnathpatel/multilingual-spam-data` (Kaggle) | **Real Hindi/Hinglish** | ~varies |

After deduplication: **~30,000+ messages** expected.

## Kaggle credentials required

These datasets need your Kaggle API key in the environment:
- `uciml/sms-spam-collection-dataset`
- `gauravduttakiit/sms-spam`
- `rajnathpatel/multilingual-spam-data`

Set `KAGGLE_USERNAME` and `KAGGLE_KEY` as Kaggle notebook secrets, or add your `kaggle.json`.

## Expected results after retraining

- English F1: **≥ 0.97**
- Hindi F1: **≥ 0.92** (now trained on Hindi data)
- Hinglish F1: **≥ 0.93**
- False Positive Rate (ham flagged as spam): **< 5%**
