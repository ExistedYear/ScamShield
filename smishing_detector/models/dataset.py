import torch
import numpy as np
import pandas as pd
from torch.utils.data import Dataset, DataLoader


class SMSDataset(Dataset):
    def __init__(self, df: pd.DataFrame, tokenizer, max_len: int = 128,
                 feature_mins: np.ndarray = None, feature_maxs: np.ndarray = None):
        self.texts = df['message'].tolist()
        self.labels = df['label'].values.astype(np.float32)
        self.tokenizer = tokenizer
        self.max_len = max_len

        from utils.data_loader import get_feature_columns
        feature_cols = get_feature_columns()
        self.features = df[feature_cols].values.astype(np.float32)

        # Use provided normalization stats (from training set) or compute them
        if feature_mins is not None and feature_maxs is not None:
            self.feature_mins = feature_mins
            self.feature_ranges = feature_maxs
        else:
            self.feature_mins = self.features.min(axis=0)
            ranges = self.features.max(axis=0) - self.feature_mins
            # Avoid division by zero: if range is 0, set to 1
            self.feature_ranges = np.where(ranges == 0, 1.0, ranges)

        self.features = (self.features - self.feature_mins) / self.feature_ranges

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]

        encoding = self.tokenizer(
            text,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].squeeze(0),
            'attention_mask': encoding['attention_mask'].squeeze(0),
            'hand_features': torch.from_numpy(self.features[idx]),
            'label': torch.tensor(self.labels[idx], dtype=torch.float32)
        }


def build_dataloaders(train_df, val_df, test_df, tokenizer, batch_size=32):
    # Build train dataset first and extract normalization stats
    train_dataset = SMSDataset(train_df, tokenizer)

    # Pass train normalization stats to val and test datasets
    val_dataset = SMSDataset(val_df, tokenizer,
                             feature_mins=train_dataset.feature_mins,
                             feature_maxs=train_dataset.feature_ranges)
    test_dataset = SMSDataset(test_df, tokenizer,
                              feature_mins=train_dataset.feature_mins,
                              feature_maxs=train_dataset.feature_ranges)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=2,
        pin_memory=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=2,
        pin_memory=True
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=2,
        pin_memory=True
    )

    # Return normalization stats along with dataloaders
    norm_stats = {
        'feature_mins': train_dataset.feature_mins,
        'feature_ranges': train_dataset.feature_ranges
    }

    return train_loader, val_loader, test_loader, norm_stats