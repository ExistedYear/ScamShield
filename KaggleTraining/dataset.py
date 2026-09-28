import torch
import numpy as np
import pandas as pd
from torch.utils.data import Dataset, DataLoader


URL_FEATURE_COLS = [
    'has_url', 'num_urls', 'has_http', 'has_https', 'suspicious_tld',
    'max_url_len', 'has_ip_url', 'has_shortened_url', 'has_legit_domain'
]

TEXT_FEATURE_COLS = [
    'num_chars', 'num_words', 'pct_upper', 'pct_digits', 'num_special',
    'urgency_count', 'has_phone', 'has_currency'
]

FEATURE_COLS = URL_FEATURE_COLS + TEXT_FEATURE_COLS  # 17 total


class SMSDataset(Dataset):
    def __init__(self, df: pd.DataFrame, tokenizer,
                 max_len: int = 128, feature_mins=None, feature_ranges=None):
        self.texts = df['message'].tolist()
        self.labels = df['label'].values.astype(np.float32)
        self.tokenizer = tokenizer
        self.max_len = max_len

        self.features = df[FEATURE_COLS].values.astype(np.float32)

        # Normalise: use training-set stats if provided, else compute from self
        if feature_mins is not None and feature_ranges is not None:
            self.feature_mins = feature_mins
            self.feature_ranges = feature_ranges
        else:
            self.feature_mins = self.features.min(axis=0)
            ranges = self.features.max(axis=0) - self.feature_mins
            self.feature_ranges = np.where(ranges == 0, 1.0, ranges)

        self.features = (self.features - self.feature_mins) / self.feature_ranges

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            self.texts[idx],
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_tensors='pt',
        )
        return {
            'input_ids':      enc['input_ids'].squeeze(0),
            'attention_mask': enc['attention_mask'].squeeze(0),
            'hand_features':  torch.from_numpy(self.features[idx]),
            'label':          torch.tensor(self.labels[idx], dtype=torch.float32),
        }


def build_dataloaders(train_df, val_df, test_df, tokenizer, batch_size=32):
    train_ds = SMSDataset(train_df, tokenizer)

    val_ds  = SMSDataset(val_df,  tokenizer,
                          feature_mins=train_ds.feature_mins,
                          feature_ranges=train_ds.feature_ranges)
    test_ds = SMSDataset(test_df, tokenizer,
                          feature_mins=train_ds.feature_mins,
                          feature_ranges=train_ds.feature_ranges)

    loader_kwargs = dict(batch_size=batch_size, num_workers=2, pin_memory=True)

    train_loader = DataLoader(train_ds, shuffle=True,  **loader_kwargs)
    val_loader   = DataLoader(val_ds,  shuffle=False, **loader_kwargs)
    test_loader  = DataLoader(test_ds, shuffle=False, **loader_kwargs)

    norm_stats = {
        'feature_mins':   train_ds.feature_mins,
        'feature_ranges': train_ds.feature_ranges,
    }
    return train_loader, val_loader, test_loader, norm_stats
