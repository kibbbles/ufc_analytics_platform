"""run_upcoming.py — Task 15

CLI entry point for the full upcoming pipeline:
  1. Scrape UFCStats upcoming events + fights  (upcoming_scraper.py)
  2. Store each bout's section start time       (refresh_section_starts.py)
  3. Compute ML predictions for matched fights  (compute_predictions.py)

Step 2 tells step 3 which fights have started and must not be rewritten. If it
fails, step 3 still runs: an unknown start time falls back to an earlier
freeze, which is safe. The run then exits 1 so the failure is not mistaken for
success.

Usage (from backend/):
    python scraper/run_upcoming.py
    python scraper/run_upcoming.py --dry-run
"""

import argparse
import logging
import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from scraper.upcoming_scraper import UpcomingScraper
from scraper.compute_predictions import run as compute_run
from scraper.refresh_section_starts import run as sections_run

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Scrape upcoming UFC events and compute ML predictions'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Run every step without writing to DB')
    args = parser.parse_args()

    logger.info('=' * 60)
    logger.info('STEP 1/3 - Scraping upcoming events and fights')
    logger.info('=' * 60)

    scraper = UpcomingScraper()
    scrape_ok = scraper.run(dry_run=args.dry_run)

    if not scrape_ok:
        logger.error('Scraper step failed — aborting pipeline')
        sys.exit(1)

    logger.info('=' * 60)
    logger.info('STEP 2/3 - Storing section start times from UFC.com')
    logger.info('=' * 60)

    sections_ok = sections_run(dry_run=args.dry_run)

    if not sections_ok:
        logger.error('Section start lookup failed - predicting anyway under the fallback freeze')

    logger.info('=' * 60)
    logger.info('STEP 3/3 - Computing ML predictions')
    logger.info('=' * 60)

    predict_ok = compute_run(dry_run=args.dry_run)

    if not predict_ok:
        logger.error('Prediction step completed with errors')
        sys.exit(1)

    if not sections_ok:
        sys.exit(1)

    logger.info('Pipeline complete.')


if __name__ == '__main__':
    main()
