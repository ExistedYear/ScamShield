import re
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import tldextract

# ── Constants ────────────────────────────────────────────────────────────────

SUSPICIOUS_TLDS = {
    'tk', 'ml', 'ga', 'cf', 'gq', 'xyz', 'top', 'click', 'link',
    'work', 'loan', 'online', 'site', 'info', 'biz'
}
URL_SHORTENERS = {
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly',
    'is.gd', 'buff.ly', 'rebrand.ly', 'cutt.ly'
}

# FIXED: removed 'account', 'verify', 'otp' — too common in legit Indian SMS
URGENCY_WORDS = {
    'urgent', 'winner', 'won', 'free', 'prize', 'claim', 'cash',
    'congratulations', 'selected', 'reward', 'limited', 'act now',
    'click', 'password', 'invoice', 'crypto', 'bitcoin',
    'wallet', 'action required', 'suspended', 'blocked', 'deactivated',
    'illegal', 'arrested', 'cyber', 'fraud', 'hack', 'share your otp',
    'do not share', 'never share',
    # Hinglish / Roman-script Hindi urgency markers
    'jaldi', 'turant', 'abhi', 'kijiye', 'rupaye', 'paisa',
    'khata', 'band', 'inam', 'jeeta', 'loot',
    'kyc', 'recharge', 'cashback', 'lucky', 'gift', 'redeem',
    # Hinglish threat/social-engineering phrases
    'katega', 'kataega', 'kataegi', 'kategi', 'cut kar',
    'bijli', 'bijli cut', 'power cut', 'connection cut',
    'band ho jayega', 'band kar', 'band ho',
    'officer', 'helpline', 'turant call', 'abhi call',
    'aaj raat', 'kal subah', 'last chance', 'antim',
    'court notice', 'fir', 'giraftari', 'arrest',
}

# FIXED: removed 'rs', 'rupee' — fires on every Indian transactional SMS
CURRENCY_SYMBOLS = {'$', '£', '€', '₹', 'btc', 'eth', 'usdt'}

LEGIT_DOMAINS = {
    'amazon.com', 'amazon.in', 'netflix.com', 'apple.com', 'google.com',
    'microsoft.com', 'paypal.com', 'flipkart.com', 'myntra.com',
    'swiggy.com', 'zomato.com', 'paytm.com', 'phonepe.com',
    'hdfcbank.com', 'onlinesbi.sbi', 'icicibank.com', 'axisbank.com',
    'kotak.com', 'airindia.in', 'goindigo.in', 'irctc.co.in',
    'airtel.in', 'jio.com', 'bsnl.co.in', 'sbicard.com',
    'bajajfinserv.in', 'cred.club', 'groww.in', 'zerodha.com',
    'upstox.com', 'bookmyshow.com', 'makemytrip.com', 'redbus.in',
    'naukri.com', 'gmail.com', 'outlook.com', 'yahoo.com',
    'zoom.us', 'slack.com', 'shopify.com',
}
TRUSTED_TLDS = {'com', 'org', 'net', 'edu', 'gov', 'co.uk', 'au', 'ca', 'in', 'co.in'}

URL_FEATURE_COLS = [
    'has_url', 'num_urls', 'has_http', 'has_https', 'suspicious_tld',
    'max_url_len', 'has_ip_url', 'has_shortened_url', 'has_legit_domain'
]
TEXT_FEATURE_COLS = [
    'num_chars', 'num_words', 'pct_upper', 'pct_digits', 'num_special',
    'urgency_count', 'has_phone', 'has_currency'
]


# ── Synthetic Indian legitimate SMS examples ──────────────────────────────────

