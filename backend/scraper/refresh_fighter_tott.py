"""refresh_fighter_tott.py

Re-reads named fighters' UFCStats profiles and rewrites their fighter_tott row
from the live page: height, weight, reach, stance, DOB, career record and the
career rate stats.

The bulk scrapers fill gaps across the whole table and skip rows that already
hold a value, so neither can correct a row whose values are wrong rather than
missing.  This exists for that case, such as the repair in
db/migrations/009_montanha_identity.sql, where two fighters held each other's
measurements.

Fighters are addressed by fighter_details.id and the page is fetched from that
row's own "URL", so a name that is wrong in the database cannot misdirect the
refresh.

Usage:
    python backend/scraper/refresh_fighter_tott.py 1f8cd763 4e30f276
    python backend/scraper/refresh_fighter_tott.py --dry-run 1f8cd763
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from sqlalchemy import text

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from db.database import engine
from live_scraper import LiveUFCScraper

logger = logging.getLogger(__name__)

CAREER_COLUMNS = ('slpm', 'str_acc', 'sapm', 'str_def', 'td_avg', 'td_acc', 'td_def', 'sub_avg')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('fighter_ids', nargs='+', help='fighter_details.id values to refresh')
    parser.add_argument('--dry-run', action='store_true', help='Scrape but do not write to DB')
    args = parser.parse_args()

    with engine.connect() as conn:
        fighters = conn.execute(text("""
            SELECT id, trim(coalesce("FIRST", '') || ' ' || coalesce("LAST", '')) AS name, "URL"
            FROM fighter_details
            WHERE id = ANY(:ids) AND "URL" IS NOT NULL
            ORDER BY id
        """), {'ids': args.fighter_ids}).mappings().all()

    missing = set(args.fighter_ids) - {f['id'] for f in fighters}
    if missing:
        logger.error(f'No fighter row with a URL for: {", ".join(sorted(missing))}')
        return 1

    scraper = LiveUFCScraper()
    failed = 0
    try:
        for fighter in fighters:
            physical = scraper.scrape_fighter_physical_stats(fighter['URL'])
            career = scraper.scrape_fighter_career_stats(fighter['URL'])
            if not physical:
                logger.error(f'  {fighter["id"]} {fighter["name"]}: could not read {fighter["URL"]}')
                failed += 1
                continue

            logger.info(
                f'  {fighter["id"]} {fighter["name"]}: '
                f'{physical.get("height")} / {physical.get("weight")} / {physical.get("reach")} / '
                f'DOB {physical.get("dob")} / '
                f'{physical.get("career_wins")}-{physical.get("career_losses")}-{physical.get("career_draws")}'
            )
            if args.dry_run:
                continue

            # store_fighter_tott resolves the row by URL and writes the physical
            # columns and the record. The career rate stats it does not cover
            # are written here from the same page read.
            scraper.store_fighter_tott(fighter['name'], {**physical, 'url': fighter['URL']})
            if career:
                with engine.begin() as conn:
                    conn.execute(
                        text('UPDATE fighter_tott SET '
                             + ', '.join(f'{c} = :{c}' for c in CAREER_COLUMNS)
                             + ' WHERE fighter_id = :fighter_id'),
                        {**{c: career.get(c) for c in CAREER_COLUMNS}, 'fighter_id': fighter['id']},
                    )
    finally:
        scraper._close()

    logger.info(f'Refreshed {len(fighters) - failed} of {len(fighters)} fighters')
    return 1 if failed else 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%H:%M:%S')
    sys.exit(main())
