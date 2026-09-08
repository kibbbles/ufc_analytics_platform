"""backfill_fight_positions.py

Scrapes UFCStats event pages and sets fight_details.position based on the
order fights appear on the page (position 0 = main event / first listed,
position N = last prelim).

UFCStats serves a JavaScript proof-of-work challenge to plain HTTP clients,
so this uses Playwright — the same browser stack as live_scraper.py — and
runs sequentially rather than across a thread pool.

Usage:
    python backend/scraper/backfill_fight_positions.py --only-missing
    python backend/scraper/backfill_fight_positions.py
    python backend/scraper/backfill_fight_positions.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from sqlalchemy import text

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from db.database import SessionLocal, engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
)
PAGE_TIMEOUT_MS = 60_000


class EventPageFetcher:
    """Headless-browser fetcher that clears the UFCStats JS challenge."""

    def __enter__(self):
        self._pw_manager = sync_playwright()
        self._pw = self._pw_manager.__enter__()
        self._browser = self._pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        self._context = self._browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )
        self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self._page = self._context.new_page()
        return self

    def __exit__(self, *exc):
        try:
            self._browser.close()
        finally:
            self._pw_manager.__exit__(*exc)
        return False

    def fight_order(self, event_url: str) -> list[str]:
        """
        Return fight detail URLs in card order (index 0 = main event, as listed
        top-to-bottom on UFCStats).  Returns an empty list on failure.
        """
        try:
            time.sleep(random.uniform(1.0, 2.5))
            self._page.goto(event_url, wait_until='networkidle', timeout=PAGE_TIMEOUT_MS)
            soup = BeautifulSoup(self._page.content(), 'html.parser')
        except Exception as exc:
            logger.warning(f'Failed to fetch {event_url}: {exc}')
            return []

        rows = soup.find_all(
            'tr',
            class_='b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click',
        )
        if not rows:
            import re
            rows = [
                r for r in soup.find_all('tr', class_=re.compile(r'b-fight-details__table-row'))
                if r.find('td') and r.get('data-link')
            ]

        return [link for r in rows if (link := r.get('data-link', '').strip())]


def apply_positions(card_urls: list[str], fights_by_url: dict[str, str]) -> int:
    """Write positions for one event; returns the number of fights updated."""
    updates = [
        {'pos': position, 'fight_id': fights_by_url[url]}
        for position, url in enumerate(card_urls)
        if url in fights_by_url
    ]
    if not updates:
        return 0

    with engine.connect() as conn:
        conn.execute(
            text('UPDATE fight_details SET position = :pos WHERE id = :fight_id'),
            updates,
        )
        conn.commit()

    return len(updates)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Scrape but do not write to DB')
    parser.add_argument(
        '--only-missing',
        action='store_true',
        help='Only process events that still have at least one fight without a position',
    )
    args = parser.parse_args()

    db = SessionLocal()

    logger.info('Loading events and fight URLs from DB...')
    event_filter = ''
    if args.only_missing:
        event_filter = (
            ' AND id IN (SELECT event_id FROM fight_details WHERE position IS NULL)'
        )
    event_rows = db.execute(text(
        'SELECT id, "URL" FROM event_details WHERE "URL" IS NOT NULL'
        + event_filter
        + ' ORDER BY date_proper DESC'
    )).mappings().all()

    fight_rows = db.execute(text(
        'SELECT id, event_id, "URL" FROM fight_details WHERE "URL" IS NOT NULL'
    )).mappings().all()
    db.close()

    # event_id -> {fight_url: fight_id}
    fights_by_event: dict[str, dict[str, str]] = {}
    for f in fight_rows:
        fights_by_event.setdefault(f['event_id'], {})[f['URL']] = f['id']

    logger.info(f'Events to process: {len(event_rows)}')
    logger.info(f'Fights total: {len(fight_rows)}')

    if args.dry_run:
        logger.info('DRY RUN — no DB writes')

    total_matched = 0
    total_events_done = 0
    total_events_failed = 0
    start = time.time()

    with EventPageFetcher() as fetcher:
        for i, row in enumerate(event_rows, 1):
            fight_map = fights_by_event.get(row['id'], {})
            card_urls = fetcher.fight_order(row['URL'])

            if not card_urls:
                total_events_failed += 1
            else:
                total_events_done += 1
                if args.dry_run:
                    total_matched += sum(1 for u in card_urls if u in fight_map)
                else:
                    total_matched += apply_positions(card_urls, fight_map)

            if i % 25 == 0 or i == len(event_rows):
                logger.info(
                    f'  Progress: {i}/{len(event_rows)} events '
                    f'| {total_matched} fights positioned '
                    f'| {time.time() - start:.0f}s elapsed'
                )

    logger.info('=== Backfill complete ===')
    logger.info(f'  Events scraped OK : {total_events_done}')
    logger.info(f'  Events failed     : {total_events_failed}')
    logger.info(f'  Fights positioned : {total_matched}')
    logger.info(f'  Time elapsed      : {time.time() - start:.0f}s')

    db2 = SessionLocal()
    null_count = db2.execute(
        text('SELECT COUNT(*) FROM fight_details WHERE position IS NULL')
    ).scalar()
    total_count = db2.execute(
        text('SELECT COUNT(*) FROM fight_details')
    ).scalar()
    db2.close()
    logger.info(f'  Positions set     : {total_count - null_count}/{total_count}')


if __name__ == '__main__':
    main()
