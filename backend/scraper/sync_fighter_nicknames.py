"""sync_fighter_nicknames.py

Brings every fighter_details.NICKNAME in line with what UFCStats lists today.

The weekly scraper keeps a fighter's nickname current once they fight again
(live_scraper._sync_identity). Fighters who have not fought since their row was
imported keep whatever the import gave them: Melissa Amaya was stored with no
nickname while UFCStats lists "Mamba". This catches everyone up once.

UFCStats' A-Z fighter listing carries First, Last, Nickname and the profile URL
for every fighter, so 26 pages cover the whole table instead of one page per
fighter. Rows are matched by URL, the only identity UFCStats gives us.

Nicknames only. Names are reported, never written: a row renamed here without
a new bout would match none of its own bouts, which is exactly the
validate_etl.py check that blocked the pipeline on 2026-09-27 and 2026-10-04.
Names follow UFCStats through the weekly scrape instead, when a bout carrying
the new name arrives.

Before writing, the old value of every changed row is saved to
reports/nickname_sync_backup_<timestamp>.json, so the run can be undone.

Usage:
    python backend/scraper/sync_fighter_nicknames.py --dry-run
    python backend/scraper/sync_fighter_nicknames.py
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import string
import sys
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import text

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from db.database import engine
from live_scraper import LiveUFCScraper

logger = logging.getLogger(__name__)

LISTING_URL = 'http://ufcstats.com/statistics/fighters?char={}&page=all'
REPORTS_DIR = os.path.join(_HERE, 'reports')


def parse_listing(soup) -> dict[str, dict]:
    """{profile URL: {'name': ..., 'nickname': ...}} for one listing page.

    nickname is '' when UFCStats lists none.
    """
    table = soup.find('table', class_='b-statistics__table')
    if table is None:
        raise ValueError('fighter listing table not found - page layout changed?')
    fighters = {}
    for row in table.find('tbody').find_all('tr'):
        cells = row.find_all('td')
        link = row.find('a')
        if len(cells) < 3 or link is None:
            continue                                  # the blank spacer row
        first, last, nickname = (c.get_text(strip=True) for c in cells[:3])
        fighters[link['href']] = {
            'name': ' '.join(filter(None, (first, last))),
            'nickname': nickname,
        }
    return fighters


def plan_changes(listing: dict[str, dict], rows) -> tuple[list[dict], list[dict]]:
    """Split DB rows into nickname changes to apply and name differences to report.

    rows: (id, FIRST, LAST, NICKNAME, URL) tuples.
    """
    changes, renamed = [], []
    for fighter_id, first, last, old_nickname, url in rows:
        listed = listing.get(url)
        if listed is None:
            continue
        new_nickname = listed['nickname'] or None
        if new_nickname != old_nickname:
            changes.append({'id': fighter_id, 'url': url,
                            'old': old_nickname, 'new': new_nickname})
        stored = ' '.join(filter(None, (first, last)))
        if listed['name'] and listed['name'] != stored:
            renamed.append({'id': fighter_id, 'stored': stored,
                            'ufcstats': listed['name']})
    return changes, renamed


def scrape_listing() -> dict[str, dict]:
    scraper = LiveUFCScraper()
    try:
        listing = {}
        for char in string.ascii_lowercase:
            page = parse_listing(scraper._get_soup(LISTING_URL.format(char)))
            logger.info(f'{char}: {len(page)} fighters')
            listing.update(page)
        return listing
    finally:
        scraper._close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--dry-run', action='store_true',
                        help='report what would change without writing')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    listing = scrape_listing()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, "FIRST", "LAST", "NICKNAME", "URL"
            FROM fighter_details WHERE "URL" IS NOT NULL
        """)).fetchall()

    changes, renamed = plan_changes(listing, rows)
    unlisted = sum(1 for r in rows if r[4] not in listing)
    kinds = Counter(
        'added' if c['old'] is None else 'cleared' if c['new'] is None else 'changed'
        for c in changes
    )

    logger.info(f'UFCStats lists {len(listing):,} fighters; '
                f'{len(rows):,} fighter rows have a URL, {unlisted:,} of them not listed')
    logger.info(f'Nickname changes: {len(changes):,} '
                f'({kinds["added"]} added, {kinds["changed"]} changed, {kinds["cleared"]} cleared)')
    for c in changes[:15]:
        logger.info(f'  {c["id"]}: {c["old"]!r} -> {c["new"]!r}')
    logger.info(f'Name differences, reported only: {len(renamed):,}')
    for r in renamed[:15]:
        logger.info(f'  {r["id"]}: {r["stored"]!r} - UFCStats lists {r["ufcstats"]!r}')

    if not listing or unlisted > len(rows) // 10:
        logger.error('Listing looks incomplete - refusing to write')
        return 1
    if args.dry_run or not changes:
        return 0

    os.makedirs(REPORTS_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = os.path.join(REPORTS_DIR, f'nickname_sync_backup_{stamp}.json')
    with open(backup, 'w', encoding='utf-8') as f:
        json.dump(changes, f, indent=2, ensure_ascii=False)
    logger.info(f'Old values saved to {backup}')

    with engine.begin() as conn:
        for c in changes:
            conn.execute(text("""
                UPDATE fighter_details SET "NICKNAME" = :new
                WHERE id = :id AND "URL" = :url
            """), c)
    logger.info(f'Updated {len(changes):,} nicknames')
    return 0


if __name__ == '__main__':
    sys.exit(main())
