# ScamShield — Commands Reference

Complete guide to running every component of the ScamShield system.
**Model:** XLM-RoBERTa (xlm-roberta-base) — multilingual, English + Hindi + Hinglish

## Project Structure

```
MAIN-EL-2/
├── smishing_detector/      ← Flask API + model inference
├── ScamShield-Mobile/      ← React Native mobile app
├── KaggleTraining/         ← Kaggle training package
├── models/                 ← Downloaded model checkpoints
├── venv/                   ← Python virtual environment
├── .env                    ← API keys (GSB + Kaggle)
└── COMMANDS_REFERENCE.md   ← This file
```

---

## Prerequisites

### Project Root

All commands run from the project root unless stated otherwise:

```bash
cd /home/neeraj/Projects/MAIN-EL-2
```

### Activate Virtual Environment

Always activate before running any Python command:

```bash
source venv/bin/activate
```

> You'll see `(venv)` in your prompt when active.

---

## 1. Installation

### Install Python Dependencies

```bash
source venv/bin/activate
pip install -r smishing_detector/requirements.txt
```

### Verify GPU

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
```

### Verify All Imports

```bash
python -c "import torch, transformers, sklearn, pandas, numpy, shap, flask, tldextract, sentencepiece; print('All OK — PyTorch', torch.__version__)"
```

---

## 2. Flask API

### Start the API

```bash
source venv/bin/activate
cd smishing_detector
python -m app.flask_api
```

**Runs at:** `http://localhost:5000`  
**Web UI at:** `http://localhost:5000` (opens the ScamShield dashboard)

### Health Check

```bash
curl http://localhost:5000/health
```

### Predict a Message

```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"message": "URGENT: Your SBI account suspended. Click http://sbi-kyc.xyz/verify now"}'
```

### SHAP Explanation

```bash
curl -X POST http://localhost:5000/explain \
  -H "Content-Type: application/json" \
  -d '{"message": "Congratulations! You won Rs.50,000. Claim at http://prize.tk/win"}'
```

### Batch Predict

```bash
curl -X POST http://localhost:5000/batch_predict \
  -H "Content-Type: application/json" \
  -d '{"messages": ["Your OTP is 483921. Do not share.", "URGENT: Click http://scam.xyz now!", "Airtel recharge Rs.239 successful."]}'
```

### Check Domain Safety (Google Safe Browsing)

```bash
curl -X POST http://localhost:5000/check-domain \
  -H "Content-Type: application/json" \
  -d '{"domain": "sbi-kyc.xyz"}'
```

### Make API Publicly Accessible (from anywhere — mobile data, etc.)

Use **ngrok** — it creates a public HTTPS tunnel to your local Flask server. Free, no server needed.

**One-time setup:**
```bash
# Install ngrok
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Authenticate (get your token from https://dashboard.ngrok.com/get-started/your-authtoken)
ngrok config add-authtoken <your-token>
```

**Every time you want to expose the API:**

Terminal 1 — Start Flask:
```bash
source venv/bin/activate
cd smishing_detector
python -m app.flask_api
```

Terminal 2 — Start ngrok tunnel:
```bash
ngrok http 5000
```

ngrok prints a public URL like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:5000
```

In the ScamShield app → **Settings** → API URL: `https://abc123.ngrok-free.app`

That URL works from **anywhere** — WiFi, mobile data, anyone's phone.

> **Note:** The ngrok URL changes every time you restart ngrok (free tier). For a fixed URL, either pay for ngrok Pro or deploy to Oracle Cloud (see below).

### Deploy Permanently (Optional — Oracle Cloud Free Tier)

If you want it always-on without running your laptop:

1. Create a free Oracle Cloud VM (4 ARM cores, 24GB RAM — free forever)
2. Copy the project: `scp -r smishing_detector/ user@<vm-ip>:~/`
3. Install dependencies + run with `gunicorn`:
```bash
pip install gunicorn
cd smishing_detector
gunicorn -w 2 -b 0.0.0.0:5000 "app.flask_api:app"
```
4. Open port 5000 in Oracle's security group
5. Use `http://<vm-public-ip>:5000` as the API URL (fixed, permanent)

