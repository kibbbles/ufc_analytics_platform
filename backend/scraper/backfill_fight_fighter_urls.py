"""backfill_fight_fighter_urls.py

Records fight_details.fighter_a_url / fighter_b_url (migration 008) for fights
stored before live_scraper.py began saving them.  populate_fighter_fks.py then
resolves missing FKs by identity instead of by name, and validate_etl.py checks
every stored FK against its URL.

This exists because names are not identifiers.  Noche UFC: Silva vs. Delgado
(2026-09-12) could not be resolved because "Jean Silva" belongs to two fighters.

Each event page lists every fight on the card with both fighters' profile links,
so the backfill reads one page per event rather than one per fight.  The event
page lists the winner first, so its pairs are matched to BOUT by name.  Fights
the event page cannot account for fall back to their own fight page.

It writes URLs only, never FKs, so there is one resolution path to trust.  A page
whose fighter names do not match "BOUT" is refused: the URL order must line up
with the name order, or fighter_a_url would be attached to fighter B.

Each event commits on its own and only rows with no URLs are selected, so an
interrupted run resumes where it stopped.

Usage:
    python backend/scraper/backfill_fight_fighter_urls.py --dry-run
    python backend/scraper/backfill_fight_fighter_urls.py
    python backend/scraper/backfill_fight_fighter_urls.py --limit-events 5
    python backend/scraper/post_scrape_clean.py --phase 1   # then resolve
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from itertools import groupby

from sqlalchemy import text

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from db.database import engine
from live_scraper import LiveUFCScraper

logger = logging.getLogger(__name__)

EVENT_ROW_CLASS = 'b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click'


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


def parse_event_fighters(soup) -> dict[str, dict]:
    """Map each fight URL on an event page to its fighters' names and URLs.

    Returns the same keys as LiveUFCScraper._parse_fight_meta so both sources
    pass through one guard.  Rows without exactly two fighter links are omitted
    and fall back to the fight page.
    """
    fights = {}
    for row in soup.find_all('tr', class_=EVENT_ROW_CLASS):
        fight_url = row.get('data-link')
        cells = row.find_all('td', class_='b-fight-details__table-col')
        if not fight_url or len(cells) < 2:
            continue
        links = [a for a in cells[1].find_all('a') if '/fighter-details/' in (a.get('href') or '')]
        if len(links) != 2:
            continue
        fights[fight_url.strip()] = {
            'fighter_a_name': links[0].get_text(strip=True),
            'fighter_a_url': links[0].get('href').strip(),
            'fighter_b_name': links[1].get_text(strip=True),
            'fighter_b_url': links[1].get('href').strip(),
        }
    return fights


def usable(bout: str, meta: dict | None) -> bool:
    return bool(meta and meta.get('fighter_a_url') and meta.get('fighter_b_url')
                and bout_matches_page(bout, meta))


def orient_to_bout(bout: str, meta: dict | None) -> dict | None:
    """Return meta in BOUT's fighter order, or None if it cannot be trusted.

    The event page lists the winner first while BOUT follows the fight page, so
    about half the rows arrive reversed.  Each URL is read from the same link as
    its name, so swapping the pair keeps every URL with its own fighter.  When
    both fighters share a name the order carries the identity, so no swap is
    attempted.
    """
    if usable(bout, meta):
        return meta
    if not meta or _norm(meta.get('fighter_a_name')) == _norm(meta.get('fighter_b_name')):
        return None
    swapped = {
        'fighter_a_name': meta.get('fighter_b_name'), 'fighter_a_url': meta.get('fighter_b_url'),
        'fighter_b_name': meta.get('fighter_a_name'), 'fighter_b_url': meta.get('fighter_a_url'),
    }
    return swapped if usable(bout, swapped) else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Scrape but do not write to DB')
    parser.add_argument('--limit-events', type=int, help='Process at most N events')
    args = parser.parse_args()

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT fd.id, fd."BOUT", fd."URL", e."URL" AS event_url
            FROM fight_details fd
            JOIN event_details e ON e.id = fd.event_id
            WHERE fd.fighter_a_url IS NULL
              AND fd.fighter_b_url IS NULL
              AND fd."URL" IS NOT NULL
            ORDER BY e.date_proper DESC, e.id, fd.id
        """)).mappings().all()

    events = [(url, list(group)) for url, group in groupby(rows, key=lambda r: r['event_url'])]
    if args.limit_events:
        events = events[:args.limit_events]
    logger.info(f'Fights without fighter URLs: {len(rows)} across {len(events)} events to process')
    if not events:
        return 0

    written = refused = failed = fallbacks = 0
    scraper = LiveUFCScraper()
    try:
        for n, (event_url, fights) in enumerate(events, 1):
            try:
                on_card = parse_event_fighters(scraper._get_soup(event_url, delay=(1.0, 2.0)))
            except Exception as exc:
                logger.warning(f'  event {event_url} fetch failed, using fight pages: {exc}')
                on_card = {}

            updates = []
            for row in fights:
                meta = orient_to_bout(row['BOUT'], on_card.get(row['URL'].strip()))
                if meta is None:
                    fallbacks += 1
                    try:
                        meta = scraper._parse_fight_meta(scraper._get_soup(row['URL']))
                    except Exception as exc:
                        logger.warning(f'  {row["id"]} fetch failed: {exc}')
                        failed += 1
                        continue
                    if not usable(row['BOUT'], meta):
                        logger.warning(
                            f'  {row["id"]} refused: BOUT {row["BOUT"]!r} vs page '
                            f'{meta.get("fighter_a_name")!r} / {meta.get("fighter_b_name")!r}'
                        )
                        refused += 1
                        continue
                updates.append({'a': meta['fighter_a_url'], 'b': meta['fighter_b_url'], 'id': row['id']})

            if updates and not args.dry_run:
                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE fight_details
                        SET fighter_a_url = :a, fighter_b_url = :b
                        WHERE id = :id
                          AND fighter_a_url IS NULL
                          AND fighter_b_url IS NULL
                    """), updates)
            written += len(updates)
            logger.info(f'[{n}/{len(events)}] {event_url}: {len(updates)}/{len(fights)} fights')
    finally:
        scraper._close()

    logger.info(
        f'{"Would write" if args.dry_run else "Wrote"} {written}, refused {refused}, '
        f'failed {failed} ({fallbacks} needed the fight page)'
    )
    return 1 if (refused or failed) else 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%H:%M:%S')
    sys.exit(main())
