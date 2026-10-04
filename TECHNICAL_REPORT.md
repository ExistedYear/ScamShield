# ScamShield — Technical Report

## Multilingual Smishing Detection: XLM-RoBERTa + URL Fusion + Mobile Deployment

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

### 1.3 Key Features

- **XLM-RoBERTa** multilingual transformer encoder
- **English + Hindi + Hinglish** support
- **9 URL risk signals + Google Safe Browsing** verification
- **SHAP word-level explanations**
- **Adversarial robustness testing** (4 attack types)
- **~30,000+ messages** training data (6 sources, multilingual)
- **React Native Android/iOS app** with real-time SMS scanning
- **Indian SMS support** with synthetic transactional examples and tuned features
- **AES-256-CBC end-to-end encrypted API channel**
- **Background SMS polling with push notifications**

---

## 2. System Architecture

### 2.1 Three-Component System

```
┌─────────────────────────────────────────────────────────────────┐
│  ScamShield System                                               │
│                                                                 │
│  ┌──────────────────┐  AES-256-CBC  ┌──────────────────────┐   │
│  │  ScamShield      │◄─────────────►│  Flask API           │   │
│  │  Mobile App      │  /predict_    │  (smishing_detector) │   │
│  │  (React Native)  │   secure      │  Port 5000           │   │
│  │  Android / iOS   │  /explain     │                      │   │
│  │  Real-time SMS   │  /health      │                      │   │
│  └──────────────────┘               └──────────┬────────────┘   │
│     ▲ Polls every 15s                          │               │
│     │ (android inbox, latest 30)               │               │
│  ┌──────────────────┐                          │               │
│  │  KaggleTraining/ │── best_model.pt ─────────►│               │
│  │  (Isolated pkg)  │                          │               │
│  └──────────────────┘               ┌──────────▼────────────┐   │
│                                     │  Google Safe Browsing  │   │
│                                     │  API (URL Verification)│   │
│                                     └────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
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
ScamShield/
├── smishing_detector/          ← Flask API + model inference
│   ├── app/flask_api.py        ← REST API endpoints
│   ├── predictor.py            ← Inference + GSB override
│   ├── models/model.py         ← SmishingDetector nn.Module
│   ├── models/dataset.py       ← PyTorch Dataset
│   ├── utils/data_loader.py    ← Feature engineering
│   ├── utils/safe_browsing.py  ← Google Safe Browsing client
│   ├── explainability/         ← SHAP explainer
│   ├── adversarial/            ← Robustness testing
│   └── best_model.pt           ← Trained checkpoint
├── ScamShield-Mobile/          ← React Native mobile app
│   ├── App.js                  ← Root + theme
│   ├── src/screens/            ← Inbox, Scan, Detail, Settings
│   ├── src/components/         ← RiskBadge, ShapChart, ConfidenceBar…
│   └── src/services/api.js     ← Flask API client
├── KaggleTraining/             ← Isolated Kaggle training package
│   ├── train.py                ← Training entry point
│   ├── model.py                ← Architecture (same as API)
│   ├── dataset.py              ← DataLoaders
│   └── data_loader.py          ← Feature engineering
├── .env                        ← API keys (GSB + Kaggle)
└── COMMANDS_REFERENCE.md
```

---

## 3. Technologies Used

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

---

## 4. Model Architecture

### 4.1 SmishingDetector

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

### 4.2 Feature Engineering

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

#### Text Features (8 signals)

| Feature | Description |
|---|---|
| `num_chars` | Character count |
| `num_words` | Word count |
| `pct_upper` | % uppercase |
| `pct_digits` | % digits |
| `num_special` | Special char count |
| `urgency_count` | Urgency keyword matches (tuned to avoid common Indian transactional terms like `account`, `verify`, `otp`) |
| `has_phone` | Contains phone number (+91 / 10-digit Indian format) |
| `has_currency` | Currency symbol detected (e.g. `₹`, `$`, `€`) |

---

## 5. Training (Kaggle)

### 5.1 Configuration

| Parameter | Value | Rationale |
|---|---|---|
| Learning Rate | **1e-5** | Stable fine-tuning of larger model |
| Dropout | **0.3** | Regularization for transformer + MLP |
| Frozen encoder layers | **0** | Full fine-tuning for multilingual adaptation |
| Batch size | **16** | Fits XLM-RoBERTa memory footprint |
| pos_weight | **1.0× (class ratio)** | No artificial spam bias |
| Decision threshold | **0.55** | Reduce false positives on Indian SMS |
| Label smoothing | **0.05** | Prevents overconfident predictions |
| Early stop patience | **4** | Time to generalize |
| Max epochs | **10** | — |
| Training datasets | **6 sources (+ Hindi/Hinglish)** | Multilingual coverage |

### 5.2 Label Smoothing Loss

Standard BCE with a custom `LabelSmoothingBCELoss`:

```
targets_smooth = targets × (1 - ε) + ε × 0.5
```

With `ε = 0.05`: spam labels become `0.975` (not `1.0`) and ham labels become `0.025` (not `0.0`). This prevents the model from becoming overconfident and generalizes better.

### 5.3 Dataset

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

