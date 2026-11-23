"""scraper/refresh_section_starts.py - store when each upcoming bout's card section starts.

compute_predictions.py and fetch_odds.py stop writing a fight once its section
starts (migration 011). This script gives them that time: it finds each
upcoming event in UFC.com's feed, matches the bouts by name, and stores
CardSegmentStartTime in upcoming_fights.section_start_at.

A bout it cannot match keeps the conservative fallback in
prediction_freeze_at(): 12:00 UTC on the day before the event. That only ever
freezes too early, never too late, so a lookup failure costs a refresh, not
integrity.

Exit status is 1 when an event in the next 7 days has no section start for any
bout, which means the feed lookup itself is broken. Single unmatched bouts are
listed as warnings; they are usually late card changes.

Run from backend/:
    python scraper/refresh_section_starts.py
    python scraper/refresh_section_starts.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

import requests
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.database import engine
from scraper import ufc_live_feed as feed

logger = logging.getLogger(__name__)

LOOKAHEAD_DAYS = 14   # events further out rarely have a final card or start time
MUST_RESOLVE_DAYS = 7


def run(dry_run: bool = False) -> bool:
    session = requests.Session()
    today = datetime.now(timezone.utc).date()   # the database's CURRENT_DATE is UTC too
    slugs: list[str] | None = None
    broken: list[str] = []

    with engine.connect() as conn:
        events = conn.execute(text("""
            SELECT id, event_name, date_proper, ufc_event_fmid
            FROM upcoming_events
            WHERE date_proper BETWEEN CURRENT_DATE - 1 AND CURRENT_DATE + :ahead
            ORDER BY date_proper
        """), {'ahead': LOOKAHEAD_DAYS}).mappings().all()
        known = {e['ufc_event_fmid'] for e in events if e['ufc_event_fmid']}

        for ev in events:
            name, when = ev['event_name'], ev['date_proper']
            must = (when - today).days <= MUST_RESOLVE_DAYS
            label = f'{name} ({when})'
            try:
                fmid = ev['ufc_event_fmid']
                if fmid is None:
                    if slugs is None:
                        slugs = feed.list_event_slugs(session)
                    fmid = feed.find_event_fmid(name, when, session, slugs, exclude=known)
                    if fmid is None:
                        raise feed.FeedError('no unique UFC.com event page matches')
                    known.add(fmid)
                    if not dry_run:
                        conn.execute(text('UPDATE upcoming_events SET ufc_event_fmid = :f WHERE id = :id'),
                                     {'f': fmid, 'id': ev['id']})
                feed_bouts = feed.bouts(feed.fetch_event(fmid, session))
            except feed.FeedError as e:
                print(f'  {label}: section starts unavailable - {e}')
                if must:
                    broken.append(label)
                continue

            ours = conn.execute(text("""
                SELECT id, fighter_a_name, fighter_b_name, section_start_at
                FROM upcoming_fights WHERE event_id = :eid
            """), {'eid': ev['id']}).mappings().all()

            matched, unmatched = 0, []
            for f in ours:
                b = feed.match_bout(f['fighter_a_name'] or '', f['fighter_b_name'] or '', feed_bouts)
                if b is None or b.segment_start is None:
                    unmatched.append(f"{f['fighter_a_name']} vs {f['fighter_b_name']}")
                    continue
                matched += 1
                if b.segment_start != f['section_start_at'] and not dry_run:
                    conn.execute(text('UPDATE upcoming_fights SET section_start_at = :s WHERE id = :id'),
                                 {'s': b.segment_start, 'id': f['id']})

            print(f'  {label}: UFC.com event {fmid}, section start known for {matched}/{len(ours)} bouts')
            for u in unmatched:
                print(f'::warning::No UFC.com section start for {u} ({name}); '
                      'it keeps the fallback freeze (12:00 UTC the day before)')
            if must and ours and matched == 0:
                broken.append(label)

        if not dry_run:
            conn.commit()

    if broken:
        for b in broken:
            print(f'::error::No section start times for {b}. Its predictions and odds freeze at the '
                  'fallback time (12:00 UTC the day before), so the fight-day refresh will not run.')
        return False
    return True


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true', help='look up start times without writing')
    args = parser.parse_args()
    sys.exit(0 if run(dry_run=args.dry_run) else 1)


if __name__ == '__main__':
    main()
