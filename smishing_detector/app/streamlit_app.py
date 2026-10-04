import os
import sys
import streamlit as st
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor import SmishingPredictor
from explainability.shap_explainer import SmishingExplainer

CHECKPOINT_PATH = "best_model.pt"

st.set_page_config(page_title="Smishing Detector", page_icon="🔍")

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-top: 0;
    }
    .footer {
        font-size: 0.8rem;
        color: #888;
        text-align: center;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_predictor():
    if not os.path.exists(CHECKPOINT_PATH):
        return None
    return SmishingPredictor(CHECKPOINT_PATH)


def load_explainer(_predictor):
    if _predictor is None:
        return None
    return SmishingExplainer(_predictor)


predictor = load_predictor()
explainer = load_explainer(predictor) if predictor else None

st.markdown('<p class="main-header">🔍 Smishing Detector</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Powered by XLM-RoBERTa + URL Feature Fusion · English, Hindi &amp; Hinglish Support</p>', unsafe_allow_html=True)

if predictor is None:
    st.warning(f"Model checkpoint not found. Please run `python train.py` first to train the model.")
    st.stop()

spam_sample = "URGENT: Your SBI account is SUSPENDED. Verify now at http://bit.ly/sbi-verify or lose access."
ham_sample = "Hey! Are we still on for dinner tonight at 7? Let me know if plans change."

col1, col2 = st.columns([2, 1])

with col1:
    def update_sample():
        sample = st.session_state.sample_selector
        if sample == "Spam Sample":
            st.session_state.message_input = spam_sample
        elif sample == "Ham Sample":
            st.session_state.message_input = ham_sample

    message_input = st.text_area("Enter SMS message to analyse:", key="message_input", height=150)
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        analyse_btn = st.button("Analyse", type="primary", use_container_width=True)
    with btn_col2:
        st.selectbox("Load sample:", ["", "Spam Sample", "Ham Sample"], index=0, key="sample_selector", on_change=update_sample)

with col2:
    st.write("**Sample Messages:**")
    st.code(spam_sample[:60] + "...")
    st.code(ham_sample[:60] + "...")

if analyse_btn and message_input:
    result = predictor.predict(message_input)

    st.divider()

    if result['label'] == 'spam':
        st.markdown("## 🚨 SPAM DETECTED")
    else:
        st.markdown("## ✅ HAM (Legitimate)")

    m1, m2, m3 = st.columns(3)
    m1.metric("Prediction", result['label'].upper())
    m2.metric("Confidence", f"{result['confidence']*100:.1f}%")
    m3.metric("Risk Level", result['risk_level'].upper())

    # Language detection display
    from utils.multilingual_loader import detect_language

    detected_lang = detect_language(message_input)
    lang_display = {
        'english':  '🇬🇧 English',
        'hindi':    '🇮🇳 Hindi (हिंदी)',
        'hinglish': '🇮🇳 Hinglish'
    }

    st.info(f"**Detected Language:** {lang_display.get(detected_lang, '🌐 Unknown')}")

    fig, ax = plt.subplots(figsize=(8, 2))
    prob = result['confidence']
    ax.barh(['Message'], [prob], color='#d62728' if result['label'] == 'spam' else '#2ca02c')
    ax.barh(['Message'], [1-prob], left=[prob], color='#2ca02c' if result['label'] == 'spam' else '#d62728')
    ax.axvline(x=0.5, color='black', linestyle='--', linewidth=1, label='Threshold')
    ax.set_xlim(0, 1)
    ax.set_yticks([])
    ax.set_xlabel('Probability')
    st.pyplot(fig)

    url_cols, text_cols = st.columns(2)

    with url_cols:
        st.write("**URL Risk Signals:**")
        url_signals = result['url_signals']
        for key, value in url_signals.items():
            flag = " ⚠️" if value and key in ['has_url', 'suspicious_tld', 'has_ip_url', 'has_shortened_url', 'has_http'] else ""
            st.write(f"`{key}`: **{value}**{flag}")

    with text_cols:
        st.write("**Text Risk Signals:**")
        text_signals = result['text_signals']
        for key, value in text_signals.items():
            st.write(f"`{key}`: **{value}**")

    if explainer:
        try:
            shap_fig = explainer.plot_explanation(message_input)
            st.pyplot(shap_fig)
        except Exception as e:
            st.caption(f"SHAP explanation unavailable: {str(e)}")

    with st.expander("View Raw Analysis"):
        st.json(result)

st.markdown('<p class="footer">ScamShield · Model: XLM-RoBERTa + URL Feature Fusion</p>', unsafe_allow_html=True)