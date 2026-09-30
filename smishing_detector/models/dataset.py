import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset


class SMSDataset(Dataset):
    def __init__(
        self,
        df: pd.DataFrame,
        tokenizer,
        max_len: int = 128,
        feature_mins: np.ndarray = None,
        feature_ranges: np.ndarray = None,
    ):
        from utils.data_loader import get_feature_columns

        self.texts = df["message"].astype(str).tolist()
        self.labels = df["label"].values.astype(np.float32)
        self.tokenizer = tokenizer
        self.max_len = max_len

        feature_cols = get_feature_columns()
        missing = [col for col in feature_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing feature columns: {missing}")

        features = df[feature_cols].values.astype(np.float32)
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

        if feature_mins is None or feature_ranges is None:
            self.feature_mins = features.min(axis=0)
            ranges = features.max(axis=0) - self.feature_mins
            self.feature_ranges = np.where(ranges == 0, 1.0, ranges).astype(np.float32)
        else:
            self.feature_mins = np.asarray(feature_mins, dtype=np.float32)
            self.feature_ranges = np.asarray(feature_ranges, dtype=np.float32)
            self.feature_ranges = np.where(self.feature_ranges == 0, 1.0, self.feature_ranges)

        features = (features - self.feature_mins) / self.feature_ranges
        features = np.nan_to_num(features, nan=0.0, posinf=3.0, neginf=-2.0)
        self.features = np.clip(features, -2.0, 3.0).astype(np.float32)

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            max_length=self.max_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "hand_features": torch.from_numpy(self.features[idx]),
            "label": torch.tensor(self.labels[idx], dtype=torch.float32),
        }


def build_dataloaders(train_df, val_df, test_df, tokenizer, batch_size=32):
    train_dataset = SMSDataset(train_df, tokenizer)
    val_dataset = SMSDataset(
        val_df,
        tokenizer,
        feature_mins=train_dataset.feature_mins,
        feature_ranges=train_dataset.feature_ranges,
    )
    test_dataset = SMSDataset(
        test_df,
        tokenizer,
        feature_mins=train_dataset.feature_mins,
        feature_ranges=train_dataset.feature_ranges,
    )

    loader_kwargs = {
        "batch_size": batch_size,
        "num_workers": 2,
        "pin_memory": torch.cuda.is_available(),
    }

    train_loader = DataLoader(train_dataset, shuffle=True, **loader_kwargs)
    val_loader = DataLoader(val_dataset, shuffle=False, **loader_kwargs)
    test_loader = DataLoader(test_dataset, shuffle=False, **loader_kwargs)

    norm_stats = {
        "feature_mins": train_dataset.feature_mins,
        "feature_ranges": train_dataset.feature_ranges,
    }
    return train_loader, val_loader, test_loader, norm_stats