---

## 3. Mobile App (ScamShield-Mobile)

### Start Dev Server (Expo Go / QR Code)

```bash
cd ScamShield-Mobile
npx expo start
```

Scan the QR code in **Expo Go** on your Android phone.

### Start Web Preview (Browser)

```bash
cd ScamShield-Mobile
npx expo start --web --port 8081
```

**Opens at:** `http://localhost:8081`

### Connect Mobile App to API

In the app → **Settings** tab → enter API URL:
- Same WiFi network: `http://<your-laptop-ip>:5000` (get IP from `hostname -I`)
- Local browser testing: `http://localhost:5000`

---

## 3b. Build APK

### One-time Setup

```bash
# Install EAS CLI globally
npm install -g eas-cli

# Log in to your Expo account
cd ScamShield-Mobile
eas login

# Configure EAS build for this project (first time only)
eas build:configure
```

### Build Preview APK (fastest, for testing)

```bash
cd ScamShield-Mobile
eas build --platform android --profile preview
```

- Builds an unsigned `.apk` you can sideload directly on Android
- Takes ~10 min on Expo's servers
- Download link appears in terminal + [expo.dev/builds](https://expo.dev/builds)
- Install: enable "Install from unknown sources" on phone, then open the `.apk`

### Build Production APK (signed, for distribution)

```bash
cd ScamShield-Mobile
eas build --platform android --profile production
```

- Produces a signed `.aab` (Android App Bundle) for Play Store, or `.apk` if configured
- EAS handles keystore automatically on first build (saves it to your Expo account)

### Check Build Status

```bash
eas build:list --platform android --limit 5
```

### Download Latest Build

```bash
eas build:download --platform android
```

> **Note:** Before building for production, update the API URL in `src/services/api.js`
> to point to your deployed server instead of a local IP.

---

## 4. Kaggle Training (Retrain the Model)

### Setup Kaggle Credentials

Add your credentials to `.env`:

```bash
KAGGLE_USERNAME=your_username
KAGGLE_KEY=your_api_key
```

Or create `~/.kaggle/kaggle.json`:

```bash
mkdir -p ~/.kaggle
echo '{"username":"your_username","key":"your_api_key"}' > ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

Get your key from: [kaggle.com/settings → API → Create New Token](https://www.kaggle.com/settings)

### Upload to Kaggle & Train

1. Upload `KaggleTraining/` folder as a **Kaggle Dataset** (name it `scamshield-training`)
2. Create a new Kaggle Notebook with **GPU T4 x2** + **Internet ON**
3. Attach the dataset under "Add data"
4. Copy each cell from `KaggleTraining/KAGGLE_NOTEBOOK.py` into the notebook in order
5. In Cell 2, verify the dataset path matches:

```python
DATASET_PATH = "/kaggle/input/scamshield-training"
```

6. Run all cells — training takes ~60–90 min on T4
7. Download `best_model.pt` (~1.1 GB) from Kaggle Output panel
8. Replace the model checkpoint:

```bash
cp ~/Downloads/best_model.pt /home/neeraj/Projects/MAIN-EL-2/smishing_detector/best_model.pt
```

9. Restart the Flask API — it loads the new model on startup

---

## 5. Single-Message Testing (Quick CLI)

### Test a Message via Python

```bash
source venv/bin/activate
cd smishing_detector
python -c "
from predictor import SmishingPredictor
import json

p = SmishingPredictor('best_model.pt')

messages = [
    'URGENT: Your SBI account suspended. Verify http://sbi-kyc.xyz/update',
    'Dear Customer, your HDFC Bank a/c credited Rs.25,000. -HDFC Bank',
    'Airtel recharge Rs.239 successful. Validity 28 days. -Airtel',
    'Your OTP for SBI login is 483921. Valid 10 mins. Do not share.',
    'Hey! Are we still on for dinner tonight?',
]

for msg in messages:
    r = p.predict(msg)
    gsb = ' [GSB cleared]' if r.get('gsb_cleared') else ''
    print(f'{r[\"risk_level\"].upper():6} {r[\"confidence\"]:.3f}{gsb} | {msg[:65]}')
"
```

### SHAP Explanation via Python

```bash
source venv/bin/activate
cd smishing_detector
python -c "
from predictor import SmishingPredictor
from explainability.shap_explainer import SmishingExplainer

p = SmishingPredictor('best_model.pt')
e = SmishingExplainer(p)

msg = 'URGENT: Your SBI account suspended. Click http://sbi-kyc.xyz/update'
exp = e.explain_text(msg, num_features=10)

print('Spam indicators:')
for word, val in exp['top_spam_words']:
    print(f'  {word}: +{val:.4f}')

print()
print('Ham indicators:')
for word, val in exp['top_ham_words']:
    print(f'  {word}: {val:.4f}')
"
```

---

## 6. Evaluation

### Run Test Set Evaluation

```bash
source venv/bin/activate
cd smishing_detector
python evaluate.py
```

### Run Multilingual Evaluation

```bash
source venv/bin/activate
cd smishing_detector
python evaluate_multilingual.py
```

**Output:** Hindi and Hinglish breakdown — precision, recall, F1 per language.

### Inspect Checkpoint

```bash
source venv/bin/activate
cd smishing_detector
python -c "
import torch
ckpt = torch.load('best_model.pt', map_location='cpu', weights_only=False)
print('Epoch:          ', ckpt['epoch'])
print('Val F1:         ', f\"{ckpt['val_f1']:.6f}\")
print('Threshold:      ', ckpt.get('threshold', 0.5))
print('Feature mins:   ', ckpt['feature_mins'])
print('Feature ranges: ', ckpt['feature_ranges'])
"
```

### Count Model Parameters

```bash
source venv/bin/activate
cd smishing_detector
python -c "
from models.model import SmishingDetector
m = SmishingDetector(num_handcrafted=17, dropout=0.3, freeze_bert_layers=0)
total = sum(p.numel() for p in m.parameters())
trainable = sum(p.numel() for p in m.parameters() if p.requires_grad)
print(f'Total:     {total:,}')
print(f'Trainable: {trainable:,}')
print(f'Frozen:    {total - trainable:,}')
"
```

---

## 7. Build APK (Mobile)

### Install EAS CLI

```bash
npm install -g eas-cli
```

### Login to Expo

```bash
cd ScamShield-Mobile
eas login
```

### Build Preview APK

```bash
eas build --platform android --profile preview
```

Download the `.apk` from the Expo dashboard after build completes (~10 min).

### Build Production APK

```bash
eas build --platform android --profile production
```

---

## 8. Quick Reference Card

| Task | Command (from `/home/neeraj/Projects/MAIN-EL-2`) |
|---|---|
| Activate venv | `source venv/bin/activate` |
| Start Flask API | `cd smishing_detector && python -m app.flask_api` |
| Start mobile dev | `cd ScamShield-Mobile && npx expo start` |
| Mobile web preview | `cd ScamShield-Mobile && npx expo start --web --port 8081` |
| Quick predict | See §5 above |
| Evaluate model | `cd smishing_detector && python evaluate.py` |
| Multilingual eval | `cd smishing_detector && python evaluate_multilingual.py` |
| Build APK | `cd ScamShield-Mobile && eas build --platform android --profile preview` |
| Retrain on Kaggle | Upload `KaggleTraining/`, copy cells from `KAGGLE_NOTEBOOK.py`, download `best_model.pt` |

> **API keys live in `.env`** at the project root. Never commit this file to git.
