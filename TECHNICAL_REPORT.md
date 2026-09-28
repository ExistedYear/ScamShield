# ScamShield — Technical Report

## Multilingual Smishing Detection: XLM-RoBERTa + URL Fusion + Mobile Deployment

**Base paper:** "Enhancing Smishing Detection: A Deep Learning Approach for Improved Accuracy and Reduced False Positives" — IEEE Access, 2024 (DOI: 10.1109/ACCESS.2024.3463871)

---

## 1. Introduction & Problem Statement

### 1.1 What is Smishing?

Smishing (SMS Phishing) is a social engineering attack where fraudulent SMS messages trick recipients into revealing sensitive information — passwords, OTPs, bank account details — by impersonating trusted entities (banks, delivery services, government agencies).

### 1.2 Why Detection is Hard

- SMS messages are short (<160 chars) — limited context
- Attackers continuously evolve language to evade filters
- **Legitimate Indian transactional SMS (OTP, bank credits, recharges) resembles spam patterns** — high false positive risk
- Class imbalance: ~61% ham, ~39% spam
- Adversarial evasion: character substitution, spacing tricks, word manipulation

### 1.3 Our Contributions Over the Base Paper

| Contribution | Base Paper (CNN-LSTM) | Our System |
|---|---|---|
| Model | CNN-LSTM from scratch | **XLM-RoBERTa** (multilingual pre-trained transformer) |
| Languages | English only | **English + Hindi + Hinglish** |
| URL Analysis | None | **9 URL risk signals + Google Safe Browsing** |
| Explainability | None | **SHAP word-level explanations** |
| Adversarial Testing | None | **4 attack types tested** |
| Training Data | ~5,574 messages | **~30,000+ messages (6 sources, multilingual)** |
| Mobile App | None | **React Native Android/iOS app** |
| Indian SMS Support | None | **60+ synthetic Indian legit SMS + feature fixes** |

---

## 2. System Architecture

### 2.1 Three-Component System

```
┌─────────────────────────────────────────────────────────────┐
│  ScamShield System                                           │
│                                                             │
│  ┌──────────────────┐    HTTP    ┌──────────────────────┐  │
│  │  ScamShield      │◄──────────►│  Flask API           │  │
│  │  Mobile App      │  /predict  │  (smishing_detector) │  │
│  │  (React Native)  │  /explain  │  Port 5000           │  │
│  │  Android / iOS   │  /health   │                      │  │
│  └──────────────────┘           └──────────┬─────────────┘  │
│                                            │                │
│  ┌──────────────────┐                      │                │
│  │  KaggleTraining/ │── best_model.pt ────►│                │
│  │  (Isolated pkg)  │                      │                │
│  └──────────────────┘           ┌──────────▼─────────────┐  │
│                                 │  Google Safe Browsing  │  │
│                                 │  API (URL Verification)│  │
│                                 └────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Model Pipeline

```
SMS Message (English / Hindi / Hinglish)
    │
    ├──► XLM-RoBERTa Tokenizer → XLM-RoBERTa Encoder → CLS Token [768-d]
    │    (SentencePiece, handles Devanagari natively)          │
    ├──► URL Feature Extractor → 9 URL signals ──┐            │
    │                                            ▼            ▼
    └──► Text Feature Extractor → 8 signals → feat_proj → [64-d]
                                                         │
                                              Concatenate [832-d]
                                                         │
                                              Classifier MLP
                                              (832→256→64→1)
                                                         │
                                              Sigmoid → P(spam)
                                                         │
                                    ┌────── ≥ 0.55? ─────┤
                                    ▼                     ▼
                               SPAM/MEDIUM            HAM/LOW
                                    │
                              Has URLs?
                                    │ Yes
                                    ▼
                          Google Safe Browsing
                          All URLs clean? → Override to HAM
