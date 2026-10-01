"""
Prediction engine for ScamShield.

The neural model remains the primary classifier. Rules are used only as:
  - spam floors: raise confidence when explicit phishing evidence is present
  - ham ceilings: lower confidence for clear legitimate transactional SMS

This avoids the old failure mode where a weak Hindi/Hinglish rule score could
average down a strong neural spam prediction.
"""

import os
import re
import sys
from typing import Dict, Iterable, List, Tuple

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.model import MAX_LEN, SmishingDetector, get_tokenizer
from utils.data_loader import (
    clean_text,
    extract_urls,
    get_feature_columns,
    text_features,
    url_features,
)


DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
TOKEN_RE = re.compile(r"[a-z]+|[\u0900-\u097F]+")

HINGLISH_MARKERS = {
    "aap", "aapka", "aapke", "apka", "mera", "meri", "tumhara", "hamara",
    "karo", "karein", "karna", "kar", "kiya", "kijiye", "dijiye",
    "hai", "hain", "tha", "thi", "hoga", "hogi", "jayega", "jayegi",
    "nahi", "nahin", "bhi", "aur", "ke", "ki", "ka", "mein", "se",
    "par", "ko", "ne", "tak", "wala", "wali", "turant", "jaldi",
    "abhi", "raat", "subah", "aaj", "kal", "rupaye", "paisa",
    "khata", "bijli", "band",
}

LEGIT_BRANDS = {
    "airtel", "jio", "bsnl", "vi", "vodafone", "idea", "amazon",
    "flipkart", "swiggy", "zomato", "zepto", "blinkit", "meesho",
    "myntra", "irctc", "uidai", "epfo", "hdfc", "icici", "sbi",
    "axis", "kotak", "paytm", "phonepe", "gpay",
}


def detect_language(text: str) -> Tuple[str, float]:
    """Return english, hinglish, or hindi with a simple confidence score."""
    if DEVANAGARI_RE.search(text):
        return "hindi", 0.95

    tokens = set(re.findall(r"[a-z]+", text.lower()))
    hits = len(tokens & HINGLISH_MARKERS)
    if hits >= 3:
        return "hinglish", min(0.55 + hits * 0.08, 0.95)
    if hits:
        return "hinglish", 0.45
    return "english", 0.90


SPAM_PATTERNS: List[Tuple[str, float]] = [
    # Account, card, identity, and service suspension
    (r"account.{0,24}(suspend|block|freez|clos|terminat|deactivat)", 0.45),
    (r"(suspend|block|freez|terminat|deactivat).{0,30}(account|card|upi|sim|pan|aadhaar)", 0.45),
    (r"(pan|aadhaar|aadhar)\s*(card\s*)?.{0,24}(block|suspend|deactivat|reactivat)", 0.45),
    (r"upi\s*(id\s*)?.{0,18}(expir|deactivat|block|suspend)", 0.42),
    (r"kyc.{0,20}(update|verify|complete|pending|expire)", 0.38),
    (r"(verify|update|confirm).{0,30}(account|payment|billing|card|kyc|details)", 0.35),
    # Delivery, fees, refunds, and prizes
    (r"(parcel|package|shipment|delivery).{0,35}(fail|held|unable|fee|customs|returned)", 0.42),
    (r"customs?\s*(fee|charge|duty|clearance|payment)", 0.40),
    (r"(tax|hmrc|irs|income\s*tax).{0,30}(refund|rebate|return|pending|claim)", 0.42),
    (r"(claim|collect|redeem).{0,30}(before|within|it\s*expires|now\s*at\s*http|at\s*http)", 0.38),
    (r"(win|won|winner|selected|chosen|lucky).{0,45}(prize|reward|gift|lottery|cash|rs\.?|inr)", 0.45),
    (r"loan.{0,35}(approved|eligible|sanction|offer).{0,40}(call|contact|whatsapp|apply)", 0.38),
    # Hinglish social engineering
    (r"bijli.{0,25}(cut|band|kataegi|kategi|nahi\s*aayegi)", 0.45),
    (r"(electricity|power|connection).{0,24}(cut|band|disconnect)", 0.42),
    (r"band\s*ho\s*(jayega|jaega|jaayega)", 0.35),
    (r"khata.{0,20}(band|block|suspend|freez)", 0.42),
    (r"(digital\s*arrest|money\s*launder|warrant|fir|giraftari|graftari)", 0.48),
    (r"(cbi|ed|police|income\s*tax).{0,35}(notice|case|action|raid|fir|arrest)", 0.42),
    # Devanagari Hindi equivalents, written as escapes to keep the file stable.
    ("\u092c\u093f\u091c\u0932\u0940.{0,24}(\u0915\u091f|\u092c\u0902\u0926)", 0.45),
    ("\u0915\u0928\u0947\u0915\u094d\u0936\u0928.{0,20}(\u0915\u091f|\u092c\u0902\u0926)", 0.42),
    ("\u0916\u093e\u0924\u093e.{0,20}(\u092c\u0902\u0926|\u092c\u094d\u0932\u0949\u0915|\u092b\u094d\u0930\u0940\u091c)", 0.42),
    ("(\u0915\u0947\u0935\u093e\u0908\u0938\u0940|kyc).{0,20}(\u0905\u092a\u0921\u0947\u091f|\u092a\u0942\u0930\u093e|\u0935\u0947\u0930\u093f\u092b)", 0.38),
    ("\u0906\u0927\u093e\u0930.{0,20}(\u092c\u094d\u0932\u0949\u0915|\u092c\u0902\u0926|\u0928\u093f\u0932\u0902\u092c\u093f\u0924)", 0.45),
    ("\u092a\u0948\u0928.{0,20}(\u092c\u094d\u0932\u0949\u0915|\u092c\u0902\u0926|\u0928\u093f\u0937\u094d\u0915\u094d\u0930\u093f\u092f)", 0.45),
    ("\u0917\u093f\u0930\u092b\u094d\u0924\u093e\u0930|\u090f\u092b\u0906\u0908\u0906\u0930|\u0935\u093e\u0930\u0902\u091f|\u0921\u093f\u091c\u093f\u091f\u0932\\s*\u0905\u0930\u0947\u0938\u094d\u091f", 0.48),
]