INDIAN_LEGIT_SMS = [
    # Bank credit/debit
    "Your SBI a/c XXXX1234 is credited with INR 5,000.00 on 01-May-25. Bal: INR 12,450.00. -SBI",
    "HDFC Bank: Rs.25,000 credited to a/c XX4521 on 02-May. Avl bal: Rs.1,42,356. -HDFC Bank",
    "Dear Customer, your ICICI a/c ending 7890 debited Rs.1,500 at AMAZON on 01-May. -ICICI Bank",
    "Kotak: INR 3,200 debited from your a/c XX9012 via UPI on 02-May-25. -Kotak Mahindra Bank",
    "Axis Bank Alert: Rs.500 debited from a/c XX6789 at SWIGGY on 01-May. Avl Bal: Rs.8,230. -Axis",
    "Your a/c XX2345 is credited with Rs.15,000 (NEFT). Txn ID: AXISXXXXXX. -Axis Bank",
    "PNB: Rs.2,000 withdrawn from ATM. Avl Bal: Rs.6,780. If not done by you call 1800-180-2222.",
    "Canara Bank: Your a/c XX3456 credited Rs.50,000 on 03-May. Bal: Rs.75,430. -Canara Bank",
    "BOI Alert: Rs.800 debited for electricity bill payment from a/c XX5678. -Bank of India",
    "Your HDFC Credit Card XX4321 has been used for Rs.2,399 at FLIPKART. -HDFC Bank",
    # OTP messages
    "Your OTP for SBI Net Banking login is 483921. Valid for 10 minutes. Do not share. -SBI",
    "HDFC Bank OTP: 726354 for UPI transaction of Rs.500 to Rahul Kumar. Valid 5 mins. -HDFC",
    "Your Paytm OTP is 318274. Use this to complete your transaction. Valid for 10 mins.",
    "Your Amazon OTP is 924716. Use it to verify your login. Do not share with anyone.",
    "851637 is your IRCTC OTP for booking. Valid for 10 minutes. -IRCTC",
    "PhonePe OTP: 273948 for payment of Rs.150 to Zomato. Do not share. -PhonePe",
    "Your GPay verification code is 639201. Expires in 5 minutes.",
    "437826 is your Flipkart login OTP. Valid for 10 minutes. Do not share.",
    "Aadhaar OTP: 581234 for e-KYC verification. Valid 30 minutes. -UIDAI",
    "Your Jio OTP is 762839 for recharge transaction. Valid for 5 minutes. -Jio",
    # Recharge / telecom
    "Airtel Thanks! Your recharge of Rs.239 is successful. Validity: 28 days. Data: 1.5GB/day. -Airtel",
    "Jio: Your recharge of Rs.299 is done. Validity 28 days, 2GB/day data. Enjoy! -Jio",
    "Vi: Recharge of Rs.209 successful. You get 1GB/day + unlimited calls for 28 days. -Vi",
    "BSNL: Rs.187 recharge done. Validity: 28 days. Balance: Rs.2. SMS: 100/day. -BSNL",
    "Your Airtel postpaid bill of Rs.499 is paid. Thank you. -Airtel",
    # Delivery / ecommerce
    "Your Amazon order #402-9876543 is out for delivery today. Track: amzn.in/track -Amazon",
    "Flipkart: Your order for 'boAt Earphones' has been shipped. Tracking: fkrt.it/xyz -Flipkart",
    "Your Swiggy order is on the way! Delivery partner Raju is 2 mins away. -Swiggy",
    "Zomato: Your order from Dominos has been picked up. ETA: 25 mins. -Zomato",
    "Meesho: Your order has been delivered. Rate your experience in the app. -Meesho",
    "DTDC: Your parcel AWB 123456789 is out for delivery today. -DTDC Courier",
    "BlueDart: Shipment 987654321 delivered on 02-May at 3:45 PM. -BlueDart",
    "Delhivery: Your order from Myntra is arriving today between 10AM-12PM. -Delhivery",
    # Travel / booking
    "Your IRCTC ticket PNR 4567891230 is confirmed. Train 12345 on 05-May. Seat: S4/32. -IRCTC",
    "IndiGo: Your flight 6E-456 on 05-May is confirmed. PNR: ABCDEF. Web check-in open. -IndiGo",
    "MakeMyTrip: Hotel booking confirmed. Check-in 05-May. Booking ID: HTL123456. -MMT",
    "redBus: Your bus ticket is booked. Bus departs 05-May 10:00 PM from KSTDC. -redBus",
    "Ola: Your ride has been booked. Driver Ramesh (KA05AB1234) is on the way. -Ola",
    # Insurance / finance
    "LIC: Your premium of Rs.5,000 for policy 123456789 is due on 10-May. Pay at licindia.in.",
    "PolicyBazaar: Your health insurance renewal is due. Policy ID: PB123456. -PolicyBazaar",
    "CRED: Rs.2,500 CRED coins added to your account. Use them on your next bill payment. -CRED",
    "Groww: Your SIP of Rs.1,000 in Axis Bluechip Fund processed on 01-May. -Groww",
    "Zerodha: Contract note for 01-May trades sent to your registered email. -Zerodha",
    # Government / utility
    "Your electricity bill of Rs.1,234 for account 98765 is due on 10-May. Pay via BESCOM app.",
    "BBMP: Property tax receipt for PID 12345 of Rs.8,500 generated. -BBMP Bangalore",
    "DigiLocker: Your document Driving Licence has been shared with RTO. -DigiLocker",
    "Income Tax: Your ITR for AY 2024-25 has been processed. Refund of Rs.5,000 initiated. -ITD",
    "EPFO: Your PF balance as of 01-May-25 is Rs.2,45,678. Check on epfindia.gov.in. -EPFO",
    # Hospital / appointment
    "Apollo: Appointment confirmed for Dr. Sharma on 05-May at 10:30 AM. Token: 15. -Apollo Hospitals",
    "Your Practo appointment with Dr. Rao on 06-May at 11:00 AM is confirmed. -Practo",
    # Salary / HR
    "Your salary of Rs.45,000 has been credited to your account. -HR Team",
    "Dear Employee, your March 2025 salary slip is available on the HR portal. -Payroll Dept",
    # UPI / wallet
    "You received Rs.500 from Priya via UPI. UPI Ref: 123456789012. -Google Pay",
    "PhonePe: Rs.1,200 sent to Ajay Kumar successfully. UPI Ref: 987654321. -PhonePe",
    "Paytm: Rs.250 added to your wallet from HDFC Bank XX1234. Wallet Bal: Rs.430. -Paytm",
    # Misc legitimate
    "Your CIBIL score is 780. Check your full report at cibil.com. -TransUnion CIBIL",
    "Nykaa: Your order #NYK987654 has been shipped. Expected delivery: 04-May. -Nykaa",
    "BigBasket: Your grocery order is out for delivery. Delivery partner is on the way. -BigBasket",
    "Blinkit: Your order will arrive in 12 minutes! -Blinkit",
]