```

### 2.3 Project Structure

```
MAIN-EL-2/
├── smishing_detector/          ← Flask API + model inference
│   ├── app/flask_api.py        ← REST API (5 endpoints)
│   ├── predictor.py            ← Inference + GSB override
│   ├── models/model.py         ← SmishingDetector nn.Module
│   ├── models/dataset.py       ← PyTorch Dataset
│   ├── utils/data_loader.py    ← Feature engineering
│   ├── utils/safe_browsing.py  ← Google Safe Browsing client
│   ├── explainability/         ← SHAP explainer
│   ├── adversarial/            ← Robustness testing
│   └── best_model.pt           ← Trained checkpoint (~266 MB)
├── ScamShield-Mobile/          ← React Native mobile app
│   ├── App.js                  ← Root + theme
│   ├── src/screens/            ← Inbox, Scan, Detail, Settings
│   ├── src/components/         ← RiskBadge, ShapChart, ConfidenceBar…
│   └── src/services/api.js     ← Flask API client
├── KaggleTraining/             ← Isolated Kaggle training package
│   ├── train.py                ← Training entry point
│   ├── model.py                ← Architecture (same as API)
│   ├── dataset.py              ← DataLoaders
│   └── data_loader.py          ← Feature engineering (fixed)
├── .env                        ← API keys (GSB + Kaggle)
└── COMMANDS_REFERENCE.md
```

---

## 3. Technologies Used

### 3.1 Core Stack

| Layer | Technology | Purpose |
|---|---|---|
| Deep Learning | **PyTorch ≥ 2.0** | Model training, inference |
| Transformer | **HuggingFace Transformers ≥ 4.35** | XLM-RoBERTa model + tokenizer |
| NLP Model | **xlm-roberta-base** | Pre-trained multilingual encoder (270M params, 100 languages) |
| Tokenizer | **SentencePiece** | Handles Devanagari, Roman, English natively |
| Data Science | **scikit-learn, pandas, NumPy** | Metrics, splitting, normalization |
| Explainability | **SHAP ≥ 0.43** | Word-level feature attribution |
| URL Analysis | **tldextract, requests** | Domain/TLD extraction |
| API | **Flask ≥ 3.0 + flask-cors** | REST backend |
| Mobile | **React Native (Expo SDK 54)** | Cross-platform mobile app |
| Mobile Nav | **React Navigation v7** | Tab + stack navigation |
| Mobile Storage | **AsyncStorage** | Scan history, settings |
| Security | **Google Safe Browsing API v4** | URL threat verification |
| GPU | **Kaggle T4** | Training (via KaggleTraining package) |

### 3.2 Why XLM-RoBERTa over DistilBERT?

| Aspect | DistilBERT (Phase 2) | XLM-RoBERTa (Phase 3) |
|---|---|---|
| Languages | English only | 100 languages (Hindi, Urdu, Bengali...) |
| Parameters | 66M | 270M |
| Pre-training data | English Wikipedia + BooksCorpus | 2.5TB CommonCrawl (100 languages) |
| Hindi support | ❌ None | ✅ Native Devanagari via SentencePiece |
| Hinglish support | ❌ Fragmented | ✅ Handles Roman-script Hindi |
| Accuracy (English) | ~99.66% | ≥97% (target, larger model needs more data) |
| Model size | 250MB | 1.1GB |

---

## 4. Model Architecture

### 4.1 SmishingDetector (Phase 3)

```python
SmishingDetector(
  bert: XLMRobertaModel          ← xlm-roberta-base, all 12 layers trainable

  feat_proj: Sequential(
    Linear(17 → 64), ReLU(), Dropout(0.3),
    Linear(64 → 64), ReLU()
  )

  classifier: Sequential(
    Linear(832 → 256), ReLU(), Dropout(0.3),
    Linear(256 → 64), ReLU(), Dropout(0.3),
    Linear(64 → 1)      ← single logit
  )
)
```

**Input dimension:** 17 hand-crafted features (9 URL + 8 text)  
**Fusion:** CLS [768] + feat_proj [64] = **[832-d]**  
**Output:** sigmoid(logit) → P(spam) ∈ [0, 1]

### 4.2 Feature Engineering (v2 — Fixed)

#### URL Features (9 signals)

| Feature | Description |
|---|---|
| `has_url` | Message contains a URL |
| `num_urls` | URL count |
| `has_http` | Insecure HTTP |
| `has_https` | HTTPS present |
| `suspicious_tld` | `.tk`, `.xyz`, `.ml`, `.loan`, etc. |
| `max_url_len` | Longest URL length |
| `has_ip_url` | Raw IP address URL |
| `has_shortened_url` | `bit.ly`, `t.co`, etc. |
| `has_legit_domain` | Domain in whitelist OR cleared by GSB |

#### Text Features (8 signals) — v2 fixes highlighted

| Feature | Description | v2 Change |
|---|---|---|
| `num_chars` | Character count | — |
| `num_words` | Word count | — |
| `pct_upper` | % uppercase | — |
| `pct_digits` | % digits | — |
| `num_special` | Special char count | — |
| `urgency_count` | Urgency keyword matches | **Removed `account`, `verify`, `otp`** — too common in legit Indian SMS |
| `has_phone` | Contains phone number | **Fixed regex for +91 / 10-digit Indian format** |
| `has_currency` | Currency detected | **Removed `rs`, `rupee` text match — only `₹` symbol now** |

---

## 5. Training — v2 (Kaggle)

### 5.1 Configuration

| Parameter | Phase 2 (DistilBERT) | Phase 3 (XLM-RoBERTa) | Rationale |
|---|---|---|---|
| Learning Rate | 2e-5 | **1e-5** | Stable fine-tuning of larger model |
| Dropout | 0.4 | **0.3** | Larger model, less aggressive dropout |
| Frozen BERT layers | 3 | **0** | Full fine-tuning needed for multilingual |
| Batch size | 32 | **16** | XLM-RoBERTa uses more VRAM |
| pos_weight multiplier | 1.5× | **1.0×** | No artificial spam bias |
| Decision threshold | 0.50 | **0.55** | Reduce false positives on Indian SMS |
| Label smoothing | None | **0.05** | Prevents overconfident predictions |
| Early stop patience | 3 | **4** | More time to generalize |
| Max epochs | 8 | **10** | — |
| Training datasets | 4 sources | **6 sources (+ Hindi/Hinglish)** | Multilingual coverage |

### 5.2 Label Smoothing Loss

Standard BCE was replaced with a custom `LabelSmoothingBCELoss`:

```
targets_smooth = targets × (1 - ε) + ε × 0.5
```

With `ε = 0.05`: spam labels become `0.975` (not `1.0`) and ham labels become `0.025` (not `0.0`). This prevents the model from becoming overconfident and generalizes better.

### 5.3 Dataset (v2)

```
Source                                        Messages    Notes
──────────────────────────────────────────────────────────────────
UCI SMS Spam Collection                       ~5,572      Gold standard
Deysi/spam-detection (HuggingFace)            ~10,900     Large, diverse
gauravduttakiit/sms-spam (Kaggle)             ~varies     Indian SMS context
Synthetic Indian Legit SMS                    60          Hand-crafted OTP/bank
dbarbedillo multilingual (en+hi columns)      ~11,144     Hindi + English
rajnathpatel/multilingual-spam-data           ~varies     Real Hindi/Hinglish
──────────────────────────────────────────────────────────────────
After deduplication:                          ~30,000+