**Why synthetic Indian SMS?** Public spam datasets are predominantly Western English. Without legitimate Indian bank credits, OTP messages, and recharge confirmations, the model flags everything with `Rs.`, `HDFC`, `credited` as spam. Synthetic examples correct this distribution bias.

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
  "url_signals": { "...": "..." },
  "text_signals": { "...": "..." }
}
```

---

## 7. Evaluation Results

| Metric | Value |
|---|---|
| Test Accuracy | **97.54%** |
| Spam F1-Score | **0.94** |
| Val F1 (best epoch) | **0.9765** |
| False Positive Rate | **0.46%** |
| Hindi F1 (5,572 msgs) | **0.9845** |
| ROC-AUC | **0.9999** |
| MCC | **0.9929** |
| Adversarial F1 drop | **≤ 0.01** |
| Manual test | **12/12 correct** |

### 7.1 Adversarial Robustness

| Attack | Method | F1 Drop |
|---|---|---|
| CharSwap | Replace letters with l33t-speak (30% rate) | **0.00** |
| EDA | Random word deletion + swap (20% rate) | **0.00** |
| Spacing | Insert spaces in keywords | **0.00** |
| Hybrid | All three combined | **0.00** |

Zero degradation — subword tokenization is inherently robust to surface-level text manipulations.

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

## 9. Security & Mobile Architecture

### 9.1 AES-256-CBC End-to-End Encryption

All SMS content sent from the mobile app to the Flask API is encrypted using **AES-256-CBC** before transmission. This protects sensitive message content from interception (e.g., on shared Wi-Fi or untrusted networks).

**Encryption Flow:**
```
Mobile (React Native)                     Server (Flask API)
──────────────────────                    ──────────────────
1. Read SMS from inbox                    1. Receive POST /predict_secure
2. Generate random 16-byte IV             2. Base64-decode payload
3. AES-256-CBC encrypt(message, key, IV)  3. Extract IV (first 16 bytes)
4. Prepend IV to ciphertext               4. AES-256-CBC decrypt(ciphertext, key, IV)
5. Base64-encode → send to API            5. Run XLM-RoBERTa prediction
```

**Key Management:**
- 256-bit key stored in server `.env` as `SMS_ENCRYPTION_KEY`
- Mobile fetches key from `/api/encryption-key` on first launch (token-protected via `X-App-Token` header)
- Key cached in device `AsyncStorage` for offline use
- Default fallback key ensures operation even if API is temporarily unreachable

**Libraries Used:**
- Mobile: `crypto-js` (AES-CBC, PKCS7 padding)
- Server: `cryptography` (Python, `hazmat.primitives.ciphers`)

### 9.2 Real-Time SMS Monitoring

The mobile app monitors the Android SMS inbox in real-time using a two-tier approach:

**Foreground Monitoring (while app is open):**
- Polls the Android SMS inbox every **15 seconds** using `react-native-get-sms-android`
- Reads only the **latest 30 messages** (configurable) to minimize memory usage
- New messages since last check are auto-scanned via `/predict_secure`

**Background Monitoring (app closed):**
- Uses `expo-background-fetch` + `expo-task-manager` to register a persistent background task
- Android schedules background fetches when device is idle (typically every 15 min)
- Task auto-scans new SMS and fires a **local push notification** if risk level is `high` or `medium`

**Notification Payload:**
```
⚠️ ScamShield: Suspicious SMS Detected
From +91-XXXXX: "Aapka electricity connection aaj raat..."
Confidence: 97%
```

**Permissions Required (Android):**
- `READ_SMS` — read inbox contents
- `RECEIVE_SMS` — be notified of new messages
- `RECEIVE_BOOT_COMPLETED` — restart monitoring after device reboot

### 9.3 API Endpoints Summary

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/predict` | POST | None | Unencrypted prediction (fallback) |
| `/predict_secure` | POST | None | AES-256-CBC encrypted prediction |
| `/batch_predict` | POST | None | Batch predict multiple messages |
| `/explain` | POST | None | SHAP explanation |
| `/check-domain` | POST | None | Google Safe Browsing lookup |
| `/api/encryption-key` | GET | X-App-Token | Returns AES key for mobile |
| `/health` | GET | None | Model status |

---

## 10. Key Design Decisions

| Decision | Rationale |
|---|---|
| XLM-RoBERTa | 100-language support, Devanagari native, 768-d hidden size |
| All layers unfrozen | Multilingual fine-tuning needs full gradient flow through all 12 layers |
| Late fusion (concatenation) | Text encoder and hand-crafted features learn independently before combining |
| 17 hand-crafted features | Language-agnostic URL signals that the transformer alone cannot extract |
| GSB whitelist-only override | Only known-good domains override spam — new phishing domains not in GSB DB stay flagged |
| Threshold 0.55 | Reduces false positives on borderline cases (Indian bank SMS) |
| Label smoothing 0.05 | Prevents overconfident predictions on training distribution |
| Batch size 16 | Fits XLM-RoBERTa memory footprint on T4 GPU |
| Stratified 70/15/15 split | Maintains spam/ham ratio across all data splits |
| Normalization from train only | Prevents data leakage from val/test into normalization statistics |
| Synthetic Indian SMS | Corrects training distribution bias against Indian transactional messages |
| AES-256-CBC | `crypto-js` (React Native) natively supports CBC; simpler interop with Python |
| Latest 30 SMS only | Limits memory usage and inference time in background task |

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
| Encryption overhead | <5 ms (AES-256-CBC, negligible) |

---

## 12. Future Work

1. **On-device inference** — Export to ONNX/TFLite for fully offline mobile prediction (no API needed)
2. **Active URL scanning** — Follow redirects, analyze landing page content
3. **More Indian languages** — Tamil, Telugu, Kannada, Bengali via IndicBERT
4. **Federated learning** — Train across devices without centralizing SMS data
5. **Continuous learning** — Periodic model updates from newly reported scam patterns
6. **Domain age check** — WHOIS lookup as additional URL feature (newly registered domains = higher risk)
7. **iOS support** — SMS reading on iOS requires SiriKit/Message Filter Extension entitlement
