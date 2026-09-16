"""backfill_fight_fighter_urls.py

Reads the UFCStats fight page for completed fights that are missing a fighter
FK and have no stored fighter URLs, and records fight_details.fighter_a_url /
fighter_b_url (migration 008).  populate_fighter_fks.py then resolves those rows
by identity instead of by name.

This exists for rows stored before live_scraper.py began saving the URLs, such
as Noche UFC: Silva vs. Delgado (2026-09-12), whose main event could not be
resolved because "Jean Silva" belongs to two fighters.

It writes URLs only, never FKs, so there is one resolution path to trust.  The
fight page is parsed with live_scraper's own parser, and a page whose fighter
names do not match "BOUT" is refused: the URL order must line up with the name
order, or fighter_a_url would be attached to fighter B.

Usage:
    python backend/scraper/backfill_fight_fighter_urls.py --dry-run
    python backend/scraper/backfill_fight_fighter_urls.py
    python backend/scraper/post_scrape_clean.py --phase 1   # then resolve
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


def _norm(name: str | None) -> str:
    return ' '.join((name or '').split()).lower()


def bout_matches_page(bout: str, meta: dict) -> bool:
    """True when the page's fighter names are BOUT's names, in BOUT's order."""
    if ' vs. ' not in (bout or ''):
        return False
    name_a, name_b = bout.split(' vs. ', 1)
    return (
        _norm(name_a) == _norm(meta.get('fighter_a_name'))
        and _norm(name_b) == _norm(meta.get('fighter_b_name'))
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Scrape but do not write to DB')
    args = parser.parse_args()

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, "BOUT", "URL"
            FROM fight_details
            WHERE (fighter_a_id IS NULL OR fighter_b_id IS NULL)
              AND fighter_a_url IS NULL
              AND fighter_b_url IS NULL
              AND "URL" IS NOT NULL
            ORDER BY id
        """)).mappings().all()

    logger.info(f'Fights missing an FK and fighter URLs: {len(rows)}')
    if not rows:
        return 0

    written = refused = failed = 0
    scraper = LiveUFCScraper()
    try:
        for row in rows:
            try:
                meta = scraper._parse_fight_meta(scraper._get_soup(row['URL']))
            except Exception as exc:
                logger.warning(f'  {row["id"]} fetch failed: {exc}')
                failed += 1
                continue

            url_a, url_b = meta.get('fighter_a_url'), meta.get('fighter_b_url')
            if not (url_a and url_b) or not bout_matches_page(row['BOUT'], meta):
                logger.warning(
                    f'  {row["id"]} refused: BOUT {row["BOUT"]!r} vs page '
                    f'{meta.get("fighter_a_name")!r} / {meta.get("fighter_b_name")!r}'
                )
                refused += 1
                continue

            logger.info(f'  {row["id"]} {row["BOUT"]}: {url_a} | {url_b}')
            if not args.dry_run:
                with engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE fight_details
                        SET fighter_a_url = :a, fighter_b_url = :b
                        WHERE id = :id
                    """), {'a': url_a, 'b': url_b, 'id': row['id']})
                    conn.commit()
            written += 1
    finally:
        scraper._close()

    logger.info(
        f'{"Would write" if args.dry_run else "Wrote"} {written}, '
        f'refused {refused}, failed {failed}'
    )
    return 1 if (refused or failed) else 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%H:%M:%S')
    sys.exit(main())
