"""ml/run_train.py — CLI entry point for model training.

Usage
-----
    cd backend
    python -m ml.run_train
    python -m ml.run_train --eval-only
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.train import train

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train UFC fight prediction models.")
    parser.add_argument(
        "--eval-only",
        action="store_true",
        help="Evaluate on test set only; do not write model files.",
    )
    args = parser.parse_args()

    logger.info("=== Model Training Pipeline ===")
    metrics = train(eval_only=args.eval_only)

    print("\n" + "=" * 50)
    print(f"Win/Loss   accuracy : {metrics['win_accuracy']:.4f}")
    print(f"Win/Loss   ROC-AUC  : {metrics['win_roc_auc']:.4f}")
    print(f"Method     accuracy : {metrics['method_accuracy']:.4f}")
    print(f"Train rows          : {metrics['train_rows']:,}")
    print(f"Test rows           : {metrics['test_rows']:,}")
    print(f"Train period        : {metrics['train_date_range'][0]} → {metrics['train_date_range'][1]}")
    print(f"Test period         : {metrics['test_date_range'][0]} → {metrics['test_date_range'][1]}")


if __name__ == "__main__":
    main()
