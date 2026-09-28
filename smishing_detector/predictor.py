"""
predictor.py — Multilingual SmishingPredictor
Language-aware ensemble: XLM-RoBERTa neural score + Hinglish/Hindi rule-based score.

For English: trust neural model fully.
For Hinglish/Hindi: blend neural (55%) + rule-based (45%) because training data
for organic Hinglish was sparse, so rules compensate for weak neural signal.
"""

import torch
import numpy as np
import os, sys, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.data_loader import url_features, text_features, clean_text, get_feature_columns
from models.model import SmishingDetector, get_tokenizer, MAX_LEN


# ── Language detection ────────────────────────────────────────────────────────

_DEVANAGARI = re.compile(r'[\u0900-\u097F]')
_HINGLISH_MARKERS = {
    'aapka', 'aapke', 'aap', 'mera', 'meri', 'tumhara', 'hamara',
    'karo', 'karein', 'karna', 'kar', 'kiya', 'kijiye',
    'hai', 'hain', 'tha', 'thi', 'hoga', 'hogi', 'jayega', 'jayegi',
    'nahi', 'nahin', 'bhi', 'aur', 'ke', 'ki', 'ka',
    'mein', 'se', 'par', 'ko', 'ne', 'tak', 'wala', 'wali',
    'turant', 'jaldi', 'abhi', 'raat', 'subah', 'aaj', 'kal',
    'rupaye', 'paisa', 'lakh', 'hazaar', 'crore',
}


def detect_language(text: str) -> tuple:
    """Returns (language, confidence) — 'english', 'hindi', or 'hinglish'."""
    if _DEVANAGARI.search(text):
        return 'hindi', 0.95
    words = set(text.lower().split())
    hits = len(words & _HINGLISH_MARKERS)
    if hits >= 3:
        return 'hinglish', min(0.5 + hits * 0.1, 0.95)
    if hits >= 1:
        return 'hinglish', 0.4
    return 'english', 0.9


# ── Hinglish / Hindi rule-based scam scorer ───────────────────────────────────

_THREAT_PATTERNS = [
    # Service disconnection threats
    r'connect[io]+n\s*(cut|band)',
    r'bijli\s*(cut|band|kataegi|kategi|nahi\s*aayegi)',
    r'power\s*(cut|band)',
    r'band\s*ho\s*(jayega|jaega|jaayega)',
    r'cut\s*kar\s*(diya|denge|diya\s*jayega)',
    r'electric\w*\s*(cut|band|disconnect)',
    # Legal / government threats
    r'giraftari|graftari',
    r'court\s*noti(ce|s)',
    r'fir\s*(darj|darz|file)',
    r'cyber\s*crime',
    r'income\s*tax',
    r'aadhaar\s*(block|band|suspend)',
    r'sim\s*(block|band|deactivat)',
    # Banking / financial fraud
    r'account\s*(block|band|freez|suspend)',
    r'khata\s*(band|suspend|block|freez)',
    r'kyc\s*(update|kijiye|verify|complete)',
    r'pension\s*(rok|band|cancel)',
    r'bank.*suspend|suspend.*bank',
    r'upi\s*(block|band|suspend)',
    r'debit\s*card\s*(block|band|suspend)',
]

_AUTHORITY_WORDS = {
    'officer', 'department', 'ministry', 'police', 'court',
    'trai', 'cbi', 'enforcement', 'inspector', 'collector',
    'helpline', 'nodal', 'superintendent',
    # Banks / financial authority
    'sbi', 'hdfc', 'icici', 'axis', 'kotak', 'pnb', 'rbi',
    'bank', 'ifsc', 'nbfc',
}

_HINGLISH_URGENCY = {
    'turant', 'jaldi', 'abhi', 'aaj', 'kal', 'antim', 'last',
}

_PHONE_RE = re.compile(r'(?:\+91[-\s]?)?\d[\d\s\-]{8,}\d')
_DEADLINE_RE = re.compile(
    r'aaj\s*raat|kal\s*subah|pm\s*tak|am\s*tak|\d{1,2}:\d{2}\s*(am|pm|baje)',
    re.IGNORECASE
)


def hinglish_rule_score(message: str) -> float:
    """
    Returns 0–1 spam score using pattern matching for Hinglish/Hindi
    social engineering scams. Focuses on:
    - Service disconnection threats (electricity, SIM, account)
    - Authority impersonation (officer, police, court)
    - Urgency + phone number combo
    - Hard deadlines ("aaj raat 9:30 PM tak")
    """
    msg = message.lower()
    words = set(msg.split())
    score = 0.0

    # Threat pattern match — each hit adds significant weight
    threat_hits = sum(1 for p in _THREAT_PATTERNS if re.search(p, msg))
    score += min(threat_hits * 0.28, 0.55)

    # Urgency + phone number together = classic social engineering combo
    has_urgency = bool(words & _HINGLISH_URGENCY)
    has_phone = bool(_PHONE_RE.search(message))
    if has_urgency and has_phone:
        score += 0.35

    # Authority impersonation
    auth_hits = len(words & _AUTHORITY_WORDS)
    score += min(auth_hits * 0.12, 0.22)

    # Hard deadline ("aaj raat 9:30 PM tak")
    if _DEADLINE_RE.search(message):
        score += 0.20

    # Suspicious URL + financial action = very strong signal
    # e.g. "KYC kijiye: http://sbi-kyc.xyz" or "verify: http://bank-update.tk"
    has_url = bool(re.search(r'https?://\S+', message))
    kyc_or_verify = bool(re.search(r'kyc|verify|update|confirm', msg))
    if has_url and kyc_or_verify:
        score += 0.25

    return min(score, 1.0)


