"""
utils/multilingual_loader.py
-----------------------------
Loads Hindi and Hinglish test datasets for multilingual evaluation.
Used ONLY for evaluation — not added to training data.
"""

import pandas as pd
import numpy as np
import re
from datasets import load_dataset as hf_load


def detect_language(text: str) -> str:
    """
    Detect if a message is:
    - 'hindi'   : contains Devanagari Unicode characters (pure Hindi)
    - 'hinglish': Roman script with Hindi words mixed with English
    - 'english' : standard English
    """
    # Check for Devanagari Unicode range (0900-097F)
    devanagari_pattern = re.compile(r'[\u0900-\u097F]')
    if devanagari_pattern.search(text):
        return 'hindi'

    # Common Hinglish words that appear in Roman script
    hinglish_markers = {
        'aapka', 'aapke', 'abhi', 'karo', 'kare', 'kiya', 'nahi', 'nai',
        'hai', 'hain', 'ho', 'ka', 'ki', 'ke', 'ko', 'se', 'mein', 'par',
        'aur', 'bhi', 'yeh', 'woh', 'ap', 'apka', 'jana', 'karna', 'dena',
        'lena', 'milega', 'milegi', 'paisa', 'rupaye', 'khata', 'band',
        'verify', 'kijiye', 'dijiye', 'lijiye', 'phir', 'agar', 'toh',
        'jaldi', 'turant', 'abhi', 'sirf', 'bahut', 'accha', 'theek'
    }
    words = set(text.lower().split())
    if len(words.intersection(hinglish_markers)) >= 2:
        return 'hinglish'

    return 'english'


def load_hindi_test_data() -> pd.DataFrame:
    """
    Load Hindi (Devanagari) test data from HuggingFace multilingual dataset.
    Returns DataFrame with columns: message, label, language
    """
    print("Loading Hindi test data from HuggingFace...")
    try:
        ds = hf_load("dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset")

        dfs = []
        for split_name in ds.keys():
            split_df = ds[split_name].to_pandas()
            dfs.append(split_df)
        df = pd.concat(dfs, ignore_index=True)

        # This dataset has columns for each language
        # Find the Hindi column
        hindi_col = None
        for col in df.columns:
            if 'hindi' in col.lower() or 'hi' == col.lower():
                hindi_col = col
                break

        if hindi_col is None:
            # Try text_hi column (actual name in this dataset)
            if 'text_hi' in df.columns:
                hindi_col = 'text_hi'
            else:
                # Auto-detect by Devanagari content
                skip = {'label', 'labels', 'v1', 'v2'}
                for col in df.columns:
                    if col in skip:
                        continue
                    sample = df[col].dropna().head(10).astype(str)
                    devanagari = re.compile(r'[\u0900-\u097F]')
                    if any(devanagari.search(s) for s in sample):
                        hindi_col = col
                        break

        if hindi_col is None:
            print("  Warning: Could not find Hindi column")
            return pd.DataFrame(columns=['message', 'label', 'language'])

        # Get label column — could be 'v1', 'label', or 'labels'
        label_col = next((c for c in ['v1', 'label', 'labels'] if c in df.columns), None)
        if label_col is None:
            print(f"  Warning: No label column found. Got: {df.columns.tolist()}")
            return pd.DataFrame(columns=['message', 'label', 'language'])

        result_df = pd.DataFrame({
            'message': df[hindi_col].astype(str),
            'label': df[label_col]
        })

        # Standardise labels
        label_map = {'ham': 0, 'spam': 1, 0: 0, 1: 1, '0': 0, '1': 1}
        result_df['label'] = result_df['label'].map(label_map)
        result_df = result_df.dropna(subset=['message', 'label'])
        result_df['label'] = result_df['label'].astype(int)
        result_df['language'] = 'hindi'

        print(f"  Hindi test data: {len(result_df)} messages "
              f"({result_df['label'].sum()} spam, "
              f"{(result_df['label']==0).sum()} ham)")
        return result_df.reset_index(drop=True)

    except Exception as e:
        print(f"  Warning: Failed to load Hindi data: {e}")
        return pd.DataFrame(columns=['message', 'label', 'language'])


def load_hinglish_test_data() -> pd.DataFrame:
    """
    Load Hinglish test data from Kaggle multilingual spam dataset.
    Returns DataFrame with columns: message, label, language
    """
    print("Loading Hinglish test data from Kaggle...")
    try:
        import kagglehub
        path = kagglehub.dataset_download("rajnathpatel/multilingual-spam-data")

        import os
        csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
        if not csv_files:
            print("  Warning: No CSV files in Kaggle multilingual dataset")
            return pd.DataFrame(columns=['message', 'label', 'language'])

        dfs = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(f"{path}/{csv_file}", encoding='latin-1')
                dfs.append(df)
            except Exception:
                continue

        if not dfs:
            return pd.DataFrame(columns=['message', 'label', 'language'])

        df = pd.concat(dfs, ignore_index=True)

        # Standardise column names
        col_lower = {c: c.lower().strip() for c in df.columns}
        df = df.rename(columns=col_lower)

        # Find message and label columns
        msg_col = next((c for c in df.columns if c in ['text', 'message', 'sms', 'v2']), None)
        lbl_col = next((c for c in ['label', 'labels', 'v1', 'category', 'class'] if c in df.columns), None)

        if not msg_col or not lbl_col:
            print(f"  Warning: Could not identify columns. Found: {df.columns.tolist()}")
            return pd.DataFrame(columns=['message', 'label', 'language'])

        result_df = pd.DataFrame({
            'message': df[msg_col].astype(str),
            'label': df[lbl_col]
        })

        label_map = {'ham': 0, 'spam': 1, 0: 0, 1: 1, '0': 0, '1': 1}
        result_df['label'] = result_df['label'].map(label_map)
        result_df = result_df.dropna(subset=['message', 'label'])
        result_df['label'] = result_df['label'].astype(int)

        # Detect language per message and keep only Hindi/Hinglish
        result_df['language'] = result_df['message'].apply(detect_language)
        result_df = result_df[result_df['language'].isin(['hindi', 'hinglish'])]

        print(f"  Hinglish/Hindi test data: {len(result_df)} messages "
              f"({result_df['label'].sum()} spam, "
              f"{(result_df['label']==0).sum()} ham)")
        return result_df.reset_index(drop=True)

    except Exception as e:
        print(f"  Warning: Failed to load Hinglish data: {e}")
        return pd.DataFrame(columns=['message', 'label', 'language'])


def load_all_multilingual_test_data() -> dict[str, pd.DataFrame]:
    """
    Loads all multilingual test data.
    Returns dict with keys: 'hindi', 'hinglish', 'combined'
    """
    hindi_df = load_hindi_test_data()
    hinglish_df = load_hinglish_test_data()

    # Separate hinglish from hindi in the combined df
    pure_hindi = pd.concat([
        hindi_df,
        hinglish_df[hinglish_df['language'] == 'hindi']
    ], ignore_index=True)

    pure_hinglish = hinglish_df[hinglish_df['language'] == 'hinglish'].reset_index(drop=True)

    combined = pd.concat([pure_hindi, pure_hinglish], ignore_index=True)

    print(f"\nTotal multilingual test data:")
    print(f"  Pure Hindi:  {len(pure_hindi)} messages")
    print(f"  Hinglish:    {len(pure_hinglish)} messages")
    print(f"  Combined:    {len(combined)} messages")

    return {
        'hindi': pure_hindi,
        'hinglish': pure_hinglish,
        'combined': combined
    }