HAM_PATTERNS: List[Tuple[str, float]] = [
    # Banking and wallet confirmations
    (r"(rs\.?|inr|\u20b9)\s*[\d,]+\.?\d*.{0,35}(credited|debited|received|paid|sent|withdrawn)", 0.58),
    (r"(credited|debited|received|paid|sent|withdrawn).{0,35}(rs\.?|inr|\u20b9)\s*[\d,]+", 0.50),
    (r"(avl|available|current)\s*(bal|balance)", 0.45),
    (r"upi\s*(ref|reference)", 0.35),
    (r"(do\s*not|never)\s*(share|give).{0,25}(otp|pin|code|password)", 0.55),
    (r"(otp|one[\s-]?time|verification\s*code).{0,60}(valid|expires|login|transaction|payment)", 0.45),
    # Recharge, travel, delivery, bills
    (r"recharge.{0,45}(successful|done|activated|renewed)", 0.55),
    (r"(order|parcel|shipment|package).{0,55}(shipped|dispatched|delivered|out\s*for\s*delivery)", 0.50),
    (r"(estimated|expected)\s*(delivery|arrival)", 0.30),
    (r"(ticket|booking|pnr).{0,55}(confirmed|booked|reserved)", 0.50),
    (r"(bill|premium|policy).{0,60}(due|generated|paid|receipt)", 0.35),
    # Telecom — legit promos, upgrades, store visits
    (r"visit.{0,20}(nearest|our).{0,20}(store|branch|centre|outlet)", 0.35),
    (r"eligible\s*(for)?\s*(a\s*)?(free\s*)?(sim|upgrade|service|plan|offer)", 0.30),
    (r"(sim|5g|4g|network|plan)\s*(upgrade|migrat|activat)", 0.30),
    # Hindi/Hinglish legitimate messages
    ("\u0913\u091f\u0940\u092a\u0940|otp", 0.20),
    ("\u0938\u093e\u091d\u093e|\u0936\u0947\u092f\u0930", 0.15),
    ("(rs\\.?|inr|\u20b9)\\s*[\\d,]+.{0,35}(\u091c\u092e\u093e|\u0921\u0947\u092c\u093f\u091f|\u092d\u0941\u0917\u0924\u093e\u0928|\u092a\u094d\u0930\u093e\u092a\u094d\u0924)", 0.45),
    ("\u092c\u093f\u0932.{0,45}(\u091c\u0947\u0928\u0930\u0947\u091f|\u0926\u0947\u092f|\u092d\u0941\u0917\u0924\u093e\u0928)", 0.35),
]

URGENCY_TOKENS = {
    "urgent", "immediately", "now", "today", "limited", "last", "final",
    "turant", "jaldi", "abhi", "aaj", "kal", "antim",
    "\u0924\u0941\u0930\u0902\u0924", "\u091c\u0932\u094d\u0926\u0940",
    "\u0905\u092d\u0940", "\u0906\u091c", "\u0915\u0932",
}

PHONE_RE = re.compile(r"(?:\+91[-\s]?)?\d[\d\s\-]{8,}\d")
DEADLINE_RE = re.compile(
    r"aaj\s*raat|kal\s*subah|\d{1,2}:\d{2}\s*(am|pm|baje)|"
    r"\d+\s*(ghante|minute|mint)\s*(mein|tak|ke\s*andar)|"
    r"\u0906\u091c\s*\u0930\u093e\u0924|\u0915\u0932\s*\u0938\u0941\u092c\u0939|"
    r"\u092c\u091c\u0947\s*\u0924\u0915|\d+\s*(\u0918\u0902\u091f\u0947|\u092e\u093f\u0928\u091f)\s*(\u092e\u0947\u0902|\u0924\u0915)",
    re.IGNORECASE,
)


