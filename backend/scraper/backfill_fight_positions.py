"""backfill_fight_positions.py

Scrapes every UFCStats event page and sets fight_details.position based on
the order fights appear on the page (position 0 = main event / first listed,
position N = last prelim).

Usage:
    python backend/scraper/backfill_fight_positions.py
    python backend/scraper/backfill_fight_positions.py --workers 8
    python backend/scraper/backfill_fight_positions.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from sqlalchemy import text

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from db.database import SessionLocal, engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; UFC-Analytics-Bot/1.0)'}
REQUEST_TIMEOUT = 15


def fetch_fight_order(event_url: str) -> list[str]:
    """
    Fetch an event page and return fight detail URLs in card order
    (position 0 = main event, as listed top-to-bottom on UFCStats).
    Returns empty list on failure.
    """
    try:
        resp = requests.get(event_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(f'Failed to fetch {event_url}: {exc}')
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')

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

    urls = []
    for row in rows:
        link = row.get('data-link', '').strip()
        if link:
            urls.append(link)

    return urls


def process_event(event_id: str, event_url: str, fight_urls_by_url: dict[str, str]) -> tuple[int, int]:
    """
    Scrape one event page and return (positions_set, fights_in_event).
    fight_urls_by_url: maps fight_details.URL -> fight_details.id for this event.
    Returns (matched, total_on_page).
    """
    card_urls = fetch_fight_order(event_url)
    if not card_urls:
        return 0, 0

    updates = []
    for position, fight_url in enumerate(card_urls):
        fight_id = fight_urls_by_url.get(fight_url)
        if fight_id:
            updates.append({'pos': position, 'fight_id': fight_id})

    if not updates:
        return 0, len(card_urls)

    with engine.connect() as conn:
        conn.execute(
            text('UPDATE fight_details SET position = :pos WHERE id = :fight_id'),
            updates,
        )
        conn.commit()

    return len(updates), len(card_urls)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=5, help='Concurrent threads (default 5)')
    parser.add_argument('--dry-run', action='store_true', help='Scrape but do not write to DB')
    args = parser.parse_args()

    db = SessionLocal()

    # Load all events + their fight URLs grouped by event
    logger.info('Loading events and fight URLs from DB...')
    event_rows = db.execute(text(
        'SELECT id, "URL" FROM event_details WHERE "URL" IS NOT NULL ORDER BY date_proper DESC'
    )).mappings().all()

    fight_rows = db.execute(text(
        'SELECT id, event_id, "URL" FROM fight_details WHERE "URL" IS NOT NULL'
    )).mappings().all()
    db.close()

    # Build per-event lookup: event_id -> {fight_url: fight_id}
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

    def _task(event_id: str, event_url: str) -> tuple[str, int, int]:
        fight_map = fights_by_event.get(event_id, {})
        if args.dry_run:
            card_urls = fetch_fight_order(event_url)
            matched = sum(1 for u in card_urls if u in fight_map)
            return event_id, matched, len(card_urls)
        matched, total = process_event(event_id, event_url, fight_map)
        return event_id, matched, total

    futures = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in event_rows:
            f = pool.submit(_task, row['id'], row['URL'])
            futures[f] = row['id']

        for i, future in enumerate(as_completed(futures), 1):
            event_id = futures[future]
            try:
                _, matched, total = future.result()
                total_matched += matched
                if total == 0:
                    total_events_failed += 1
                else:
                    total_events_done += 1
            except Exception as exc:
                logger.warning(f'Event {event_id} raised: {exc}')
                total_events_failed += 1

            if i % 50 == 0 or i == len(event_rows):
                elapsed = time.time() - start
                logger.info(
                    f'  Progress: {i}/{len(event_rows)} events '
                    f'| {total_matched} fights positioned '
                    f'| {elapsed:.0f}s elapsed'
                )

    elapsed = time.time() - start
    logger.info('=== Backfill complete ===')
    logger.info(f'  Events scraped OK : {total_events_done}')
    logger.info(f'  Events failed     : {total_events_failed}')
    logger.info(f'  Fights positioned : {total_matched}')
    logger.info(f'  Time elapsed      : {elapsed:.0f}s')

    # Verify
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
