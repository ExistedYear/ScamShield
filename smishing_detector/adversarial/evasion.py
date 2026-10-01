import random
import pandas as pd
import numpy as np
from sklearn.metrics import f1_score
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor import SmishingPredictor


CHARSWAP_MAP = {
    'a': '@', 'e': '3', 'i': '1', 'o': '0',
    's': '$', 't': '7', 'l': '1', 'g': '9'
}


def charswap(text: str, rate: float = 0.3) -> str:
    chars = list(text)
    eligible_indices = [i for i, c in enumerate(chars) if c.lower() in CHARSWAP_MAP]

    if not eligible_indices:
        return text

    num_swaps = max(1, int(len(eligible_indices) * rate))
    indices_to_swap = random.sample(eligible_indices, min(num_swaps, len(eligible_indices)))

    for i in indices_to_swap:
        chars[i] = CHARSWAP_MAP[chars[i].lower()]

    return ''.join(chars)


def eda_attack(text: str, rate: float = 0.2) -> str:
    words = text.split()

    if len(words) < 2:
        return text

    num_to_delete = max(1, int(len(words) * rate))
    indices_to_delete = random.sample(range(len(words)), num_to_delete)

    words = [w for i, w in enumerate(words) if i not in indices_to_delete]

    if len(words) >= 2:
        for i in range(0, len(words) - 1, 2):
            if random.random() < 0.5:
                words[i], words[i + 1] = words[i + 1], words[i]

    return ' '.join(words)


def spacing_attack(text: str) -> str:
    urgency_words = {'urgent', 'winner', 'free', 'prize', 'cash', 'claim', 'verify', 'act now'}

    words = text.split()
    modified = []

    for word in words:
        if word.lower() in urgency_words:
            modified.append(' '.join(list(word)))
        else:
            modified.append(word)

    return ' '.join(modified)


def hybrid_attack(text: str) -> str:
    text = charswap(text, rate=0.3)
    text = eda_attack(text, rate=0.2)
    text = spacing_attack(text)
    return text


def run_adversarial_evaluation(
    predictor: SmishingPredictor,
    test_df: pd.DataFrame,
    spam_only: bool = True
) -> pd.DataFrame:
    if spam_only:
        messages = test_df[test_df['label'] == 1]['message'].tolist()
        true_labels = [1] * len(messages)
    else:
        messages = test_df['message'].tolist()
        true_labels = test_df['label'].tolist()

    results = []

    for attack_name, attack_fn in [('CharSwap', charswap), ('EDA', eda_attack), ('Spacing', spacing_attack), ('Hybrid', hybrid_attack)]:
        original_preds = []
        attacked_preds = []

        for msg in messages:
            original_result = predictor.predict(msg)
            original_preds.append(1 if original_result['label'] == 'spam' else 0)

            attacked_msg = attack_fn(msg)
            attacked_result = predictor.predict(attacked_msg)
            attacked_preds.append(1 if attacked_result['label'] == 'spam' else 0)

        original_f1 = f1_score(true_labels, original_preds, zero_division=0)
        attacked_f1 = f1_score(true_labels, attacked_preds, zero_division=0)
        accuracy_drop = original_f1 - attacked_f1

        results.append({
            'attack_type': attack_name,
            'original_f1': original_f1,
            'attacked_f1': attacked_f1,
            'accuracy_drop': accuracy_drop
        })

    return pd.DataFrame(results)