def _tokens(text: str) -> set:
    return set(TOKEN_RE.findall(text.lower()))


def _sum_patterns(text: str, patterns: Iterable[Tuple[str, float]]) -> float:
    msg = text.lower()
    score = 0.0
    for pattern, weight in patterns:
        if re.search(pattern, msg, re.IGNORECASE):
            score += weight
    return min(score, 1.0)


def spam_rule_score(message: str, uf: Dict[str, int]) -> float:
    """Explicit phishing/scam confidence from transparent rules."""
    score = _sum_patterns(message, SPAM_PATTERNS)
    tokens = _tokens(message)

    if tokens & URGENCY_TOKENS and PHONE_RE.search(message):
        score += 0.25
    if DEADLINE_RE.search(message):
        score += 0.15
    if uf.get("has_url"):
        score += 0.15  # any URL + spam pattern match is a signal
        if uf.get("suspicious_tld") or uf.get("has_ip_url") or uf.get("has_shortened_url"):
            score += 0.25
        if re.search(r"https?://\S*(verify|login|update|confirm|secure|kyc|account)\S*", message, re.IGNORECASE):
            score += 0.20

    return min(score, 1.0)


def ham_rule_score(message: str, uf: Dict[str, int]) -> float:
    """Legitimate transactional confidence from transparent rules."""
    score = _sum_patterns(message, HAM_PATTERNS)
    tokens = _tokens(message)

    if tokens & LEGIT_BRANDS:
        score += 0.18
    if uf.get("has_url") and uf.get("has_legit_domain"):
        score += 0.20
    if uf.get("has_url") and (uf.get("suspicious_tld") or uf.get("has_ip_url") or uf.get("has_shortened_url")):
        score -= 0.35

    return max(0.0, min(score, 1.0))


def combine_scores(neural: float, spam_rule: float, ham_rule: float, has_url: bool, has_legit_domain: bool) -> float:
    """
    Combine neural and rule scores.

    Rules never average down spam evidence. They only set floors/ceilings.
    """
    final = float(neural)

    if spam_rule >= 0.35:
        final = max(final, spam_rule)

    clear_legit = ham_rule >= 0.35 and spam_rule < 0.55
    if clear_legit:
        if not has_url:
            cap = 1.0 - ham_rule * 0.82
        elif has_legit_domain:
            cap = 1.0 - ham_rule * 0.58
        else:
            cap = 1.0 - ham_rule * 0.25
        final = min(final, cap)

    return max(0.0, min(1.0, final))


