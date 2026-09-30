"""
Dataset and feature engine for ScamShield.

Feature extraction is deterministic and side-effect free. In particular, it does
not call Google Safe Browsing or any network service. Training, evaluation, and
inference all import the same functions from this module.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd
import tldextract
from sklearn.model_selection import train_test_split


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

SUSPICIOUS_TLDS = {
    "tk", "ml", "ga", "cf", "gq", "xyz", "top", "click", "link",
    "work", "loan", "online", "site", "info", "biz", "club",
}

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd",
    "buff.ly", "rebrand.ly", "cutt.ly", "fkrt.it", "amzn.in",
}

LEGIT_DOMAINS = {
    "amazon.com", "amazon.in", "netflix.com", "spotify.com", "apple.com",
    "google.com", "microsoft.com", "paypal.com", "ebay.com", "walmart.com",
    "fedex.com", "ups.com", "usps.com", "shopify.com", "slack.com",
    "zoom.us", "gmail.com", "outlook.com", "yahoo.com",
    "flipkart.com", "myntra.com", "swiggy.com", "zomato.com",
    "makemytrip.com", "yatra.com", "cleartrip.com", "paytm.com",
    "phonepe.com", "hdfcbank.com", "onlinesbi.sbi", "icicibank.com",
    "axisbank.com", "kotak.com", "airindia.in", "goindigo.in",
    "irctc.co.in", "redbus.in", "olacabs.com", "hotstar.com",
    "sonyliv.com", "zee5.com", "jiocinema.com", "moneycontrol.com",
    "bseindia.com", "nseindia.com", "bookmyshow.com", "policybazaar.com",
    "nykaa.com", "ajio.com", "firstcry.com", "bigbasket.com",
    "blinkit.com", "zepto.com", "upstox.com", "groww.in", "zerodha.com",
    "airtel.in", "jio.com", "myvi.in", "vi.com", "bsnl.co.in",
    "tataplay.com", "dishtv.in", "sbicard.com", "bajajfinserv.in",
    "cred.club", "licindia.in", "epfindia.gov.in", "mseb.co.in",
    "bescom.org", "uidai.gov.in", "cibil.com",
}

TRUSTED_TLDS = {
    "com", "org", "net", "edu", "gov", "gov.in", "co.uk", "au",
    "ca", "de", "fr", "in", "co.in", "sbi",
}

URL_FEATURE_COLS = [
    "has_url", "num_urls", "has_http", "has_https", "suspicious_tld",
    "max_url_len", "has_ip_url", "has_shortened_url", "has_legit_domain",
]

TEXT_FEATURE_COLS = [
    "num_chars", "num_words", "pct_upper", "pct_digits", "num_special",
    "urgency_count", "has_phone", "has_currency",
]

URGENCY_WORDS = {
    "urgent", "winner", "won", "free", "prize", "claim", "cash",
    "congratulations", "selected", "reward", "limited", "click",
    "password", "invoice", "crypto", "bitcoin", "wallet", "suspended",
    "blocked", "deactivated", "illegal", "arrested", "cyber", "fraud",
    "hack", "jaldi", "turant", "abhi", "kijiye", "rupaye", "paisa",
    "khata", "band", "inam", "jeeta", "loot", "kyc", "cashback",
    "lucky", "gift", "redeem", "bijli", "officer", "helpline",
    "fir", "giraftari", "arrest",
}

URGENCY_PHRASES = {
    "act now", "action required", "share your otp", "last chance",
    "court notice", "turant call", "abhi call", "aaj raat",
    "kal subah", "power cut", "connection cut", "band ho jayega",
}

CURRENCY_SYMBOLS = {"$", "\u00a3", "\u20ac", "\u20b9", "btc", "eth", "usdt"}

INDIAN_LEGIT_SMS = [
    "HDFC Bank: Rs.25,000 credited to a/c XX4521 on 02-May. Avl bal: Rs.1,42,356. -HDFC Bank",
    "Dear Customer, your ICICI a/c ending 7890 debited Rs.1,500 at AMAZON on 01-May. -ICICI Bank",
    "Your SBI a/c XXXX1234 is credited with INR 5,000.00 on 01-May-25. Bal: INR 12,450.00. -SBI",
    "Your OTP for SBI Net Banking login is 483921. Valid for 10 minutes. Do not share. -SBI",
    "PhonePe OTP: 273948 for payment of Rs.150 to Zomato. Do not share. -PhonePe",
    "Aadhaar OTP: 581234 for e-KYC verification. Valid 30 minutes. -UIDAI",
    "Airtel Thanks! Your recharge of Rs.239 is successful. Validity: 28 days. Data: 1.5GB/day. -Airtel",
    "Jio: Your recharge of Rs.299 is done. Validity 28 days, 2GB/day data. Enjoy! -Jio",
    "Your electricity bill of Rs.1,234 for account 98765 is due on 10-May. Pay via BESCOM app.",
    "Bijli Bill: Aapka MSEB bijli bill Rs.1,847 generate ho gaya hai. Due date: 10-Jun-26. Pay at mseb.co.in",
    "Your Amazon order #402-9876543 is out for delivery today. Track: amzn.in/track -Amazon",
    "Flipkart: Your order for boAt Earphones has been shipped. Tracking: fkrt.it/xyz -Flipkart",
    "Zomato: Your order from Dominos has been picked up. ETA: 25 mins. -Zomato",
    "Your IRCTC ticket PNR 4567891230 is confirmed. Train 12345 on 05-May. Seat: S4/32. -IRCTC",
    "IndiGo: Your flight 6E-456 on 05-May is confirmed. PNR: ABCDEF. Web check-in open. -IndiGo",
    "LIC: Your premium of Rs.5,000 for policy 123456789 is due on 10-May. Pay at licindia.in.",
    "EPFO: Your PF balance as of 01-May-25 is Rs.2,45,678. Check on epfindia.gov.in. -EPFO",
    "You received Rs.500 from Priya via UPI. UPI Ref: 123456789012. -Google Pay",
    "PhonePe: Rs.1,200 sent to Ajay Kumar successfully. UPI Ref: 987654321. -PhonePe",
    "Paytm: Rs.250 added to your wallet from HDFC Bank XX1234. Wallet Bal: Rs.430. -Paytm",
]

URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.IGNORECASE)
BARE_DOMAIN_RE = re.compile(
    r"\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|edu|gov|gov\.in|co\.uk|co\.in|in|io|co|sbi|club|xyz|top|click|link|online|site|info|biz)\b",
    re.IGNORECASE,
)
PHONE_RE = re.compile(r"(?:\+91[-\s]?)?\d[\d\s-]{8,}\d")
TOKEN_RE = re.compile(r"[a-z]+|[\u0900-\u097F]+")


def get_feature_columns() -> list[str]:
    return URL_FEATURE_COLS + TEXT_FEATURE_COLS


def clean_text(text: str, remove_urls: bool = False) -> str:
    text = "" if text is None else str(text)
    if remove_urls:
        text = URL_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_urls(text: str) -> list[str]:
    text = "" if text is None else str(text)
    urls = URL_RE.findall(text)
    urls.extend(BARE_DOMAIN_RE.findall(text))
    cleaned = []
    for url in urls:
        cleaned.append(url.strip(".,;:!?)\"]}'").lower())
    return sorted(set(u for u in cleaned if u))


def _registered_domain(url: str) -> tuple[str, str]:
    ext = tldextract.extract(url)
    domain = ext.domain.lower()
    suffix = ext.suffix.lower()
    full_domain = f"{domain}.{suffix}".strip(".")
    return full_domain, suffix


def url_features(text: str) -> dict:
    urls = extract_urls(text)

    suspicious_tld = 0
    has_ip_url = 0
    has_shortened_url = 0
    has_legit_domain = 0
    max_url_len = 0

    for url in urls:
        max_url_len = max(max_url_len, len(url))
        full_domain, suffix = _registered_domain(url)

        if suffix in SUSPICIOUS_TLDS:
            suspicious_tld = 1
        if full_domain in URL_SHORTENERS:
            has_shortened_url = 1
        if full_domain in LEGIT_DOMAINS or suffix in TRUSTED_TLDS:
            has_legit_domain = 1
        if re.search(r"https?://\d{1,3}(?:\.\d{1,3}){3}", url, re.IGNORECASE):
            has_ip_url = 1

    return {
        "has_url": int(bool(urls)),
        "num_urls": len(urls),
        "has_http": int(any(u.startswith("http://") for u in urls)),
        "has_https": int(any(u.startswith("https://") for u in urls)),
        "suspicious_tld": suspicious_tld,
        "max_url_len": max_url_len,
        "has_ip_url": has_ip_url,
        "has_shortened_url": has_shortened_url,
        "has_legit_domain": has_legit_domain,
    }


def text_features(text: str) -> dict:
    text = "" if text is None else str(text)
    lowered = text.lower()
    tokens = TOKEN_RE.findall(lowered)

    num_chars = len(text)
    upper_count = sum(1 for c in text if c.isupper())
    digit_count = sum(1 for c in text if c.isdigit())
    special_count = sum(1 for c in text if c in "!@#$%^&*()_+-=[]{}|;:,.<>?")
    urgency_count = sum(1 for token in tokens if token in URGENCY_WORDS)
    urgency_count += sum(1 for phrase in URGENCY_PHRASES if phrase in lowered)

    return {
        "num_chars": num_chars,
        "num_words": len(tokens),
        "pct_upper": upper_count / num_chars if num_chars else 0.0,
        "pct_digits": digit_count / num_chars if num_chars else 0.0,
        "num_special": special_count,
        "urgency_count": urgency_count,
        "has_phone": int(bool(PHONE_RE.search(text))),
        "has_currency": int(any(symbol in lowered for symbol in CURRENCY_SYMBOLS)),
    }


def _standardize_label(value) -> Optional[int]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip().lower()
    mapping = {
        "spam": 1, "scam": 1, "phishing": 1, "smishing": 1, "1": 1, "true": 1,
        "ham": 0, "safe": 0, "legit": 0, "legitimate": 0, "not_spam": 0,
        "0": 0, "false": 0,
    }
    return mapping.get(text)


def _standardize_frame(df: pd.DataFrame, message_cols: Iterable[str], label_cols: Iterable[str]) -> pd.DataFrame:
    lower_map = {c.lower().strip(): c for c in df.columns}
    msg_col = next((lower_map[c] for c in message_cols if c in lower_map), None)
    lbl_col = next((lower_map[c] for c in label_cols if c in lower_map), None)

    if msg_col is None or lbl_col is None:
        return pd.DataFrame(columns=["message", "label"])

    result = pd.DataFrame({
        "message": df[msg_col].astype(str),
        "label": df[lbl_col].apply(_standardize_label),
    })
    result = result.dropna(subset=["message", "label"])
    result["label"] = result["label"].astype(int)
    result = result[result["message"].str.strip() != ""]
    return result[["message", "label"]].reset_index(drop=True)


def _load_local_spam_csv() -> pd.DataFrame:
    path = DATA_DIR / "spam.csv"
    if not path.exists():
        return pd.DataFrame(columns=["message", "label"])
    try:
        df = pd.read_csv(path, encoding="latin-1")
        result = _standardize_frame(df, ["v2", "message", "text", "sms"], ["v1", "label", "labels", "category"])
        print(f"  Local UCI spam.csv: {len(result)} messages loaded")
        return result
    except Exception as exc:
        print(f"  Warning: failed to load local spam.csv: {exc}")
        return pd.DataFrame(columns=["message", "label"])


def _load_local_parquet() -> pd.DataFrame:
    frames = []
    for path in sorted(DATA_DIR.glob("*.parquet")):
        try:
            raw = pd.read_parquet(path)
            result = _standardize_frame(raw, ["message", "text", "sms", "email"], ["label", "labels", "category", "class"])
            if len(result):
                print(f"  Local {path.name}: {len(result)} messages loaded")
                frames.append(result)
        except Exception as exc:
            print(f"  Warning: failed to load {path.name}: {exc}")
    if not frames:
        return pd.DataFrame(columns=["message", "label"])
    return pd.concat(frames, ignore_index=True)


def _load_synthetic_indian_legit() -> pd.DataFrame:
    print(f"  Synthetic Indian legit SMS: {len(INDIAN_LEGIT_SMS)} messages loaded")
    return pd.DataFrame({"message": INDIAN_LEGIT_SMS, "label": 0})


def _load_huggingface_dataset(name: str) -> pd.DataFrame:
    try:
        from datasets import load_dataset as hf_load

        ds = hf_load(name)
        frames = []
        for split_name in ds.keys():
            raw = ds[split_name].to_pandas()
            frames.append(_standardize_frame(raw, ["message", "text", "sms", "email"], ["label", "labels", "category", "class"]))
        result = pd.concat(frames, ignore_index=True)
        print(f"  HuggingFace {name}: {len(result)} messages loaded")
        return result
    except Exception as exc:
        print(f"  Warning: failed to load HuggingFace {name}: {exc}")
        return pd.DataFrame(columns=["message", "label"])


def _load_multilingual_hf(name: str) -> pd.DataFrame:
    try:
        from datasets import load_dataset as hf_load

        ds = hf_load(name)
        raw = pd.concat([ds[s].to_pandas() for s in ds.keys()], ignore_index=True)
        lower_map = {c.lower().strip(): c for c in raw.columns}
        label_col = next((lower_map[c] for c in ["label", "labels", "v1", "category", "class"] if c in lower_map), None)
        if label_col is None:
            return pd.DataFrame(columns=["message", "label"])

        message_cols = []
        for col in raw.columns:
            lower = col.lower().strip()
            if lower in {"text", "message", "sms", "v2", "text_en", "en", "text_hi", "hi", "hindi"} or lower.endswith("_hi"):
                message_cols.append(col)

        frames = []
        for col in message_cols:
            frame = pd.DataFrame({"message": raw[col].astype(str), "label": raw[label_col].apply(_standardize_label)})
            frame = frame.dropna(subset=["message", "label"])
            frame["label"] = frame["label"].astype(int)
            frame = frame[frame["message"].str.strip() != ""]
            frames.append(frame[["message", "label"]])

        result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["message", "label"])
        print(f"  Multilingual {name}: {len(result)} messages loaded")
        return result
    except Exception as exc:
        print(f"  Warning: failed to load multilingual {name}: {exc}")
        return pd.DataFrame(columns=["message", "label"])


def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_norm"] = df["message"].astype(str).str.lower().str.strip().str.replace(r"\s+", " ", regex=True)
    df = df.drop_duplicates(subset="_norm", keep="first").drop(columns=["_norm"])
    return df.reset_index(drop=True)


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    url_rows = []
    text_rows = []
    cleaned = []

    for message in df["message"]:
        message = str(message)
        url_rows.append(url_features(message))
        text_rows.append(text_features(message))
        cleaned.append(clean_text(message))

    result = pd.concat(
        [df.reset_index(drop=True), pd.DataFrame(url_rows), pd.DataFrame(text_rows)],
        axis=1,
    )
    result["message"] = cleaned
    return result


def load_dataset(use_remote: Optional[bool] = None) -> pd.DataFrame:
    """
    Load SMS datasets and return message, label, and feature columns.

    Remote loaders are enabled by default. Set SCAMSHIELD_USE_REMOTE_DATA=0 or
    pass use_remote=False to train only on local files plus synthetic examples.
    """
    if use_remote is None:
        use_remote = os.getenv("SCAMSHIELD_USE_REMOTE_DATA", "1").lower() not in {"0", "false", "no"}

    print("Loading datasets...")
    frames = [
        _load_local_spam_csv(),
        _load_local_parquet(),
        _load_synthetic_indian_legit(),
    ]

    if use_remote:
        frames.extend([
            _load_huggingface_dataset("Deysi/spam-detection-dataset"),
            _load_huggingface_dataset("Ngadou/Spam_SMS"),
            _load_multilingual_hf("dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset"),
        ])

    frames = [frame for frame in frames if len(frame) > 0]
    if not frames:
        raise RuntimeError("No datasets loaded. Check local data files or enable remote datasets.")

    df = pd.concat(frames, ignore_index=True)
    before = len(df)
    df = _deduplicate(df)
    if before != len(df):
        print(f"  Removed {before - len(df)} duplicate messages")

    df = _add_features(df)
    spam_count = int(df["label"].sum())
    ham_count = len(df) - spam_count
    print(f"\nDataset loaded: {len(df)} messages ({spam_count} spam, {ham_count} ham)")
    return df


def split_dataset(df: pd.DataFrame, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_df, temp_df = train_test_split(
        df,
        test_size=0.30,
        stratify=df["label"],
        random_state=seed,
    )
    val_df, test_df = train_test_split(
        temp_df,
        test_size=0.50,
        stratify=temp_df["label"],
        random_state=seed,
    )
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True), test_df.reset_index(drop=True)
