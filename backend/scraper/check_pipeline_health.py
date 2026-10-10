"""check_pipeline_health.py - Fail when the weekly pipeline has silently stopped
preserving predictions.

Runs daily from the keepalive workflow and in every pipeline check. It reads
the database only.

The failure it exists for: the Post-Scrape ETL failed validation on 2026-09-27
and 2026-10-04, which skipped the pre-fight prediction archive both weeks. No
one noticed, and the Sep 26 card's pre-fight predictions were deleted before
anything archived them.

A card is unhealthy when its event finished at least ARCHIVE_DEADLINE_DAYS ago,
it still has predictions waiting in upcoming_predictions, and none of its fights
were archived - the archive has not run for it at all. A card where most fights
archived and one did not is a bout cancelled on the night or an identity
mismatch; that is reported as a warning, not a failure, because no pipeline is
broken.

Usage:
    cd backend && python scraper/check_pipeline_health.py
Exit code 1 when any card is unhealthy.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text

from db.database import engine

# The Saturday event is archived by the Sunday pipeline, so by Monday every
# fight with a result should be archived.
ARCHIVE_DEADLINE_DAYS = 2


def main() -> int:
    with engine.connect() as conn:
        cards = conn.execute(text("""
            SELECT ue.event_name,
                   ue.date_proper,
                   -- Counted from the archive itself. The Saturday purge deletes
                   -- a card's archived fights from the upcoming tables, so on
                   -- 2026-10-10 UFC 332 read as 0 archived of 1 and failed,
                   -- although 10 of its 11 predictions were archived.
                   (SELECT COUNT(*) FROM past_predictions pp
                    WHERE pp.prediction_source = 'pre_fight_archive'
                      AND pp.event_date = ue.date_proper)        AS archived,
                   COUNT(*) FILTER (WHERE uf.archived IS NOT TRUE) AS waiting
            FROM upcoming_events ue
            JOIN upcoming_fights uf      ON uf.event_id = ue.id
            JOIN upcoming_predictions up ON up.fight_id = uf.id
            WHERE ue.date_proper <= CURRENT_DATE - :deadline
            GROUP BY ue.event_name, ue.date_proper
            HAVING COUNT(*) FILTER (WHERE uf.archived IS NOT TRUE) > 0
            ORDER BY ue.date_proper
        """), {"deadline": ARCHIVE_DEADLINE_DAYS}).fetchall()

    failed = [c for c in cards if c.archived == 0]
    for c in cards:
        if c.archived:
            print(f"WARN  {c.event_name} ({c.date_proper}): {c.waiting} prediction(s) "
                  f"not archived alongside {c.archived} archived - cancelled bout or identity mismatch")
    for c in failed:
        print(f"FAIL  {c.event_name} ({c.date_proper}): {c.waiting} prediction(s) and none archived - "
              f"the prediction archive has not run for this card")

    if failed:
        print(f"\nUnhealthy: {len(failed)} card(s) not archived. Check the Post-Scrape ETL runs, then run "
              f"python backend/scraper/archive_completed_predictions.py")
        return 1
    print("Healthy: every finished card with predictions has been archived")
    return 0


if __name__ == "__main__":
    sys.exit(main())
