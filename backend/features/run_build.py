"""features/run_build.py — CLI runner for the feature engineering pipeline.

Called by the GitHub Actions feature-engineering workflow after every
successful ETL cleanup run.  Also runnable locally for ad-hoc rebuilds.

Usage
-----
    cd backend
    python features/run_build.py             # full rebuild
    python features/run_build.py --no-select # skip feature selection step
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure 'backend/' is on sys.path when invoked from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from features.pipeline import PARQUET_PATH, build_training_matrix
from features.selection import OUTPUT_PATH as SEL_PATH, run_feature_selection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild training matrix and (optionally) feature selection."
    )
    parser.add_argument(
        "--no-select",
        action="store_true",
        help="Skip feature selection; only rebuild training_data.parquet.",
    )
    args = parser.parse_args()

    logger.info("=== Feature Engineering Pipeline ===")

    # Step 1: Build training matrix -> training_data.parquet
    mat = build_training_matrix(save_path=PARQUET_PATH)
    logger.info(
        "Training matrix: %d rows x %d columns -> %s",
        len(mat), len(mat.columns), PARQUET_PATH,
    )

    # Step 2: Feature selection -> selected_features.json
    if not args.no_select:
        result = run_feature_selection()
        logger.info(
            "Feature selection: %d -> %d features -> %s",
            result["n_features_before"],
            result["n_features_selected"],
            SEL_PATH,
        )

    logger.info("=== Done ===")


if __name__ == "__main__":
    main()