Split: 70% train / 15% val / 15% test (stratified)
```

**Why synthetic Indian SMS?** All 3 original datasets are Western English. The model had never seen legitimate Indian bank credits, OTP messages, or recharge confirmations — so it flagged everything with `Rs.`, `HDFC`, `credited` as spam.

### 5.4 Root Cause of Overfitting (v1)

The original model marked every Indian transactional SMS as high-risk spam (99.9% confidence) because:

1. **Distribution mismatch** — zero legitimate Indian SMS in training data
2. **`has_currency` fired on `Rs.`** — every bank SMS triggered it
3. **`urgency_count` fired on `account`, `verify`** — every bank SMS triggered it
4. **All BERT layers unfrozen** — model memorized training corpus patterns aggressively
5. **pos_weight 1.5×** — artificially pushed predictions toward spam

---

## 6. Google Safe Browsing Integration

### 6.1 How It Works

```
Model Prediction: SPAM (confidence 0.82)
        │
        └── Message has URLs?  Yes
                │
                ▼
        Extract all URLs
                │
                ▼
        Query Google Safe Browsing API v4
        (MALWARE, SOCIAL_ENGINEERING, UNWANTED_SOFTWARE)
                │
        All URLs clean?
          Yes ──────────────► Override → HAM / LOW risk
                              gsb_cleared = true in response
          No / Error ───────► Keep model prediction
```

### 6.2 API Response with GSB

```json
{
  "label": "ham",
  "confidence": 0.45,
  "risk_level": "low",
  "gsb_cleared": true,
  "url_signals": { ... },
  "text_signals": { ... }
}
```

### 6.3 Bug Fixed in v1

The original `safe_browsing.py` had an **inverted cache logic** — when GSB returned "no threats found" (domain is safe), it was storing `False` in the cache, meaning every GSB-verified clean domain was still treated as dangerous. This has been fixed.

---

## 7. Evaluation Results (v1 Model)

> Note: v2 results will be available after Kaggle retraining.

### 7.1 Core Metrics

| Metric | Our System (v1) | Paper (CNN-LSTM) | Improvement |
|---|---|---|---|
| Accuracy | **99.66%** | 97.49% | +2.17% |
| Precision (spam) | **99.46%** | ~97% | +2.46% |
| Recall (spam) | **99.67%** | ~97% | +2.67% |
| F1 (spam) | **99.57%** | 0.97 | +2.57% |
| False Positive Rate | **0.34%** | ~3% | 8.8× lower |
| ROC-AUC | **0.9999** | — | — |
| MCC | **0.9929** | — | — |

### 7.2 Confusion Matrix (v1, test set n=2,373)

```
                  Predicted
              Ham       Spam
Actual  Ham  [1446        5]   ← 5 false alarms
        Spam [   3      919]   ← 3 missed
