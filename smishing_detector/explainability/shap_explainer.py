import numpy as np
import torch
import shap
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor import SmishingPredictor
from utils.data_loader import url_features, text_features, clean_text, get_feature_columns
from models.model import get_tokenizer, MAX_LEN


class SmishingExplainer:
    def __init__(self, predictor: SmishingPredictor):
        self.predictor = predictor

    def _get_prediction_function(self):
        def predict_fn(texts):
            results = []
            for text in texts:
                cleaned = clean_text(text)

                encoding = self.predictor.tokenizer(
                    cleaned,
                    max_length=MAX_LEN,
                    padding='max_length',
                    truncation=True,
                    return_tensors='pt'
                )

                input_ids = encoding['input_ids'].to(self.predictor.device)
                attention_mask = encoding['attention_mask'].to(self.predictor.device)

                url_feats = url_features(text)
                text_feats = text_features(text)

                feature_cols = get_feature_columns()
                combined = {**url_feats, **text_feats}
                raw = np.array([[combined[col] for col in feature_cols]], dtype=np.float32)
                norm = (raw - self.predictor.feature_mins) / self.predictor.feature_ranges
                hand_features = torch.from_numpy(norm).to(self.predictor.device)

                prob = self.predictor.model.predict_proba(input_ids, attention_mask, hand_features).item()
                results.append(prob)

            return np.array(results)

        return predict_fn

    def explain_text(self, message: str, num_features: int = 10) -> dict:
        predict_fn = self._get_prediction_function()

        tokenizer = self.predictor.tokenizer
        masker = shap.maskers.Text(tokenizer)

        explainer = shap.Explainer(predict_fn, masker)

        shap_values = explainer([message])

        tokens = [str(t) for t in shap_values.data[0]]
        values = shap_values.values[0]

        token_importance = list(zip(tokens, values))
        token_importance.sort(key=lambda x: x[1], reverse=True)

        top_spam = [(t, v) for t, v in token_importance if v > 0][:num_features]
        top_ham = [(t, v) for t, v in token_importance if v < 0][-num_features:]
        top_ham.sort(key=lambda x: x[1])

        feature_cols = get_feature_columns()
        url_feats = url_features(message)
        text_feats = text_features(message)
        combined = {**url_feats, **text_feats}

        feature_importances = {col: combined[col] for col in feature_cols}

        return {
            "top_spam_words": top_spam,
            "top_ham_words": top_ham,
            "feature_importances": feature_importances
        }

    def plot_explanation(self, message: str) -> plt.Figure:
        explanation = self.explain_text(message, num_features=10)

        fig, ax = plt.subplots(figsize=(10, 6))

        all_words = explanation["top_spam_words"] + explanation["top_ham_words"]
        all_words.sort(key=lambda x: x[1], reverse=True)

        words = [w for w, v in all_words[:10]]
        values = [v for w, v in all_words[:10]]

        colors = ['#d62728' if v > 0 else '#2ca02c' for v in values]

        ax.barh(words, values, color=colors)
        ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        ax.set_xlabel('SHAP Value')
        ax.set_title('SHAP Explanation for Spam Detection')

        plt.tight_layout()
        return fig
