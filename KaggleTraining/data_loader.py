"""
Compatibility wrapper for Kaggle training.

The canonical dataset and feature engine lives in:
    smishing_detector/utils/data_loader.py

Keeping KaggleTraining on the same module prevents training/inference feature
drift. When running on Kaggle, upload the full project, not just this folder.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from smishing_detector.utils.data_loader import *  # noqa: F401,F403
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "KaggleTraining now uses the canonical smishing_detector data engine. "
        "Upload the full project folder to Kaggle so smishing_detector/ is present."
    ) from exc