```

### 7.3 Adversarial Robustness

| Attack | Method | F1 Drop |
|---|---|---|
| CharSwap | Replace letters with l33t-speak (30% rate) | **0.00** |
| EDA | Random word deletion + swap (20% rate) | **0.00** |
| Spacing | Insert spaces in keywords | **0.00** |
| Hybrid | All three combined | **0.00** |

Zero degradation — DistilBERT's subword tokenization is inherently robust to surface-level text manipulations.

---

## 8. Mobile Application

### 8.1 Overview

React Native (Expo) cross-platform app providing real-time SMS analysis on Android and manual scanning on iOS.

### 8.2 Screens

| Screen | Description |
|---|---|
| **Inbox** | SMS message list with risk badges; stats card (Scanned/Threats/Safe); Scan All button |
| **Scan** | Manual message input + URL extractor; full analysis on submit |
| **Detail** | SHAP chart, confidence bar, URL analysis, text signals, threat warnings, GSB badge |
| **Settings** | API URL config + connectivity test, auto-scan toggle, dark/light theme, history management |

### 8.3 Key Components

| Component | Purpose |
|---|---|
| `RiskBadge` | Color-coded pill (green=low, amber=medium, red=high) |
| `ConfidenceBar` | Animated probability bar |
| `ShapChart` | Horizontal bar chart of top spam/ham word contributions |
| `UrlAnalysis` | Per-URL safety breakdown with risk indicators |

### 8.4 API Integration

```
Mobile App → POST /predict  → Risk label, confidence, signals, gsb_cleared
           → POST /explain  → SHAP top_spam_words, top_ham_words
           → POST /check-domain → Google Safe Browsing result
           → GET  /health   → API connectivity check
```

### 8.5 Build

```bash
eas build --platform android --profile preview   # → .apk
eas build --platform android --profile production # → signed .apk
```

---

## 9. API Endpoints

| Endpoint | Method | Input | Output |
|---|---|---|---|
| `/health` | GET | — | `{status, model}` |
| `/predict` | POST | `{message}` | `{label, confidence, risk_level, gsb_cleared, url_signals, text_signals}` |
| `/explain` | POST | `{message}` | `{label, confidence, top_spam_words, top_ham_words, feature_importances}` |
| `/batch_predict` | POST | `{messages[]}` | `{results[], count}` |
| `/check-domain` | POST | `{domain}` | `{domain, is_legitimate, status}` |

---

## 10. Key Design Decisions

| Decision | Rationale |
|---|---|
| XLM-RoBERTa over DistilBERT | 100-language support, Devanagari native, same 768-d hidden size |
| All layers unfrozen | Multilingual fine-tuning needs full gradient flow through all 12 layers |
| Late fusion (concatenation) | BERT and hand-crafted features learn independently before combining |
| 17 hand-crafted features | Language-agnostic URL signals that XLM-RoBERTa alone cannot extract |
| GSB post-prediction override | URLs are the most reliable spam signal — trust GSB over model alone |
| Threshold 0.55 (not 0.50) | Reduces false positives on borderline cases (Indian bank SMS) |
| Label smoothing 0.05 | Prevents overconfident predictions on training distribution |
| Batch size 16 (not 32) | XLM-RoBERTa (1.1GB) needs more VRAM per forward pass than DistilBERT |
| Stratified 70/15/15 split | Maintains spam/ham ratio across all data splits |
| Normalization from train only | Prevents data leakage from val/test into normalization statistics |
| Synthetic Indian SMS | Corrects training distribution bias against Indian transactional messages |

---

## 11. Hardware & Performance

| Component | Spec |
|---|---|
| GPU (training) | Kaggle T4 (via KaggleTraining package) |
| RAM | 16 GB recommended |
| Storage | ~1.3 GB (model ~1.1 GB + cached XLM-RoBERTa weights) |
| Training time | ~45–90 min (Kaggle T4) |
| Inference latency | ~100 ms/message (GPU), ~500 ms (CPU) |
| API response time | ~600 ms (includes GSB lookup) |

---

## 12. Future Work

1. **Real-time SMS** — Android broadcast receiver for automatic scanning on SMS receive
2. **On-device inference** — Export to ONNX/TFLite for offline mobile prediction
3. **Active URL scanning** — Follow redirects, analyze page content
4. **More Indian languages** — Tamil, Telugu, Kannada, Bengali via IndicBERT
5. **Federated learning** — Train across devices without centralizing SMS data
6. **Continuous learning** — Periodic model updates from newly reported scam patterns
7. **Domain age check** — WHOIS lookup as additional URL feature
8. **Tranco list** — Replace hardcoded LEGIT_DOMAINS whitelist with Tranco top-1M