class SmishingPredictor:
    def __init__(self, checkpoint_path: str = "best_model.pt"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = get_tokenizer()

        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        self.model = SmishingDetector(
            num_handcrafted=17,
            dropout=0.3,
            freeze_bert_layers=0,
        ).to(self.device)
        self.model.load_state_dict(checkpoint["model_state"])
        self.model.eval()

        self.threshold = float(checkpoint.get("threshold", 0.55))
        self.feature_mins = np.array(checkpoint.get("feature_mins", [0.0] * 17), dtype=np.float32)
        self.feature_ranges = np.array(checkpoint.get("feature_ranges", [1.0] * 17), dtype=np.float32)
        self.feature_ranges = np.where(self.feature_ranges == 0, 1.0, self.feature_ranges)

        print(
            "SmishingPredictor loaded | "
            f"threshold={self.threshold} | "
            f"val_f1={checkpoint.get('val_f1', 'N/A')} | "
            f"epoch={checkpoint.get('epoch', 'N/A')}"
        )

    def _handcrafted_features(self, message: str) -> Tuple[Dict[str, int], Dict[str, float], torch.Tensor]:
        uf = url_features(message)
        tf = text_features(message)
        merged = {**uf, **tf}
        raw = np.array([merged[col] for col in get_feature_columns()], dtype=np.float32)
        norm = (raw - self.feature_mins) / self.feature_ranges
        norm = np.nan_to_num(norm, nan=0.0, posinf=3.0, neginf=-2.0)
        norm = np.clip(norm, -2.0, 3.0)
        tensor = torch.from_numpy(norm.reshape(1, -1)).to(self.device)
        return uf, tf, tensor

    def _neural_score(self, message: str, hand_features: torch.Tensor) -> float:
        cleaned = clean_text(message)
        enc = self.tokenizer(
            cleaned,
            max_length=MAX_LEN,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        enc = {k: v.to(self.device) for k, v in enc.items()}

        with torch.no_grad():
            prob = self.model.predict_proba(enc["input_ids"], enc["attention_mask"], hand_features)
        return float(prob.item())

    def _green_channel(self, message: str, label: str, final_prob: float,
                        spam_rule: float, ham_rule: float,
                        uf: dict) -> Tuple[str, str, float, bool, str]:
        """
        Green Channel — distinguishes SCAMS from harmless promotional spam.

        This project detects smishing (scam SMS), NOT general spam.
        A message like "Congratulations! Free 5G SIM upgrade. Visit your nearest
        Airtel store" is promotional spam, not a scam — it has no phishing URL,
        no threats, no urgency to click a link.

        Logic:
        1. Hard scam signals (spam_rule >= 0.55) → NEVER clear. These have
           explicit phishing patterns like "account suspended", "KYC update",
           "digital arrest" with suspicious URLs.
        2. Soft spam (spam_rule < 0.55) + ALL URLs are verified legit domains
           → GREEN CHANNEL → downgrade to "safe" (it's just an ad/promo).
        3. Soft spam + NO URLs at all + ham patterns detected → also GREEN
           CHANNEL (legit transactional or brand notification).

        Returns: (label, risk, final_prob, green_cleared, green_reason)
        """
        # Never green-channel if hard scam patterns are present
        if spam_rule >= 0.55:
            risk = "high" if final_prob >= 0.75 else "medium" if final_prob >= self.threshold else "low"
            return label, risk, final_prob, False, ""

        # Only applies to messages that would otherwise be classified as spam
        if label != "spam":
            risk = "low"
            return label, risk, final_prob, False, ""

        # Build unified legit domain set (safe_browsing + data_loader)
        legit_domains = set()
        try:
            from utils.safe_browsing import get_checker
            legit_domains |= get_checker().fallback_legit_domains
        except Exception:
            pass
        try:
            from utils.data_loader import LEGIT_DOMAINS
            legit_domains |= LEGIT_DOMAINS
        except Exception:
            pass

        has_url = bool(uf.get("has_url"))
        has_suspicious = bool(uf.get("suspicious_tld") or uf.get("has_ip_url"))

        # Case 1: Message has URLs — check if ALL are legit
        if has_url and not has_suspicious:
            try:
                import tldextract
                urls = extract_urls(message)
                if urls:
                    all_legit = True
                    for url in urls:
                        ext = tldextract.extract(url)
                        full_domain = f"{ext.domain}.{ext.suffix}".lower().strip(".")
                        if full_domain not in legit_domains:
                            all_legit = False
                            break
                    if all_legit:
                        return "safe", "low", min(final_prob, 0.40), True, \
                            "all URLs verified as legitimate domains"
            except Exception:
                pass

        # Case 2: No URL + ham patterns present + low spam rule score
        # e.g. "Airtel: Congratulations! Eligible for free 5G upgrade. Visit store."
        if not has_url and ham_rule >= 0.35 and spam_rule < 0.35:
            return "safe", "low", min(final_prob, 0.35), True, \
                "no URLs + legitimate transactional patterns detected"

        # Case 3: Has legit domain URL + ham patterns dominate spam patterns
        if has_url and uf.get("has_legit_domain") and ham_rule > spam_rule:
            return "safe", "low", min(final_prob, 0.42), True, \
                "legit domain URL + stronger ham signals than scam signals"

        risk = "high" if final_prob >= 0.75 else "medium" if final_prob >= self.threshold else "low"
        return label, risk, final_prob, False, ""

    def predict(self, message: str) -> dict:
        lang, lang_conf = detect_language(message)
        uf, tf, hand_features = self._handcrafted_features(message)

        neural_prob = self._neural_score(message, hand_features)
        spam_s = spam_rule_score(message, uf)
        ham_s = ham_rule_score(message, uf)
        final_prob = combine_scores(
            neural_prob,
            spam_s,
            ham_s,
            bool(uf.get("has_url")),
            bool(uf.get("has_legit_domain")),
        )

        label = "spam" if final_prob >= self.threshold else "ham"
        risk = "high" if final_prob >= 0.75 else "medium" if final_prob >= self.threshold else "low"

        # Green channel: distinguish scams from harmless promo spam
        label, risk, final_prob, green_cleared, green_reason = self._green_channel(
            message, label, final_prob, spam_s, ham_s, uf
        )

        return {
            "label": label,
            "confidence": round(final_prob, 4),
            "risk_level": risk,
            "language": lang,
            "language_confidence": round(lang_conf, 2),
            "green_channel": green_cleared,
            "green_reason": green_reason,
            "url_signals": uf,
            "text_signals": tf,
            "_neural_score": round(neural_prob, 4),
            "_rule_score": round(spam_s, 4),
            "_ham_rule_score": round(ham_s, 4),
            "_threshold": self.threshold,
        }