# ── Dataset loaders ───────────────────────────────────────────────────────────

def _load_uci() -> pd.DataFrame:
    """UCI SMS Spam Collection — gold standard."""
    try:
        import kagglehub
        path = kagglehub.dataset_download("uciml/sms-spam-collection-dataset")
        df = pd.read_csv(f"{path}/spam.csv", encoding='latin-1')[['v1', 'v2']]
        df.columns = ['label_str', 'message']
        df['label'] = df['label_str'].map({'ham': 0, 'spam': 1})
        df = df[['message', 'label']].dropna()
        print(f"  UCI SMS Spam: {len(df)} rows")
        return df
    except Exception as e:
        print(f"  UCI failed: {e}")
        return pd.DataFrame(columns=['message', 'label'])


def _load_deysi() -> pd.DataFrame:
    """Deysi/spam-detection-dataset from HuggingFace (~10.9k, no auth)."""
    try:
        from datasets import load_dataset as hf_load
        ds = hf_load("Deysi/spam-detection-dataset")
        dfs = [ds[s].to_pandas() for s in ds.keys()]
        df = pd.concat(dfs, ignore_index=True)
        if 'text' in df.columns:
            df = df.rename(columns={'text': 'message'})
        label_map = {'spam': 1, 'not_spam': 0, 'ham': 0, 1: 1, 0: 0, '1': 1, '0': 0}
        df['label'] = df['label'].map(label_map)
        df = df[['message', 'label']].dropna()
        df['label'] = df['label'].astype(int)
        print(f"  Deysi spam-detection: {len(df)} rows")
        return df
    except Exception as e:
        print(f"  Deysi failed: {e}")
        return pd.DataFrame(columns=['message', 'label'])


