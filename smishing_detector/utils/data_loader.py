import re
import pandas as pd
import numpy as np
import requests
from sklearn.model_selection import train_test_split
import tldextract
from io import StringIO
from .safe_browsing import is_domain_legitimate


SUSPICIOUS_TLDS = {'tk', 'ml', 'ga', 'cf', 'gq', 'xyz', 'top', 'click', 'link', 'work', 'loan', 'online', 'site', 'info', 'biz'}

URL_SHORTENERS = {'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'is.gd', 'buff.ly', 'rebrand.ly', 'cutt.ly'}

URGENCY_WORDS = {
    # English urgency
    'urgent', 'winner', 'won', 'free', 'prize', 'claim', 'cash',
    'congratulations', 'selected', 'reward', 'limited', 'act now',
    'suspended', 'click',
    'password', 'invoice', 'payment', 'attached', 'order', 'receipt',
    'crypto', 'bitcoin', 'wallet', 'action required',
    # Hinglish / Roman-script Hindi urgency markers
    'jaldi', 'turant', 'abhi', 'kijiye', 'rupaye', 'paisa',
    'khata', 'band', 'inam', 'jeeta', 'loot', 'offer',
    'kyc', 'recharge', 'cashback', 'lucky', 'gift', 'redeem',
    # Hinglish threat/social-engineering phrases
    'katega', 'kataega', 'kataegi', 'kategi', 'cut kar',
    'bijli', 'bijli cut', 'power cut', 'connection cut',
    'band ho jayega', 'band kar', 'band ho',
    'officer', 'helpline', 'turant call', 'abhi call',
    'aaj raat', 'kal subah', 'last chance', 'antim',
    'court notice', 'fir', 'giraftari', 'arrest',
}

CURRENCY_SYMBOLS = {'$', '£', '€', '₹', 'rs', 'rupee', 'btc', 'eth', 'usdt'}


# Keep Indian "Rs"/"rupee" text from becoming a generic spam signal.
CURRENCY_SYMBOLS = {'$', '\u00a3', '\u20ac', '\u20b9', 'btc', 'eth', 'usdt'}

URL_FEATURE_COLS = [
    'has_url', 'num_urls', 'has_http', 'has_https', 'suspicious_tld',
    'max_url_len', 'has_ip_url', 'has_shortened_url', 'has_legit_domain'
]

TEXT_FEATURE_COLS = [
    'num_chars', 'num_words', 'pct_upper', 'pct_digits', 'num_special',
    'urgency_count', 'has_phone', 'has_currency'
]


LEGIT_DOMAINS = {
    'amazon.com', 'amazon.co.uk', 'amazon.in', 'netflix.com', 'spotify.com', 'apple.com', 
    'google.com', 'microsoft.com', 'paypal.com', 'ebay.com', 'walmart.com', 
    'target.com', 'bestbuy.com', 'costco.com', 'fedex.com', 'ups.com', 'usps.com',
    'airlines.com', 'ba.com', 'united.com', 'delta.com', 'jetblue.com',
    'library.org', 'cvs.com', 'walgreens.com', 'riteaid.com', 'shopify.com',
    'slack.com', 'zoom.us', 'gmail.com', 'outlook.com', 'yahoo.com',
    # Famous Indian Websites
    'flipkart.com', 'myntra.com', 'swiggy.com', 'zomato.com', 'makemytrip.com', 'yatra.com', 
    'cleartrip.com', 'paytm.com', 'phonepe.com', 'hdfcbank.com', 'onlinesbi.sbi', 'icicibank.com', 
    'axisbank.com', 'kotak.com', 'airindia.in', 'goindigo.in', 'irctc.co.in', 'redbus.in', 
    'olacabs.com', 'hotstar.com', 'sonyliv.com', 'zee5.com', 'jiocinema.com', 
    'timesofindia.indiatimes.com', 'hindustantimes.com', 'thehindu.com', 'ndtv.com', 'moneycontrol.com', 
    'bseindia.com', 'nseindia.com', 'naukri.com', 'shaadi.com', 'bharatmatrimony.com',
    'bookmyshow.com', 'policybazaar.com', 'nykaa.com', 'ajio.com', 'firstcry.com',
    'bigbasket.com', 'blinkit.com', 'zepto.com', 'upstox.com', 'groww.in', 'zerodha.com',
    # Frequent SMS Senders (Telecom, DTH, Credit Cards)
    'airtel.in', 'jio.com', 'myvi.in', 'vi.com', 'bsnl.co.in', 'tataplay.com', 'dishtv.in',
    'sbicard.com', 'bajajfinserv.in', 'cred.club'
}

TRUSTED_TLDS = {'com', 'org', 'net', 'edu', 'gov', 'co.uk', 'au', 'ca', 'de', 'fr'}


def _load_uci_dataset() -> pd.DataFrame:
    """Load the UCI SMS Spam Collection via kagglehub."""
    try:
        import kagglehub
        path = kagglehub.dataset_download("uciml/sms-spam-collection-dataset")
        df = pd.read_csv(f"{path}/spam.csv", encoding='latin-1')
        df = df[['v1', 'v2']].rename(columns={'v1': 'label_str', 'v2': 'message'})
        df['label'] = df['label_str'].map({'ham': 0, 'spam': 1})
        df = df[['message', 'label']].dropna()
        print(f"  UCI SMS Spam Collection: {len(df)} messages loaded")
        return df
    except Exception as e:
        print(f"  Warning: Failed to load UCI dataset: {e}")
        return pd.DataFrame(columns=['message', 'label'])


def _load_huggingface_spam_detection() -> pd.DataFrame:
    """Load the Deysi/spam-detection-dataset from HuggingFace (no API key needed).
    Contains ~10,900 messages with balanced spam/ham split.
    """
    try:
        from datasets import load_dataset as hf_load
        ds = hf_load("Deysi/spam-detection-dataset")
        
        # Combine train and test splits
        dfs = []
        for split_name in ds.keys():
            split_df = ds[split_name].to_pandas()
            dfs.append(split_df)
        df = pd.concat(dfs, ignore_index=True)
        
        # Standardize column names
        if 'text' in df.columns:
            df = df.rename(columns={'text': 'message'})
        
        # Convert string labels to integers
        label_map = {'spam': 1, 'not_spam': 0, 'ham': 0, 1: 1, 0: 0, '1': 1, '0': 0}
        df['label'] = df['label'].map(label_map)
        
        df = df[['message', 'label']].dropna()
        df['label'] = df['label'].astype(int)
        df = df[df['label'].isin([0, 1])]
        
        print(f"  HuggingFace spam-detection-dataset: {len(df)} messages loaded")
        return df
    except Exception as e:
        print(f"  Warning: Failed to load HuggingFace spam-detection dataset: {e}")
        return pd.DataFrame(columns=['message', 'label'])


def _load_kaggle_sms_spam() -> pd.DataFrame:
    """Load the team-ai/sms-spam-dataset from Kaggle (may need auth)."""
    try:
        import kagglehub
        path = kagglehub.dataset_download("team-ai/sms-spam-dataset")
        
        # Try common CSV names
        import os
        csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
        if not csv_files:
            print(f"  Warning: No CSV files found in Kaggle SMS spam dataset")
            return pd.DataFrame(columns=['message', 'label'])
        
        df = pd.read_csv(f"{path}/{csv_files[0]}", encoding='latin-1')
        
        # Standardize columns (this dataset may have different column names)
        col_lower = {c: c.lower() for c in df.columns}
        df = df.rename(columns=col_lower)
        
        if 'v1' in df.columns and 'v2' in df.columns:
            df = df.rename(columns={'v1': 'label_str', 'v2': 'message'})
            df['label'] = df['label_str'].map({'ham': 0, 'spam': 1})
        elif 'label' in df.columns and 'message' in df.columns:
            if df['label'].dtype == object:
                df['label'] = df['label'].map({'ham': 0, 'spam': 1})
        elif 'label' in df.columns and 'text' in df.columns:
            df = df.rename(columns={'text': 'message'})
            if df['label'].dtype == object:
                df['label'] = df['label'].map({'ham': 0, 'spam': 1})
        elif 'sms' in df.columns:
            df = df.rename(columns={'sms': 'message'})
        
        df = df[['message', 'label']].dropna()
        df['label'] = df['label'].astype(int)
        
        print(f"  Kaggle SMS Spam Dataset: {len(df)} messages loaded")
        return df
    except Exception as e:
        print(f"  Warning: Failed to load Kaggle SMS spam dataset: {e}")
        return pd.DataFrame(columns=['message', 'label'])


def _load_dbarbedillo_multilingual() -> pd.DataFrame:
    """
    Load all language columns from dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset.
    This dataset contains UCI SMS messages translated into multiple languages
    (English, Hindi, French, German, etc.). ALL language variants are added
    to the training pool so the model learns multilingual spam patterns.
    """
    try:
        from datasets import load_dataset as hf_load
        ds = hf_load("dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset")

        dfs_raw = []
        for split_name in ds.keys():
            dfs_raw.append(ds[split_name].to_pandas())
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
            if col_lower in ('text', 'text_en', 'en', 'english'):
                target_cols.append(col)
                continue
            if col_lower in ('text_hi', 'hi', 'hindi') or col_lower.endswith('_hi'):
                target_cols.append(col)
                continue
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
        print(f"  Warning: Failed to load dbarbedillo multilingual dataset: {e}")
        return pd.DataFrame(columns=['message', 'label'])


def _load_rajnathpatel_multilingual() -> pd.DataFrame:
    """
    Load rajnathpatel/multilingual-spam-data from Kaggle.
    Contains real Hindi/Hinglish spam messages collected in India —
    the most India-specific training signal in the pipeline.
    """
    try:
        import kagglehub
        import os
        path = kagglehub.dataset_download("rajnathpatel/multilingual-spam-data")

        csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
        if not csv_files:
            print("  Warning: No CSV files in rajnathpatel multilingual dataset")
            return pd.DataFrame(columns=['message', 'label'])

        raw_dfs = []
        for csv_file in csv_files:
            try:
                raw_dfs.append(pd.read_csv(f"{path}/{csv_file}", encoding='latin-1'))
            except Exception:
                continue

        if not raw_dfs:
            return pd.DataFrame(columns=['message', 'label'])

        df = pd.concat(raw_dfs, ignore_index=True)
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
        print(f"  Warning: Failed to load rajnathpatel multilingual dataset: {e}")
        return pd.DataFrame(columns=['message', 'label'])
def _load_ngadou_spam_sms() -> pd.DataFrame:
    """Load the Ngadou/Spam_SMS dataset from HuggingFace."""
    try:
        from datasets import load_dataset as hf_load
        ds = hf_load("Ngadou/Spam_SMS")['train']
        df = ds.to_pandas()
        if 'email' in df.columns:
            df = df.rename(columns={'email': 'message'})
        df = df[['message', 'label']].dropna()
        df['label'] = df['label'].astype(int)
        print(f"  Ngadou/Spam_SMS Dataset: {len(df)} messages loaded")
        return df
    except Exception as e:
        print(f"  Warning: Failed to load Ngadou/Spam_SMS dataset: {e}")
        return pd.DataFrame(columns=['message', 'label'])


def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate messages by normalized text content."""
    df = df.copy()
    df['_norm'] = df['message'].str.lower().str.strip().str.replace(r'\s+', ' ', regex=True)
    df = df.drop_duplicates(subset='_norm', keep='first')
    df = df.drop(columns=['_norm'])
    return df.reset_index(drop=True)


def load_dataset() -> pd.DataFrame:
    """Load and combine SMS spam datasets from multiple sources."""
    print("Loading datasets from multiple sources...")
    
    # Load from all sources
    dfs = []
    
    # Source 1: UCI (primary, should always work)
    uci_df = _load_uci_dataset()
    if len(uci_df) > 0:
        dfs.append(uci_df)
    
    # Source 2: HuggingFace spam detection dataset (no auth needed, ~10.9k messages)
    hf_df = _load_huggingface_spam_detection()
    if len(hf_df) > 0:
        dfs.append(hf_df)
    
    # Source 3: Kaggle SMS Spam (may fail without auth — that's OK)
    kaggle_df = _load_kaggle_sms_spam()
    if len(kaggle_df) > 0:
        dfs.append(kaggle_df)
        
    # Source 4: Ngadou/Spam_SMS (for out-of-distribution robustness)
    ngadou_df = _load_ngadou_spam_sms()
    if len(ngadou_df) > 0:
        dfs.append(ngadou_df)

    # Source 5: dbarbedillo multilingual (all language columns — Hindi, French, German, etc.)
    dbarbedillo_df = _load_dbarbedillo_multilingual()
    if len(dbarbedillo_df) > 0:
        dfs.append(dbarbedillo_df)

    # Source 6: rajnathpatel multilingual (real Hindi/Hinglish Indian spam)
    rajnathpatel_df = _load_rajnathpatel_multilingual()
    if len(rajnathpatel_df) > 0:
        dfs.append(rajnathpatel_df)
    
    if not dfs:
        raise RuntimeError("Failed to load any dataset! Check your internet connection.")
    
    # Combine and deduplicate
    df = pd.concat(dfs, ignore_index=True)
    before_dedup = len(df)
    df = _deduplicate(df)
    after_dedup = len(df)
    
    if before_dedup != after_dedup:
        print(f"  Removed {before_dedup - after_dedup} duplicate messages")
    
    # Extract features and clean text
    url_feats_list = []
    text_feats_list = []
    cleaned_messages = []

    for msg in df['message']:
        url_feats = url_features(str(msg))
        text_feats = text_features(str(msg))
        cleaned = clean_text(str(msg))

        url_feats_list.append(url_feats)
        text_feats_list.append(text_feats)
        cleaned_messages.append(cleaned)

    url_df = pd.DataFrame(url_feats_list)
    text_df = pd.DataFrame(text_feats_list)

    df = pd.concat([df.reset_index(drop=True), url_df, text_df], axis=1)
    df['message'] = cleaned_messages

    spam_count = int(df['label'].sum())
    ham_count = len(df) - spam_count
    print(f"\nDataset loaded: {len(df)} messages ({spam_count} spam, {ham_count} ham)")

    return df


def get_feature_columns() -> list[str]:
    return URL_FEATURE_COLS + TEXT_FEATURE_COLS


def split_dataset(df, seed=42) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_df, temp_df = train_test_split(df, test_size=0.3, stratify=df['label'], random_state=seed)
    val_df, test_df = train_test_split(temp_df, test_size=0.5, stratify=temp_df['label'], random_state=seed)
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True), test_df.reset_index(drop=True)


def extract_urls(text: str) -> list[str]:
    url_pattern = r'(?:https?://|www\.)[^\s]+'
    urls = re.findall(url_pattern, text, re.IGNORECASE)
    
    domain_pattern = r'(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|edu|gov|co\.uk|au|ca|in|io|co)'
    domain_urls = re.findall(domain_pattern, text, re.IGNORECASE)
    urls.extend(domain_urls)
    
    return list(set(urls))


def url_features(text: str) -> dict:
    urls = extract_urls(text)

    has_url = 1 if urls else 0
    num_urls = len(urls)
    has_http = 1 if any('http:' in u.lower() for u in urls) else 0
    has_https = 1 if any('https:' in u.lower() for u in urls) else 0

    suspicious_tld = 0
    trusted_tld_count = 0
    max_url_len = 0
    has_ip_url = 0
    has_shortened_url = 0
    has_legit_domain = 0

    for url in urls:
        max_url_len = max(max_url_len, len(url))

        try:
            extracted = tldextract.extract(url)
            domain = extracted.domain.lower() if extracted.domain else ''
            suffix = extracted.suffix.lower() if extracted.suffix else ''
            
            if suffix in SUSPICIOUS_TLDS:
                suspicious_tld = 1
            if suffix in TRUSTED_TLDS:
                trusted_tld_count += 1
            
            # Check full domain (domain.suffix) against shorteners
            full_domain = f"{domain}.{suffix}" if suffix else domain
            if full_domain in URL_SHORTENERS:
                has_shortened_url = 1
            # Use Google Safe Browsing API to check domain legitimacy
            if is_domain_legitimate(full_domain):
                has_legit_domain = 1
        except:
            pass

        if re.match(r'https?://\d+\.\d+\.\d+\.\d+', url, re.IGNORECASE):
            has_ip_url = 1

    return {
        'has_url': has_url,
        'num_urls': num_urls,
        'has_http': has_http,
        'has_https': has_https,
        'suspicious_tld': suspicious_tld,
        'max_url_len': max_url_len,
        'has_ip_url': has_ip_url,
        'has_shortened_url': has_shortened_url,
        'has_legit_domain': has_legit_domain
    }


def text_features(text: str) -> dict:
    num_chars = len(text)
    num_words = len(text.split())

    upper_count = sum(1 for c in text if c.isupper())
    pct_upper = upper_count / num_chars if num_chars > 0 else 0.0

    digit_count = sum(1 for c in text if c.isdigit())
    pct_digits = digit_count / num_chars if num_chars > 0 else 0.0

    special_count = sum(1 for c in text if c in '!@#$%^&*()_+-=[]{}|;:,.<>?')
    num_special = special_count

    words = text.lower().split()
    urgency_count = sum(1 for w in words if w in URGENCY_WORDS)

    phone_pattern = r'(?:\+91[-\s]?)?\d[\d\s-]{8,}\d'
    has_phone = 1 if re.search(phone_pattern, text) else 0

    has_currency = 1 if any(s in text.lower() for s in CURRENCY_SYMBOLS) else 0

    return {
        'num_chars': num_chars,
        'num_words': num_words,
        'pct_upper': pct_upper,
        'pct_digits': pct_digits,
        'num_special': num_special,
        'urgency_count': urgency_count,
        'has_phone': has_phone,
        'has_currency': has_currency
    }


def clean_text(text: str, remove_urls: bool = False) -> str:
    if remove_urls:
        text = re.sub(r'(?:https?://|www\.)[^\s]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
