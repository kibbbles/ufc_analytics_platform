"""
Upcoming UFC event scraper — Task 12

Scrapes http://ufcstats.com/statistics/events/upcoming to get all booked
UFC events, then visits each event detail page to get the full fight card
(fighter names, URLs, weight class, title fight flag).

Fighters are matched to fighter_details by URL (primary) with rapidfuzz
name fallback (threshold 88). Unmatched fighters stored with NULL id.

Writes to: upcoming_events, upcoming_fights
Predictions (upcoming_predictions) are computed separately — Task 13.

Usage:
    cd backend && python scraper/upcoming_scraper.py
    cd backend && python scraper/upcoming_scraper.py --dry-run
"""

import sys
import os
import re
import string
import random
import logging
import time
import argparse
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy import text

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from db.database import engine

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upcoming_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UPCOMING_URL = 'http://ufcstats.com/statistics/events/upcoming?page=all'
HEADERS      = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
FUZZY_THRESHOLD = 88


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

class UpcomingScraper:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.existing_ids: set = set()
        self._load_existing_ids()

    # ------------------------------------------------------------------
    # ID generation
    # ------------------------------------------------------------------

    def _load_existing_ids(self):
        tables = [
            'event_details', 'fighter_details', 'fight_details',
            'fight_results', 'fight_stats', 'fighter_tott',
            'upcoming_events', 'upcoming_fights', 'upcoming_predictions',
        ]
        with engine.connect() as conn:
            for table in tables:
                try:
                    for row in conn.execute(text(f'SELECT id FROM {table}')):
                        self.existing_ids.add(row[0])
                except Exception:
                    continue
        logger.info(f'Loaded {len(self.existing_ids)} existing IDs')

    def _new_id(self) -> str:
        chars = string.ascii_uppercase + string.digits
        while True:
            candidate = ''.join(random.choices(chars, k=6))
            if candidate not in self.existing_ids:
                self.existing_ids.add(candidate)
                return candidate

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, delay: tuple = (1.5, 3.0)) -> BeautifulSoup:
        time.sleep(random.uniform(*delay))
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return BeautifulSoup(resp.content, 'html.parser')

    # ------------------------------------------------------------------
    # Fighter matching
    # ------------------------------------------------------------------

    def _match_by_url(self, url: str) -> str | None:
        """Exact URL lookup against fighter_details."URL"."""
        if not url:
            return None
        with engine.connect() as conn:
            row = conn.execute(
                text('SELECT id FROM fighter_details WHERE "URL" = :url'),
                {'url': url}
            ).fetchone()
        return row[0] if row else None

    def _match_by_name(self, name: str) -> str | None:
        """rapidfuzz WRatio fallback (threshold 88)."""
        try:
            from rapidfuzz import fuzz
        except ImportError:
            logger.warning('rapidfuzz not installed — skipping name fallback')
            return None
        with engine.connect() as conn:
            rows = conn.execute(
                text('SELECT id, "FIRST", "LAST" FROM fighter_details')
            ).fetchall()
        name_q = name.lower().strip()
        best_score, best_id = 0, None
        for row in rows:
            candidate = f"{row[1] or ''} {row[2] or ''}".lower().strip()
            score = fuzz.WRatio(name_q, candidate)
            if score > best_score:
                best_score, best_id = score, row[0]
        if best_score >= FUZZY_THRESHOLD:
            logger.debug(f'Name match: "{name}" → {best_id} (score {best_score})')
            return best_id
        logger.warning(f'No match for "{name}" (best score: {best_score})')
        return None

    def resolve_fighter(self, url: str, name: str) -> str | None:
        """URL first, name fallback, None if neither matches."""
        return self._match_by_url(url) or self._match_by_name(name)

    # ------------------------------------------------------------------
    # Scraping — events listing
    # ------------------------------------------------------------------

    def scrape_upcoming_events(self) -> list[dict]:
        """
        Scrape upcoming events listing page.
        Same HTML structure as /completed — mirrors live_scraper.scrape_events_page.
        Returns list of dicts: event_name, ufcstats_url, date_proper, location, is_numbered.
        """
        logger.info(f'Fetching upcoming events: {UPCOMING_URL}')
        soup = self._get(UPCOMING_URL, delay=(0.5, 1.5))
        events = []

        tbody = soup.find('tbody')
        if not tbody:
            logger.warning('No tbody on upcoming events page')
            return events

        for row in tbody.find_all('tr', class_='b-statistics__table-row'):
            try:
                link = row.find('a', class_='b-link b-link_style_black')
                if not link:
                    continue
                event_name   = link.text.strip()
                event_url    = link.get('href', '').strip()
                if not event_url:
                    continue

                date_span  = row.find('span', class_='b-statistics__date')
                date_text  = date_span.text.strip() if date_span else ''

                location_td = row.find(
                    'td',
                    class_='b-statistics__table-col b-statistics__table-col_style_big-top-padding'
                )
                location = location_td.text.strip() if location_td else ''

                date_proper = None
                if date_text:
                    try:
                        date_proper = pd.to_datetime(date_text).date()
                    except Exception:
                        pass

                # e.g. "UFC 315" → numbered; "UFC Fight Night: ..." → not numbered
                is_numbered = bool(re.match(r'^UFC\s+\d+', event_name))

                events.append({
                    'event_name':   event_name,
                    'ufcstats_url': event_url,
                    'date_proper':  date_proper,
                    'location':     location,
                    'is_numbered':  is_numbered,
                })
            except Exception as e:
                logger.warning(f'Error parsing event row: {e}')

        logger.info(f'Found {len(events)} upcoming events')
        return events

    # ------------------------------------------------------------------
    # Scraping — fight card per event
    # ------------------------------------------------------------------

    def scrape_event_fights(self, event_url: str) -> list[dict]:
        """
        Scrape the full fight card from an event detail page.

        UFCStats event detail table structure (both upcoming and completed):
          col 0: outcome flag / empty
          col 1: fighter names — two <p><a> per cell (fighter A, fighter B)
          col 2: KD
          col 3: Sig. Str.
          col 4: Sig. Str. %
          col 5: Total Str.
          col 6: Td
          col 7: Td %
          col 8: Sub. Att
          col 9: Pass (or Rev.)
          col 10: weight class text (e.g. "Welterweight", "UFC Lightweight Championship")

        Fighter URLs from cell[1] links — primary key for fighter matching.
        Weight class from cell[10], or the rightmost non-empty text cell.
        Title fight: weight class contains "championship" or "title".

        Returns list of fight dicts.
        """
        logger.info(f'Scraping fight card: {event_url}')
        soup = self._get(event_url)
        fights = []

        # Fight rows — upcoming events use same selector as completed
        rows = soup.find_all(
            'tr',
            class_='b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click'
        )
        if not rows:
            # Upcoming events may use a slightly different class — try broader match
            rows = [
                r for r in soup.find_all('tr', class_=re.compile(r'b-fight-details__table-row'))
                if r.find('td')
            ]

        for row in rows:
            try:
                cells = row.find_all('td', class_='b-fight-details__table-col')
                if not cells:
                    cells = row.find_all('td')
                if len(cells) < 2:
                    continue

                # Fighter names + URLs — cell[1]: two <p> tags, each wrapping an <a>
                fighter_cell = cells[1]
                f_links = fighter_cell.find_all('a')
                if len(f_links) < 2:
                    continue

                fighter_a_name = f_links[0].text.strip()
                fighter_a_url  = f_links[0].get('href', '').strip()
                fighter_b_name = f_links[1].text.strip()
                fighter_b_url  = f_links[1].get('href', '').strip()

                if not fighter_a_name or not fighter_b_name:
                    continue

                # Title fight detection — scan full row text (UFCStats may put
                # "championship"/"title bout" in any cell, or show a belt icon)
                row_text       = row.get_text(separator=' ', strip=True).lower()
                is_title_fight = any(kw in row_text for kw in [
                    'championship', 'title bout', 'title fight', 'title match',
                    'for the ufc', 'ufc title', 'world title',
                ])
                is_interim     = is_title_fight and 'interim' in row_text

                # Weight class — scan cells for weight class keywords
                # Strip title/interim/ufc prefixes to get clean weight class name
                weight_class = ''
                for idx in [6, 7, 8, 9, 10, len(cells) - 1]:
                    if idx < len(cells):
                        raw = cells[idx].get_text(separator=' ', strip=True)
                        if raw and any(
                            kw in raw.lower()
                            for kw in ['weight', 'championship', 'title', 'pound', 'catch', 'women']
                        ):
                            # Normalize: strip "UFC", "Interim", "Championship", "Title Bout"
                            cleaned = re.sub(
                                r'\b(UFC|Interim|Championship|Title\s+Bout|Title)\b',
                                '', raw, flags=re.IGNORECASE
                            )
                            weight_class = ' '.join(cleaned.split())
                            break

                # fight detail URL (data-link) — may be empty for upcoming fights
                fight_url = row.get('data-link', '').strip()

                fights.append({
                    'fighter_a_name':  fighter_a_name,
                    'fighter_a_url':   fighter_a_url,
                    'fighter_b_name':  fighter_b_name,
                    'fighter_b_url':   fighter_b_url,
                    'weight_class':    weight_class,
                    'is_title_fight':  is_title_fight,
                    'is_interim_title': is_interim,
                    'ufcstats_url':    fight_url,
                })

            except Exception as e:
                logger.warning(f'Error parsing fight row: {e}')

        logger.info(f'Found {len(fights)} fights for {event_url}')
        return fights

    # ------------------------------------------------------------------
    # DB writes (idempotent upserts)
    # ------------------------------------------------------------------

    def _upsert_event(self, conn, event: dict) -> str:
        """
        Upsert upcoming_event row by ufcstats_url.
        Returns the row's id (existing or newly inserted).
        """
        row = conn.execute(
            text('SELECT id FROM upcoming_events WHERE ufcstats_url = :url'),
            {'url': event['ufcstats_url']}
        ).fetchone()

        if row:
            # Update mutable fields in case date/location changed
            conn.execute(text("""
                UPDATE upcoming_events
                SET event_name  = :name,
                    date_proper = :date,
                    location    = :loc,
                    is_numbered = :numbered,
                    scraped_at  = now()
                WHERE ufcstats_url = :url
            """), {
                'name':     event['event_name'],
                'date':     str(event['date_proper']) if event['date_proper'] else None,
                'loc':      event['location'],
                'numbered': event['is_numbered'],
                'url':      event['ufcstats_url'],
            })
            return row[0]

        event_id = self._new_id()
        conn.execute(text("""
            INSERT INTO upcoming_events
                (id, event_name, date_proper, location, ufcstats_url, is_numbered)
            VALUES
                (:id, :name, :date, :loc, :url, :numbered)
        """), {
            'id':       event_id,
            'name':     event['event_name'],
            'date':     str(event['date_proper']) if event['date_proper'] else None,
            'loc':      event['location'],
            'url':      event['ufcstats_url'],
            'numbered': event['is_numbered'],
        })
        logger.info(f'Inserted event: {event["event_name"]} ({event_id})')
        return event_id

    def _upsert_fight(self, conn, event_id: str, fight: dict, position: int = 0) -> str | None:
        """
        Upsert upcoming_fight row by (event_id, fighter_a_url, fighter_b_url).
        Returns the row's id.
        """
        row = conn.execute(text("""
            SELECT id FROM upcoming_fights
            WHERE event_id = :eid
              AND fighter_a_url = :url_a
              AND fighter_b_url = :url_b
        """), {
            'eid':   event_id,
            'url_a': fight['fighter_a_url'],
            'url_b': fight['fighter_b_url'],
        }).fetchone()

        if row:
            conn.execute(text("""
                UPDATE upcoming_fights
                SET weight_class    = :wc,
                    is_title_fight  = :title,
                    is_interim_title = :interim,
                    fighter_a_id    = :fa_id,
                    fighter_b_id    = :fb_id,
                    ufcstats_url    = :url,
                    position        = :pos,
                    scraped_at      = now()
                WHERE id = :id
            """), {
                'wc':      fight['weight_class'],
                'title':   fight['is_title_fight'],
                'interim': fight.get('is_interim_title', False),
                'fa_id':   fight.get('fighter_a_id'),
                'fb_id':   fight.get('fighter_b_id'),
                'url':     fight['ufcstats_url'],
                'pos':     position,
                'id':      row[0],
            })
            return row[0]

        fight_id = self._new_id()
        conn.execute(text("""
            INSERT INTO upcoming_fights
                (id, event_id, fighter_a_name, fighter_b_name,
                 fighter_a_id, fighter_b_id,
                 fighter_a_url, fighter_b_url,
                 weight_class, is_title_fight, is_interim_title, ufcstats_url, position)
            VALUES
                (:id, :eid, :fa_name, :fb_name,
                 :fa_id, :fb_id,
                 :fa_url, :fb_url,
                 :wc, :title, :interim, :url, :pos)
        """), {
            'id':      fight_id,
            'eid':     event_id,
            'fa_name': fight['fighter_a_name'],
            'fb_name': fight['fighter_b_name'],
            'fa_id':   fight.get('fighter_a_id'),
            'fb_id':   fight.get('fighter_b_id'),
            'fa_url':  fight['fighter_a_url'],
            'fb_url':  fight['fighter_b_url'],
            'wc':      fight['weight_class'],
            'title':   fight['is_title_fight'],
            'interim': fight.get('is_interim_title', False),
            'url':     fight['ufcstats_url'],
            'pos':     position,
        })
        logger.info(f'  Fight: {fight["fighter_a_name"]} vs {fight["fighter_b_name"]} ({fight_id})')
        return fight_id

    # ------------------------------------------------------------------
    # Main run
    # ------------------------------------------------------------------

    def run(self, dry_run: bool = False) -> bool:
        print('=' * 60)
        print('UFC UPCOMING SCRAPER')
        print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        if dry_run:
            print('[DRY RUN — no DB writes]')
        print('=' * 60)

        try:
            # Purge past events (and their fights/predictions) before scraping
            if not dry_run:
                with engine.connect() as conn:
                    result = conn.execute(text("""
                        DELETE FROM upcoming_predictions
                        WHERE fight_id IN (
                            SELECT uf.id FROM upcoming_fights uf
                            JOIN upcoming_events ue ON ue.id = uf.event_id
                            WHERE ue.date_proper < CURRENT_DATE
                        )
                    """))
                    preds_deleted = result.rowcount
                    result = conn.execute(text("""
                        DELETE FROM upcoming_fights
                        WHERE event_id IN (
                            SELECT id FROM upcoming_events WHERE date_proper < CURRENT_DATE
                        )
                    """))
                    fights_deleted = result.rowcount
                    result = conn.execute(text(
                        "DELETE FROM upcoming_events WHERE date_proper < CURRENT_DATE"
                    ))
                    events_deleted = result.rowcount
                    conn.commit()
                if events_deleted:
                    print(f'Purged {events_deleted} past event(s), {fights_deleted} fight(s), {preds_deleted} prediction(s)')

            events = self.scrape_upcoming_events()
            if not events:
                print('No upcoming events found.')
                return True

            total_fights = 0

            for event in events:
                print(f'\n>> {event["event_name"]}  |  {event["date_proper"]}  |  {event["location"]}')

                fights = self.scrape_event_fights(event['ufcstats_url'])

                # Resolve fighter IDs
                for fight in fights:
                    fight['fighter_a_id'] = self.resolve_fighter(
                        fight['fighter_a_url'], fight['fighter_a_name']
                    )
                    fight['fighter_b_id'] = self.resolve_fighter(
                        fight['fighter_b_url'], fight['fighter_b_name']
                    )
                    matched_a = 'OK' if fight['fighter_a_id'] else '--'
                    matched_b = 'OK' if fight['fighter_b_id'] else '--'
                    print(
                        f'  [{matched_a}] {fight["fighter_a_name"]} vs '
                        f'[{matched_b}] {fight["fighter_b_name"]}'
                        + (f'  ({fight["weight_class"]})' if fight['weight_class'] else '')
                        + (' [INTERIM TITLE]' if fight.get('is_interim_title') else ' [TITLE]' if fight['is_title_fight'] else '')
                    )

                if dry_run:
                    total_fights += len(fights)
                    continue

                with engine.connect() as conn:
                    event_id = self._upsert_event(conn, event)
                    live_fight_ids = []
                    for position, fight in enumerate(fights):
                        fid = self._upsert_fight(conn, event_id, fight, position)
                        live_fight_ids.append(fid)

                    # Remove fights that were pulled from the card since last scrape
                    if live_fight_ids:
                        placeholders = ','.join(f"'{fid}'" for fid in live_fight_ids)
                        removed = conn.execute(text(f"""
                            DELETE FROM upcoming_predictions
                            WHERE fight_id IN (
                                SELECT id FROM upcoming_fights
                                WHERE event_id = :eid
                                  AND id NOT IN ({placeholders})
                            )
                        """), {'eid': event_id})
                        stale = conn.execute(text(f"""
                            DELETE FROM upcoming_fights
                            WHERE event_id = :eid
                              AND id NOT IN ({placeholders})
                        """), {'eid': event_id})
                        if stale.rowcount:
                            print(f'  Removed {stale.rowcount} stale fight(s) no longer on the card')

                    conn.commit()

                total_fights += len(fights)

            print('\n' + '=' * 60)
            print(f'Done — {len(events)} events, {total_fights} fights')
            if dry_run:
                print('[DRY RUN — nothing written to DB]')
            print(f'Finished: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
            print('=' * 60)
            return True

        except Exception as e:
            logger.error(f'Scraper failed: {e}', exc_info=True)
            print(f'\nERROR: {e}')
            return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Scrape upcoming UFC events into DB')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print scraped data without writing to DB')
    args = parser.parse_args()

    scraper = UpcomingScraper()
    success = scraper.run(dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