# ── Predictor ─────────────────────────────────────────────────────────────────

class SmishingPredictor:
    def __init__(self, checkpoint_path: str = "best_model.pt"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = get_tokenizer()

        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)

        # Must match training config: freeze_bert_layers=0, dropout=0.3
        self.model = SmishingDetector(
            num_handcrafted=17, dropout=0.3, freeze_bert_layers=0
        ).to(self.device)
        self.model.load_state_dict(checkpoint['model_state'])
        self.model.eval()

        # Use threshold saved during training
        self.threshold = checkpoint.get('threshold', 0.55)

        if 'feature_mins' in checkpoint and 'feature_ranges' in checkpoint:
            self.feature_mins = np.array(checkpoint['feature_mins'], dtype=np.float32)
            self.feature_ranges = np.array(checkpoint['feature_ranges'], dtype=np.float32)
        else:
            self.feature_mins = np.zeros(17, dtype=np.float32)
            self.feature_ranges = np.ones(17, dtype=np.float32)
            print("Warning: no normalization stats in checkpoint.")

        print(f"SmishingPredictor loaded | threshold={self.threshold} | "
              f"val_f1={checkpoint.get('val_f1', 'N/A')} | "
              f"epoch={checkpoint.get('epoch', 'N/A')}")

    def _neural_score(self, message: str) -> float:
        """Raw XLM-RoBERTa probability."""
        cleaned = clean_text(message)
        enc = self.tokenizer(
            cleaned, max_length=MAX_LEN,
            padding='max_length', truncation=True, return_tensors='pt'
        )
        enc = {k: v.to(self.device) for k, v in enc.items()}

        uf = url_features(message)
        tf = text_features(message)
        cols = get_feature_columns()
        raw = np.array([{**uf, **tf}[c] for c in cols], dtype=np.float32)
        norm = (raw - self.feature_mins) / self.feature_ranges
        hf = torch.from_numpy(norm.reshape(1, -1)).to(self.device)

        with torch.no_grad():
            return self.model.predict_proba(enc['input_ids'], enc['attention_mask'], hf).item()

    def predict(self, message: str) -> dict:
        lang, lang_conf = detect_language(message)
        uf = url_features(message)
        tf = text_features(message)

        neural_prob = self._neural_score(message)

        # ── Language-aware ensemble ────────────────────────────────────────────
        if lang in ('hinglish', 'hindi'):
            rule_prob = hinglish_rule_score(message)
            # Dynamic rule weight: higher weight when rule is very confident
            # (compensates for sparse Hinglish training data)
            base_weight = 0.35 + 0.10 * lang_conf          # 0.35–0.45
            if rule_prob >= 0.7:
                rule_weight = min(base_weight + 0.25, 0.70) # boost to 0.60–0.70
            else:
                rule_weight = base_weight
            final_prob = (1 - rule_weight) * neural_prob + rule_weight * rule_prob
        else:
            rule_prob = 0.0
            final_prob = neural_prob

        label = "spam" if final_prob >= self.threshold else "ham"
        risk  = "high" if final_prob >= 0.75 else "medium" if final_prob >= self.threshold else "low"

        # ── Google Safe Browsing override ─────────────────────────────────────
        # IMPORTANT: Only downgrade to ham if the domain is in a KNOWN-SAFE
        # whitelist. Do NOT trust "GSB returned no threats" as proof of safety —
        # new phishing domains won't be in GSB's database yet.
        gsb_cleared = False
        if uf['has_url'] and uf['num_urls'] > 0 and label == 'spam':
            try:
                from utils.safe_browsing import get_checker
                from utils.data_loader import extract_urls
                import tldextract
                checker = get_checker()
                urls = extract_urls(message)
                if urls:
                    all_whitelisted = all(
                        f"{tldextract.extract(u).domain}.{tldextract.extract(u).suffix}"
                        in checker.fallback_legit_domains
                        for u in urls
                    )
                    if all_whitelisted:
                        label      = "ham"
                        risk       = "low"
                        final_prob = min(final_prob, 0.45)
                        gsb_cleared = True
            except Exception:
                pass

        return {
            "label":        label,
            "confidence":   round(final_prob, 4),
            "risk_level":   risk,
            "language":     lang,
            "gsb_cleared":  gsb_cleared,
            "url_signals":  uf,
            "text_signals": tf,
            # Breakdown — useful for debugging / UI display
            "_neural_score": round(neural_prob, 4),
            "_rule_score":   round(rule_prob, 4),
            "_rule_weight":  round(0.35 + 0.10 * lang_conf if lang != 'english' else 0.0, 2),
        }