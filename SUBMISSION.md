# 🛡️ ScamShield — Multilingual Smishing Detection

> **Catch the scam before it catches you.**
> AI smishing defense for English, Hindi, and Hinglish — with word-level evidence for every verdict.

🔗 **Live demo:** https://scam-shield-flame-delta.vercel.app
🤖 **API + full demo:** https://existedyear-scamshield.hf.space
📱 **Android APK:** https://github.com/ExistedYear/ScamShield/raw/main/APKs/app-release.apk
💻 **Code:** https://github.com/ExistedYear/ScamShield

| Metric | Score |
|:---|:---|
| 🎯 Test accuracy | **97.54%** |
| 📊 Spam F1 | **0.94** |
| 🛡️ False-positive rate | **0.46%** |
| 🇮🇳 Hindi F1 | **0.9845** |
| 🥷 Adversarial F1 drop | **≤ 0.01** |

---

## 💡 Inspiration

SMS phishing — *smishing* — is the scam most people meet first and defend against worst.
A single text impersonating a bank, a courier, or a government agency can drain an
account in minutes, and the messages are getting harder to tell apart from legitimate
ones: **Indian bank credits, OTPs, and recharge alerts look like spam by every naive
heuristic.** English-only filters miss the Hindi and Hinglish lures entirely.

We wanted a detector that reads what attackers *actually* write — and that can
**prove its verdicts instead of asking for blind trust**.

---

## ⚙️ What it does

ScamShield takes any SMS in **English, Hindi, or Hinglish** and returns a calibrated
verdict — safe, low, medium, or high risk — with the exact signals behind it:

- 🔗 **Nine URL features** — suspicious TLDs, shorteners, raw IP hosts, domain whitelist
- 📝 **Eight text features** — urgency, phone numbers, caps, digits
- 🛡️ **Google Safe Browsing** reputation with a live API key
- 📊 **Word-level SHAP attribution** showing which tokens pushed the score each way

It ships three ways: an **interactive web demo**, a **JSON API** for automated
evaluation, and an **Android app** with real-time inbox monitoring, background threat
notifications, and an AES-256-CBC encrypted channel to the backend.

---

## 🔨 How we built it

The core is **XLM-RoBERTa-base**, fine-tuned on **~30,000 messages from six sources**
(UCI, Hugging Face and Kaggle corpora, plus hand-crafted Indian transactional SMS to fix
the distribution gap), fused late with 17 hand-crafted features. The 768-d CLS
embedding and the 64-d projected feature vector are concatenated into a single
832-d vector, passed through a 832 → 256 → 64 → 1 classifier head, and flagged
as spam whenever the sigmoid output is ≥ 0.55:

    P(spam | message) = sigmoid(W · [CLS_768 ; features_64])
    verdict = SPAM  iff  P ≥ 0.55   (else HAM)

The **0.55 decision threshold** was chosen specifically to stop flagging legitimate
bank SMS. Training ran on Kaggle T4s with label smoothing and early stopping
(best val F1 **0.9765**).

Inference serves from a Hugging Face Space with a Gradio UI and JSON endpoints; the
static landing site and the React Native client are thin front ends over that same API.
SHAP runs on demand behind the verdict, so the answer lands in **~1.5s** while
attribution streams in after.

---

## 🧗 Challenges we ran into

**1. Everything Indian looked like phishing.**
The model initially flagged nearly every transactional SMS as an attack. We fixed it
by adding synthetic legitimate examples and retuning the urgency and currency features.

**2. Free-tier GPU quota died after a handful of scans.**
ZeroGPU gives 5 min/day, and each call re-transfers 1.1 GB of weights onto the GPU.
We moved serving to **CPU (~1.5s per prediction, unmetered)** with GPU as an opt-in
flag — the demo literally cannot die on quota anymore.

**3. ZeroGPU refuses to boot with zero decorated functions.**
So a never-called probe function satisfies the runtime check while every real request
stays on CPU. One of those bugs you only find at 2 AM.

---

## 🏆 Accomplishments that we're proud of

- ✨ **97.54% test accuracy** with a **0.46%** false-positive rate
- ✨ Hindi F1 of **0.9845** — the hard language, not the easy one
- ✨ Three risk tiers consistent across web UI, seeded mobile inbox, *and* native app
- ✨ An API automated evaluators can drive with two curl calls
- ✨ A demo architecture that **degrades gracefully instead of dying** when the GPU runs out

---

## 📚 What we learned

> **Accuracy is the easy part; calibration is the product.**

The difference between "spam" and *"medium risk, here is why"* is what makes a
detector usable. Free infrastructure shapes architecture more than any textbook —
quota mechanics dictated our CPU serving, caching, and streaming design. And
explainability isn't garnish: when a model flags your bank SMS, *"here are the three
words responsible"* is the only response that keeps trust.

---

## 🚀 What's next for ScamShield

- 📴 **On-device inference** via ONNX/TFLite — no message ever leaves the phone
- 🔗 **Redirect-chain analysis** — follow short links to their landing pages
- 🕰️ **WHOIS domain-age** as a first-class signal for fresh phishing domains
- 🌏 **Tamil, Telugu, and Bengali** coverage
- 🔐 **Federated learning** — the model keeps improving without centralizing anyone's SMS
