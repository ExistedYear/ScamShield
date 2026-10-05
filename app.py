import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "smishing_detector"))

import gradio as gr
from predictor import SmishingPredictor
from explainability.shap_explainer import SmishingExplainer

CHECKPOINT = os.path.join(os.path.dirname(__file__), "smishing_detector", "best_model.pt")

print("Loading ScamShield model...")
predictor = SmishingPredictor(CHECKPOINT)
print("Loading SHAP explainer...")
explainer = SmishingExplainer(predictor)
print("Model loaded. Ready.")

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
.gradio-container { font-family: 'Plus Jakarta Sans', sans-serif !important; max-width: 920px !important; margin: 0 auto !important; }
.ss-hero { text-align: center; padding: 2rem 0 1.2rem; }
.ss-hero h1 { font-size: 2.3rem; font-weight: 800; letter-spacing: -0.5px; margin: 0; }
.ss-hero h1 span { color: #3b82f6; }
.ss-hero p { opacity: 0.65; font-size: 0.92rem; margin-top: 0.4rem; }
.ss-badge { display: inline-flex; align-items: center; gap: 0.35rem; background: rgba(59,130,246,.12);
  border: 1px solid rgba(59,130,246,.35); color: #3b82f6; font-size: 0.72rem; font-weight: 700;
  padding: 0.25rem 0.7rem; border-radius: 20px; margin-bottom: 0.8rem; }
.phone-frame { max-width: 392px !important; margin: 0 auto !important; border: 10px solid #0b0e13;
  border-radius: 34px; padding: 1rem 0.9rem 1.3rem !important; box-shadow: 0 14px 44px rgba(0,0,0,.35); }
.phone-notch { width: 120px; height: 22px; background: #0b0e13; border-radius: 0 0 12px 12px; margin: -1rem auto 0.7rem; }
.phone-title { text-align: center; font-weight: 800; font-size: 1rem; margin-bottom: 0.2rem; }
.phone-sub { text-align: center; font-size: 0.72rem; opacity: 0.6; margin-bottom: 0.8rem; }
.ss-footer { text-align: center; font-size: 0.75rem; opacity: 0.6; margin-top: 1.6rem; line-height: 1.7; }
"""


def analyze(message):
    if not message or not message.strip():
        return "⚠️ Please enter a message.", None, None, None

    result = predictor.predict(message)

    label = result["label"]
    risk = result["risk_level"]
    conf = result["confidence"]
    lang = result.get("language", "?")
    gc = result.get("green_channel", False)
    gc_reason = result.get("green_reason", "")

    # --- Verdict ---
    if label == "safe":
        verdict = f"## ✅ Safe\nGreen Channel cleared: {gc_reason}"
    elif label == "spam":
        emoji = "🔴" if risk == "high" else "🟠"
        verdict = f"## {emoji} {label.upper()} — {risk.upper()} RISK"
    else:
        verdict = f"## 🟢 {label.upper()} — LOW RISK"

    verdict += f"\nConfidence: **{conf:.1%}** | Threshold: {predictor.threshold} | Language: {lang}"

    if gc:
        verdict += f"\n\n🛡️ Green Channel: {gc_reason}"

    # --- URL signals ---
    urls = result.get("url_signals", {})
    url_text = ""
    if urls.get("has_url"):
        url_text = "### 🔗 URL Analysis\n"
        flags = []
        if urls.get("has_ip_url"):      flags.append("🔴 IP address instead of domain")
        if urls.get("has_shortened_url"): flags.append("🔴 URL shortener — hides real destination")
        if urls.get("suspicious_tld"):  flags.append("🟠 Suspicious TLD (.xyz, .tk, .top etc.)")
        if urls.get("has_http") and not urls.get("has_https"):
            flags.append("🟠 HTTP (not encrypted)")
        if urls.get("has_legit_domain"): flags.append("🟢 Legitimate domain detected")
        url_text += "\n".join(f"- {f}" for f in flags) if flags else "- No obvious threats"
        url_text += f"\nLinks found: {urls.get('num_urls', 0)}"

    # --- Text signals ---
    text = result.get("text_signals", {})
    text_info = "### 📝 Text Signals\n"
    text_info += f"- Chars: {text.get('num_chars', 0)} | Words: {text.get('num_words', 0)}\n"
    text_info += f"- Uppercase: {text.get('pct_upper', 0)*100:.0f}% | Digits: {text.get('pct_digits', 0)*100:.0f}%\n"
    text_info += f"- Urgency keywords: {text.get('urgency_count', 0)}\n"
    text_info += f"- Phone number: {'Yes' if text.get('has_phone') else 'No'} | Currency symbol: {'Yes' if text.get('has_currency') else 'No'}"

    # --- Internal scores ---
    scores = "### ⚙️ Scores\n"
    scores += f"Neural: {result.get('_neural_score', 0):.3f} | Rule: {result.get('_rule_score', 0):.3f} | Ham: {result.get('_ham_rule_score', 0):.3f}"

    # --- SHAP explanation ---
    shap_text = "### 🔬 SHAP Explainability\n"
    try:
        explanation = explainer.explain_text(message, num_features=8)
        if explanation["top_spam_words"]:
            shap_text += "*Spam indicators:*\n"
            for word, val in explanation["top_spam_words"]:
                shap_text += f"- `{word}` +{val:.3f}\n"
        if explanation["top_ham_words"]:
            shap_text += "*Ham indicators:*\n"
            for word, val in explanation["top_ham_words"]:
                shap_text += f"- `{word}` {val:.3f}\n"
        if not explanation["top_spam_words"] and not explanation["top_ham_words"]:
            shap_text += "No strong word-level signals found."
    except Exception:
        shap_text += "SHAP explanation unavailable for this message."

    return verdict, url_text if url_text else "No URLs found", text_info + "\n\n" + scores, shap_text


examples = [
    "URGENT: Your SBI account has been suspended. Verify KYC now at http://sbi-kyc-verify.xyz or funds frozen.",
    "HDFC Bank: Rs.25,000 credited to a/c XX4521. Avl bal: Rs.1,42,356. -HDFC Bank",
    "Aapka bijli connection aaj raat 9:30 baje band ho jayega. Turant call karein: 9876543210",
    "Airtel: Your recharge of Rs.239 is successful. Validity 28 days. -Airtel",
    "CBI notice: Aapke khilaf money laundering case darj. Digital arrest warrant. Call 9911000000.",
    "PhonePe: Rs.500 received from Rahul Kumar. UPI Ref: 4893721019.",
    "बधाई हो! आपको KBC लॉटरी में ₹25,00,000 का इनाम मिला। http://kbc-lottery.ml/win",
    "Your OTP for SBI login is 483921. Valid 10 mins. Do NOT share. -SBI",
    "Dear user, your UPI ID expires in 24h. Renew at http://upi-renew.club/verify",
    "Mom, I landed safely. Will call from the hotel in an hour.",
]

seed_labels = ["Seed 1 · EN spam (KYC)", "Seed 2 · EN ham (bank)", "Seed 3 · Hinglish spam (bijli)",
               "Seed 4 · EN ham (recharge)", "Seed 5 · Hinglish spam (CBI)", "Seed 6 · EN ham (UPI)",
               "Seed 7 · Hindi spam (lottery)", "Seed 8 · EN ham (OTP)", "Seed 9 · EN spam (UPI)",
               "Seed 10 · EN ham (personal)"]


def _pick_seed(choice):
    try:
        idx = seed_labels.index(choice)
    except ValueError:
        idx = 0
    return examples[idx]


with gr.Blocks(title="ScamShield — Smishing Detector", css=CSS,
               theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate")) as demo:
    gr.HTML("""<div class="ss-hero">
        <div class="ss-badge">🛡️ AI · Cybersecurity — Smishing Detection</div>
        <h1>Detect <span>Scams</span> Before They Strike</h1>
        <p>XLM-RoBERTa + URL fusion + SHAP · English · Hindi · Hinglish · Threshold 0.55</p>
    </div>""")

    with gr.Tabs():
        with gr.TabItem("Desktop"):
            with gr.Row():
                with gr.Column(scale=2):
                    inp = gr.Textbox(label="SMS Message", placeholder="Paste the SMS message here...",
                                     lines=4, max_lines=10)
                    btn = gr.Button("🔍 Analyze", variant="primary", size="lg")
                    gr.Examples(examples=examples, inputs=inp, label="Try these examples")

                with gr.Column(scale=3):
                    verdict = gr.Markdown(label="Verdict")
                    with gr.Tabs():
                        with gr.TabItem("URL Analysis"):
                            url_box = gr.Markdown()
                        with gr.TabItem("Text Signals"):
                            text_box = gr.Markdown()
                        with gr.TabItem("SHAP Explainability"):
                            shap_box = gr.Markdown()

            btn.click(fn=analyze, inputs=inp,
                      outputs=[verdict, url_box, text_box, shap_box], api_name="predict")
            inp.submit(fn=analyze, inputs=inp,
                       outputs=[verdict, url_box, text_box, shap_box])

        with gr.TabItem("Mobile"):
            gr.Markdown("Phone-style scanner — same live model. Full app adds the 100-message seeded inbox + Scan All; "
                        "pick a seed below or paste any SMS.")
            with gr.Column(elem_classes="phone-frame"):
                gr.HTML('<div class="phone-notch"></div><div class="phone-title">🛡️ ScamShield</div>'
                        '<div class="phone-sub">Seeded inbox preview · live analysis</div>')
                seed = gr.Dropdown(choices=seed_labels, value=seed_labels[0], label="Seeded message")
                minp = gr.Textbox(label="SMS Message", lines=3, max_lines=6)
                mbtn = gr.Button("🔍 Scan", variant="primary")
                mverdict = gr.Markdown(label="Verdict")
                with gr.Tabs():
                    with gr.TabItem("URLs"):
                        murl = gr.Markdown()
                    with gr.TabItem("Signals"):
                        mtext = gr.Markdown()
                    with gr.TabItem("SHAP"):
                        mshap = gr.Markdown()

            seed.change(fn=_pick_seed, inputs=seed, outputs=minp, api_name=False)
            mbtn.click(fn=analyze, inputs=minp,
                       outputs=[mverdict, murl, mtext, mshap], api_name="predict_mobile")

    gr.HTML("""<div class="ss-footer">
        <b>Model:</b> XLM-RoBERTa (xlm-roberta-base) · <b>Threshold:</b> 0.55 ·
        <b>Languages:</b> English · Hindi · Hinglish · <b>Features:</b> 9 URL + 8 text signals · <b>Spam F1:</b> 0.94<br/>
        Full Android app (.apk) via EAS build — same API underneath.
    </div>""")


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1)
    demo.launch()
