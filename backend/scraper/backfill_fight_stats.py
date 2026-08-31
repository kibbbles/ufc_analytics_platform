"""
backfill_fight_stats.py — recover round-by-round stats for events that have none

UFCStats moved per-round data into extra <tbody> elements around May 2026. The
parser read only the first <tbody>, which is now an empty shell, so it returned
nothing and logged it at INFO. Thirteen consecutive events were ingested with
zero fight_stats rows while every workflow reported success.

live_scraper.py now reads the current shape. This script re-visits the fights on
events that were ingested during the broken window and writes their stats.

It only touches events that have fights but no stats at all, so it cannot
duplicate rows for events that were ingested correctly, and re-running it after
a successful pass finds nothing to do.

The typed columns (sig_str_landed, ctrl_seconds and the rest) and the fight_stats
foreign keys are populated by the ETL, not here. Run post_scrape_clean.py
afterwards.

DRY RUN BY DEFAULT. Nothing is written without --apply.

Usage:
    python backend/scraper/backfill_fight_stats.py                  # plan
    python backend/scraper/backfill_fight_stats.py --apply          # execute
    python backend/scraper/backfill_fight_stats.py --apply --limit 1  # one event
"""

import sys
import os
import argparse
import logging

from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db.database import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("backfill_fight_stats")


def find_gaps(conn, limit=None):
    """Events that have fights recorded but no round stats at all."""
    rows = conn.execute(text("""
        SELECT e.id, e."EVENT", e.date_proper,
               (SELECT COUNT(*) FROM fight_results fr WHERE fr.event_id = e.id) AS fights
        FROM event_details e
        WHERE (SELECT COUNT(*) FROM fight_results fr WHERE fr.event_id = e.id) > 0
          AND (SELECT COUNT(*) FROM fight_stats  fs WHERE fs.event_id = e.id) = 0
        ORDER BY e.date_proper DESC
    """)).fetchall()
    return rows[:limit] if limit else rows


def fights_for(conn, event_id):
    """Every fight on an event that we can visit, in card order."""
    return conn.execute(text("""
        SELECT fd.id, fd."BOUT", fd."URL"
        FROM fight_details fd
        WHERE fd.event_id = :eid AND fd."URL" IS NOT NULL
        ORDER BY fd.position NULLS LAST, fd.id
    """), {"eid": event_id}).fetchall()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="write the stats (default is a dry run)")
    ap.add_argument("--limit", type=int, default=None,
                    help="only process this many events, newest first")
    args = ap.parse_args()

    with engine.connect() as conn:
        gaps = find_gaps(conn, args.limit)
        plan = [(e, name, d, n, fights_for(conn, e)) for e, name, d, n in gaps]

    log.info("=" * 78)
    log.info("  BACKFILL PLAN")
    log.info("=" * 78)
    if not plan:
        log.info("  No events are missing round stats. Nothing to do.")
        return 0

    total_fights = sum(len(f) for *_, f in plan)
    for eid, name, d, n, fights in plan:
        log.info(f"  {d}  {name[:46]:<46} fights={n:<3} visitable={len(fights)}")
    log.info(f"\n  {len(plan)} event(s), {total_fights} fight page(s) to visit")

    if not args.apply:
        log.info("\n  DRY RUN — nothing written. Re-run with --apply.")
        return 0

    # Imported here so a dry run needs neither Playwright nor a browser.
    from live_scraper import LiveUFCScraper

    scraper = LiveUFCScraper()
    scraper.load_existing_ids()
    written = failed = 0
    try:
        for eid, name, d, n, fights in plan:
            log.info(f"\n  {name}  ({d})")
            for fight_id, bout, url in fights:
                detail = scraper.scrape_fight_detail_stats(url)
                rounds = detail.get("round_stats") or []
                if not rounds:
                    # Old events legitimately have no recorded stats. Anything
                    # recent reaching this branch means the page moved again.
                    log.warning(f"    no stats parsed: {bout[:50]}")
                    failed += 1
                    continue
                scraper.store_fight_stats(eid, name, fight_id, bout, rounds)
                written += len(rounds)
                log.info(f"    {len(rounds):>2} rows  {bout[:52]}")
    finally:
        scraper._close()

    log.info("")
    log.info("=" * 78)
    log.info(f"  Wrote {written} fight_stats row(s); {failed} fight(s) yielded none")
    log.info("=" * 78)

    with engine.connect() as conn:
        remaining = len(find_gaps(conn))
    log.info(f"  Events still missing stats: {remaining}")
    log.info("  Now run: python backend/scraper/post_scrape_clean.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