def _load_gaurav() -> pd.DataFrame:
    """gauravduttakiit/sms-spam from Kaggle — includes Indian SMS context."""
    try:
        import kagglehub
        import os
        path = kagglehub.dataset_download("gauravduttakiit/sms-spam")
        csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
        if not csv_files:
            return pd.DataFrame(columns=['message', 'label'])
        df = pd.read_csv(f"{path}/{csv_files[0]}", encoding='latin-1')
        col = {c.lower(): c for c in df.columns}
        # Handle different column naming conventions
        if 'v1' in col and 'v2' in col:
            df = df[[col['v1'], col['v2']]].copy()
            df.columns = ['label_str', 'message']
            df['label'] = df['label_str'].map({'ham': 0, 'spam': 1})
        elif 'label' in col and 'message' in col:
            df = df[[col['label'], col['message']]].copy()
            df.columns = ['label', 'message']
            if df['label'].dtype == object:
                df['label'] = df['label'].map({'ham': 0, 'spam': 1})
        else:
            return pd.DataFrame(columns=['message', 'label'])
        df = df[['message', 'label']].dropna()
        df['label'] = df['label'].astype(int)
        df = df[df['label'].isin([0, 1])]
        print(f"  gauravduttakiit/sms-spam: {len(df)} rows")
        return df
    except Exception as e:
        print(f"  Gaurav SMS spam failed: {e}")
        return pd.DataFrame(columns=['message', 'label'])


def _synthetic_indian_legit() -> pd.DataFrame:
    """Synthetic genuine Indian transactional SMS to fix distribution bias."""
    df = pd.DataFrame({'message': INDIAN_LEGIT_SMS, 'label': 0})
    print(f"  Synthetic Indian legit SMS: {len(df)} rows")
    return df


def _load_dbarbedillo_multilingual() -> pd.DataFrame:
    """
    dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset (HuggingFace).
    Columns in this dataset: labels, text, text_hi, text_de, text_fr
    We load only text (English) and text_hi (Hindi).
    """
    try:
        from datasets import load_dataset as hf_load
        ds = hf_load("dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset")
        dfs_raw = [ds[s].to_pandas() for s in ds.keys()]
        df = pd.concat(dfs_raw, ignore_index=True)

        # Label column is 'labels' in this dataset (not 'label' or 'v1')
        label_col = next((c for c in ['v1', 'label', 'labels'] if c in df.columns), None)
        if label_col is None:
            print(f"  dbarbedillo: no label column found. Got: {df.columns.tolist()}")
            return pd.DataFrame(columns=['message', 'label'])

        label_map = {'ham': 0, 'spam': 1, 0: 0, 1: 1, '0': 0, '1': 1}

        import re as _re
        devanagari = _re.compile(r'[\u0900-\u097F]')
        skip = {label_col, 'v1', 'v2', 'label', 'labels'}
        target_cols = []

        for col in df.columns:
            if col in skip:
                continue
            col_lower = col.lower()
            # English: 'text', 'text_en', 'en', 'english'
            if col_lower in ('text', 'text_en', 'en', 'english'):
                target_cols.append(col)
                continue
            # Hindi: 'text_hi', 'hi', 'hindi', or any column ending '_hi'
            if col_lower in ('text_hi', 'hi', 'hindi') or col_lower.endswith('_hi'):
                target_cols.append(col)
                continue
            # Auto-detect Hindi by Devanagari script content
            sample = df[col].dropna().astype(str).head(20)
            if any(devanagari.search(s) for s in sample):
                target_cols.append(col)

        if not target_cols:
            target_cols = ['v2'] if 'v2' in df.columns else []

        if not target_cols:
            print(f"  dbarbedillo: no English/Hindi columns found. Got: {df.columns.tolist()}")
            return pd.DataFrame(columns=['message', 'label'])

        result_dfs = []
        for col in target_cols:
            lang_df = pd.DataFrame({'message': df[col].astype(str), 'label': df[label_col]})
            lang_df['label'] = lang_df['label'].map(label_map)
            lang_df = lang_df.dropna(subset=['message', 'label'])
            lang_df['label'] = lang_df['label'].astype(int)
            lang_df = lang_df[lang_df['message'].str.strip() != '']
            result_dfs.append(lang_df)

        if not result_dfs:
            return pd.DataFrame(columns=['message', 'label'])

        result = pd.concat(result_dfs, ignore_index=True)
        print(f"  dbarbedillo (en+hi): {len(result)} rows from columns {target_cols}")
        return result
    except Exception as e:
        print(f"  dbarbedillo failed: {e}")
        return pd.DataFrame(columns=['message', 'label'])


