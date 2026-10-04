import torch
import torch.nn as nn
from transformers import XLMRobertaModel, XLMRobertaTokenizerFast


MODEL_NAME = "xlm-roberta-base"
MAX_LEN = 128
NUM_HANDCRAFTED = 17


class SmishingDetector(nn.Module):
    def __init__(self, num_handcrafted: int = 17, dropout: float = 0.3, freeze_bert_layers: int = 0):
        super().__init__()

        # XLM-RoBERTa encoder
        # xlm-roberta-base has 12 transformer layers with 768-d hidden size
        self.bert = XLMRobertaModel.from_pretrained(MODEL_NAME)

        # Freeze bottom N layers if specified
        for i, layer in enumerate(self.bert.encoder.layer):
            if i < freeze_bert_layers:
                for param in layer.parameters():
                    param.requires_grad = False

        self.feat_proj = nn.Sequential(
            nn.Linear(num_handcrafted, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 64),
            nn.ReLU()
        )

        classifier_input_dim = 768 + 64
        self.classifier = nn.Sequential(
            nn.Linear(classifier_input_dim, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1)
        )

    def forward(self, input_ids, attention_mask, hand_features):
        # XLM-RoBERTa output format is same as BERT
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls_emb = outputs.last_hidden_state[:, 0, :]   # CLS token → (B, 768)
        feat_emb = self.feat_proj(hand_features)        # (B, 64)
        fused = torch.cat([cls_emb, feat_emb], dim=1)  # (B, 832)
        logit = self.classifier(fused)
        return logit.squeeze(-1)

    def predict_proba(self, input_ids, attention_mask, hand_features):
        with torch.no_grad():
            logit = self.forward(input_ids, attention_mask, hand_features)
            return torch.sigmoid(logit)


def get_tokenizer():
    # XLM-RoBERTa tokenizer handles 100 languages automatically
    return XLMRobertaTokenizerFast.from_pretrained(MODEL_NAME)
