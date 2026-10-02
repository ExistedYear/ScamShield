import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "smishing_detector"))

import json
import gradio as gr
from predictor import SmishingPredictor
from explainability.shap_explainer import SmishingExplainer

CHECKPOINT = os.path.join(os.path.dirname(__file__), "smishing_detector", "best_model.pt")

print("Loading ScamShield model...")
predictor = SmishingPredictor(CHECKPOINT)
print("Loading SHAP explainer...")
explainer = SmishingExplainer(predictor)
print("Model loaded. Ready.")

def analyze(message):
    if not message or not message.strip():
        return "⚠️ Please enter a message.", None, None

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

with gr.Blocks(title="ScamShield — Smishing Detector") as demo:
    gr.Markdown("# 🛡️ ScamShield — Multilingual Smishing Detector")
    gr.Markdown("Detect SMS phishing (smishing) in English, Hindi, and Hinglish. "
                "Powered by XLM-RoBERTa + hand-crafted URL/text features + Google Safe Browsing.")

    with gr.Row():
        with gr.Column(scale=2):
            inp = gr.Textbox(label="SMS Message", placeholder="Paste the SMS message here...",
                             lines=4, max_lines=10)
            btn = gr.Button("🔍 Analyze", variant="primary", size="lg")

        with gr.Column(scale=3):
            verdict = gr.Markdown(label="Verdict")
            with gr.Tabs():
                with gr.TabItem("URL Analysis"):
                    url_box = gr.Markdown()
                with gr.TabItem("Text Signals"):
                    text_box = gr.Markdown()
                with gr.TabItem("SHAP Explainability"):
                    shap_box = gr.Markdown()

    btn.click(fn=analyze, inputs=inp, outputs=[verdict, url_box, text_box, shap_box])
    inp.submit(fn=analyze, inputs=inp, outputs=[verdict, url_box, text_box, shap_box])

    gr.Examples(examples=examples, inputs=inp, label="Try these examples")

    gr.Markdown("---\n"
                "**Model:** XLM-RoBERTa (xlm-roberta-base) | **Threshold:** 0.55 | "
                "**Languages:** English · Hindi · Hinglish | "
                "**Features:** 9 URL signals + 8 text signals | **F1:** 0.98")


def api_predict(message: str) -> str:
    return json.dumps(predictor.predict(message), ensure_ascii=False)


api = gr.Interface(
    fn=api_predict,
    inputs=gr.Textbox(label="message"),
    outputs=gr.Textbox(label="result"),
    api_name="predict",
    title="ScamShield API",
)


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1)
    gr.mount_gradio_app(demo, api, path="/api")
    demo.launch()