def _load_rajnathpatel_multilingual() -> pd.DataFrame:
    """
    rajnathpatel/multilingual-spam-data (Kaggle).
    Columns: labels, text (English), text_hi (Hindi), text_de, text_fr
    We load text (English) and text_hi (Hindi) only.
    """
    try:
        import kagglehub, os
        path = kagglehub.dataset_download("rajnathpatel/multilingual-spam-data")
        csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
        if not csv_files:
            print("  rajnathpatel: no CSV files found")
            return pd.DataFrame(columns=['message', 'label'])

        raw = []
        for f in csv_files:
            try:
                raw.append(pd.read_csv(f"{path}/{f}", encoding='latin-1'))
            except Exception:
                continue
        if not raw:
            return pd.DataFrame(columns=['message', 'label'])

        df = pd.concat(raw, ignore_index=True)
        df = df.rename(columns={c: c.lower().strip() for c in df.columns})

        # Label column is 'labels' in this dataset
        lbl_col = next((c for c in ['label', 'labels', 'v1', 'category', 'class'] if c in df.columns), None)
        if lbl_col is None:
            print(f"  rajnathpatel: no label column. Got: {df.columns.tolist()}")
            return pd.DataFrame(columns=['message', 'label'])

        label_map = {'ham': 0, 'spam': 1, 0: 0, 1: 1, '0': 0, '1': 1}
        skip = {lbl_col, 'label', 'labels', 'v1', 'category', 'class'}

        # Load English (text) and Hindi (text_hi) columns
        msg_cols = []
        for col in df.columns:
            if col in skip:
                continue
            if col in ('text', 'message', 'sms', 'v2', 'text_en', 'en'):
                msg_cols.append(col)
            elif col in ('text_hi', 'hi', 'hindi') or col.endswith('_hi'):
                msg_cols.append(col)

        if not msg_cols:
            print(f"  rajnathpatel: no message columns found. Got: {df.columns.tolist()}")
            return pd.DataFrame(columns=['message', 'label'])

        result_dfs = []
        for col in msg_cols:
            r = pd.DataFrame({'message': df[col].astype(str), 'label': df[lbl_col]})
            r['label'] = r['label'].map(label_map)
            r = r.dropna(subset=['message', 'label'])
            r['label'] = r['label'].astype(int)
            r = r[r['message'].str.strip() != '']
            result_dfs.append(r)

        result = pd.concat(result_dfs, ignore_index=True)
        print(f"  rajnathpatel multilingual: {len(result)} rows from {msg_cols} "
              f"({int(result['label'].sum())} spam, {(result['label']==0).sum()} ham)")
        return result.reset_index(drop=True)
    except Exception as e:
        print(f"  rajnathpatel failed: {e}")
        return pd.DataFrame(columns=['message', 'label'])


def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['_norm'] = df['message'].str.lower().str.strip().str.replace(r'\s+', ' ', regex=True)
    df = df.drop_duplicates(subset='_norm').drop(columns=['_norm'])
    return df.reset_index(drop=True)


