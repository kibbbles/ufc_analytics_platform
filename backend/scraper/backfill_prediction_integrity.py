"""
backfill_prediction_integrity.py - flag archived predictions written after the start

Fills section_start_at, prediction_after_start, odds_after_start and
odds_scraped_at (migration 011) for every live pre-fight prediction archived
before the freeze existed. Nothing is deleted: a flagged row stays in
past_predictions and drops out of scored_predictions, which every scorecard,
ROI and Vegas figure reads.

The values come from reports/prediction_integrity_audit.json, not from a fresh
lookup. The odds verdicts rest on GitHub Actions job logs, which expire, so the
audit file is the lasting record. See its "method" field for how each verdict
was reached and each row's "odds_evidence" for the run that proves it.

Each row is checked against the database before anything is written: the
fight, event date and pre-fight timestamp must match the audit exactly, or the
script stops without writing.

DRY RUN BY DEFAULT. Nothing is written without --apply.

Usage:
    python backend/scraper/backfill_prediction_integrity.py           # plan
    python backend/scraper/backfill_prediction_integrity.py --apply   # execute
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

AUDIT = os.path.join(os.path.dirname(__file__), "reports", "prediction_integrity_audit.json")


def _ts(value):
    return datetime.fromisoformat(value) if value else None


def load_audit(path=AUDIT):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["rows"]


def check_against_db(conn, rows):
    """Return a list of mismatches between the audit and the live rows."""
    live = {
        r["id"]: r for r in conn.execute(text("""
            SELECT id, event_date, fighter_a_name, fighter_b_name,
                   pre_fight_predicted_at, odds_a, odds_b
            FROM past_predictions
            WHERE id = ANY(:ids) AND prediction_source = 'pre_fight_archive'
        """), {"ids": [r["id"] for r in rows]}).mappings()
    }
    problems = []
    for r in rows:
        db = live.get(r["id"])
        if db is None:
            problems.append(f"{r['id']}: not found as a pre_fight_archive row")
            continue
        if str(db["event_date"]) != r["event_date"]:
            problems.append(f"{r['id']}: event date {db['event_date']} != audit {r['event_date']}")
        if f"{db['fighter_a_name']} vs {db['fighter_b_name']}" != r["bout"]:
            problems.append(f"{r['id']}: bout changed since the audit")
        if db["pre_fight_predicted_at"] != _ts(r["pre_fight_predicted_at"]):
            problems.append(f"{r['id']}: pre-fight timestamp changed since the audit")
        if [db["odds_a"], db["odds_b"]] != r["odds"]:
            problems.append(f"{r['id']}: odds changed since the audit")
    return problems


def apply(conn, rows):
    for r in rows:
        conn.execute(text("""
            UPDATE past_predictions
            SET section_start_at       = :section_start_at,
                prediction_after_start = :prediction_after_start,
                odds_after_start       = :odds_after_start,
                odds_scraped_at        = COALESCE(odds_scraped_at, :odds_scraped_at)
            WHERE id = :id
        """), {
            "id": r["id"],
            "section_start_at": _ts(r["section_start_at"]),
            "prediction_after_start": r["prediction_after_start"],
            "odds_after_start": r["odds_after_start"],
            "odds_scraped_at": _ts(r["odds_scraped_at"]),
        })


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the flags (default is a dry run)")
    args = ap.parse_args()

    rows = load_audit()
    late_pred = [r for r in rows if r["prediction_after_start"]]
    late_odds = [r for r in rows if r["odds_after_start"] is True]
    unknown = [r for r in rows if r["odds"][0] is not None and r["odds_after_start"] is None]
    log.info(f"{len(rows)} audited rows: {len(late_pred)} predictions written after the start, "
             f"{len(late_odds)} odds written after the start, {len(unknown)} odds with unknown capture time")
    for r in late_pred:
        log.info(f"  prediction  {r['event_date']}  {r['bout']}  (section {r['section_start_at'][11:16]}Z, "
                 f"written {r['pre_fight_predicted_at'][:16]})")
    for r in late_odds:
        log.info(f"  odds        {r['event_date']}  {r['bout']}  {r['odds']}  ({r['odds_evidence']})")

    with engine.begin() as conn:
        problems = check_against_db(conn, rows)
        if problems:
            for p in problems:
                log.error(p)
            log.error(f"{len(problems)} row(s) differ from the audit. Nothing written.")
            sys.exit(1)
        if not args.apply:
            log.info("Dry run: every row matches the audit. Re-run with --apply to write.")
            return
        apply(conn, rows)
    log.info(f"Wrote flags for {len(rows)} rows. Refresh the betting views next:")
    log.info("    python backend/scraper/post_scrape_clean.py --phase 5")


if __name__ == "__main__":
    main()