def load_dataset() -> pd.DataFrame:
    print("Loading datasets...")
    dfs = []
    for loader in [
        _load_uci,
        _load_deysi,
        _load_gaurav,
        _synthetic_indian_legit,
        _load_dbarbedillo_multilingual,   # English + Hindi columns only
        _load_rajnathpatel_multilingual,  # Real Hindi/Hinglish Indian spam
    ]:
        df = loader()
        if len(df) > 0:
            dfs.append(df)

    if not dfs:
        raise RuntimeError("No datasets loaded! Check internet/Kaggle credentials.")

    df = pd.concat(dfs, ignore_index=True)
    before = len(df)
    df = _deduplicate(df)
    print(f"  Removed {before - len(df)} duplicates")

    # Extract features
    url_rows, text_rows, clean_msgs = [], [], []
    for msg in df['message']:
        url_rows.append(url_features(str(msg)))
        text_rows.append(text_features(str(msg)))
        clean_msgs.append(clean_text(str(msg)))

    df = pd.concat([df.reset_index(drop=True),
                    pd.DataFrame(url_rows),
                    pd.DataFrame(text_rows)], axis=1)
    df['message'] = clean_msgs

    spam = int(df['label'].sum())
    ham = len(df) - spam
    print(f"\nFinal dataset: {len(df)} messages ({spam} spam, {ham} ham, ratio {ham/spam:.1f}:1)\n")
    return df


# ── Feature engineering ───────────────────────────────────────────────────────

def get_feature_columns() -> list:
    return URL_FEATURE_COLS + TEXT_FEATURE_COLS


def split_dataset(df, seed=42):
    train, temp = train_test_split(df, test_size=0.3, stratify=df['label'], random_state=seed)
    val, test = train_test_split(temp, test_size=0.5, stratify=temp['label'], random_state=seed)
    return train.reset_index(drop=True), val.reset_index(drop=True), test.reset_index(drop=True)


def extract_urls(text: str) -> list:
    urls = re.findall(r'(?:https?://|www\.)[^\s]+', text, re.IGNORECASE)
    domains = re.findall(r'(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|edu|gov|co\.in|in|io|co)', text, re.IGNORECASE)
    return list(set(urls + domains))


def url_features(text: str) -> dict:
    urls = extract_urls(text)
    has_url = int(bool(urls))
    num_urls = len(urls)
    has_http = int(any('http:' in u.lower() for u in urls))
    has_https = int(any('https:' in u.lower() for u in urls))

    suspicious_tld = has_ip_url = has_shortened_url = has_legit_domain = 0
    max_url_len = 0

    for url in urls:
        max_url_len = max(max_url_len, len(url))
        try:
            ext = tldextract.extract(url)
            domain = ext.domain.lower()
            suffix = ext.suffix.lower()
            full = f"{domain}.{suffix}" if suffix else domain
            if suffix in SUSPICIOUS_TLDS:
                suspicious_tld = 1
            if full in URL_SHORTENERS:
                has_shortened_url = 1
            if full in LEGIT_DOMAINS or suffix in TRUSTED_TLDS:
                has_legit_domain = 1
        except Exception:
            pass
        if re.match(r'https?://\d+\.\d+\.\d+\.\d+', url, re.IGNORECASE):
            has_ip_url = 1

    return {
        'has_url': has_url, 'num_urls': num_urls,
        'has_http': has_http, 'has_https': has_https,
        'suspicious_tld': suspicious_tld, 'max_url_len': max_url_len,
        'has_ip_url': has_ip_url, 'has_shortened_url': has_shortened_url,
        'has_legit_domain': has_legit_domain,
    }


def text_features(text: str) -> dict:
    num_chars = len(text)
    num_words = len(text.split())
    upper = sum(c.isupper() for c in text)
    pct_upper = upper / num_chars if num_chars else 0.0
    digits = sum(c.isdigit() for c in text)
    pct_digits = digits / num_chars if num_chars else 0.0
    num_special = sum(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in text)
    words = text.lower().split()
    urgency_count = sum(1 for w in words if w in URGENCY_WORDS)
    # FIXED: Indian phone numbers — 10-digit or +91 prefix
    has_phone = int(bool(re.search(r'(?:\+91[-\s]?)?\d{10}', text)))
    # FIXED: only ₹ symbol triggers currency, not 'Rs.' text
    has_currency = int(any(s in text for s in CURRENCY_SYMBOLS))

    return {
        'num_chars': num_chars, 'num_words': num_words,
        'pct_upper': pct_upper, 'pct_digits': pct_digits,
        'num_special': num_special, 'urgency_count': urgency_count,
        'has_phone': has_phone, 'has_currency': has_currency,
    }


def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
