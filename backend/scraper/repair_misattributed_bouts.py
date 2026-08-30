"""
repair_misattributed_bouts.py — reassign bouts filed under the wrong fighter

Seven names in fighter_details belong to two genuinely different athletes each
(two UFC Bruno Silvas, two Mike Davises, and so on). FK resolution keyed on
names and kept whichever row came back first, so one of each pair inherited the
other's entire career. Bruno Silva's row holds a flyweight's twelve bouts and a
middleweight's eleven; Michael McDonald's nine bantamweight bouts sit on a
light heavyweight who has exactly one UFC fight.

Ownership is decided against UFCStats itself, not inferred. Each fighter page
lists its own bouts with a data-link to the fight page, and fight_details."URL"
holds that same URL, so a bout is matched to its owner by exact URL equality.
No name matching is involved anywhere in this script - name matching is the
defect being repaired.

A bout whose URL appears on both pages, or neither, is reported and left alone.

DRY RUN BY DEFAULT. Nothing is written without --apply.

Usage:
    python backend/scraper/repair_misattributed_bouts.py                # plan
    python backend/scraper/repair_misattributed_bouts.py --apply        # execute
    python backend/scraper/repair_misattributed_bouts.py --refresh      # re-scrape
"""

import sys
import os
import json
import argparse
import logging

from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

CACHE = os.path.join(os.path.dirname(__file__), "reports",
                     "misattribution_ownership.json")

# The seven names shared by two different athletes. Both ids of each pair are
# real people who must keep their own careers; these are NEVER merged.
PAIRS = [
    ("bruno silva",       "294aa73dbf37d281", "12ebd7d157e91701"),
    ("jean silva",        "9211aae062b799d6", "52ef95b5860fb28c"),
    ("joey gomez",        "0778f94eb5d588a5", "3a28e1e641366308"),
    ("michael mcdonald",  "d52ef694108f8235", "d0314416a7f26527"),
    ("mike davis",        "c8661e204c66f325", "fb3e61720be4690c"),
    ("tony johnson",      "3641a0d117e9bc6c", "a45bab49951a45cd"),
    ("victor valenzuela", "de277a4abcfeea46", "078695e385ec2f57"),
]


def fetch_ownership(refresh=False):
    """Return {fighter_id: [fight_url, ...]} straight from UFCStats.

    UFCStats sits behind a JS challenge, so this uses Playwright exactly as the
    live scraper does. Results are cached because the answer is historical and
    does not change between runs.
    """
    if os.path.exists(CACHE) and not refresh:
        with open(CACHE, encoding="utf-8") as f:
            log.info(f"  Using cached ownership from {CACHE}")
            return json.load(f)

    from playwright.sync_api import sync_playwright
    from bs4 import BeautifulSoup

    ownership = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for _, *slugs in PAIRS:
            for slug in slugs:
                url = f"http://ufcstats.com/fighter-details/{slug}"
                page.goto(url, wait_until="networkidle", timeout=45000)
                soup = BeautifulSoup(page.content(), "html.parser")
                links = [tr.get("data-link")
                         for tr in soup.select("tr.b-fight-details__table-row")
                         if tr.get("data-link")]
                ownership[slug[:8]] = sorted(set(links))
                log.info(f"  {slug[:8]}  {len(links)} fight(s) listed on UFCStats")
        browser.close()

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(ownership, f, indent=1)
    return ownership


def build_corrections(conn, ownership):
    """Work out which bout is on the wrong fighter.

    Returns (corrections, unmatched) where a correction is
    (fight_id, bout, wrong_id, right_id).
    """
    corrections, unmatched = [], []

    for name, slug_a, slug_b in PAIRS:
        a, b = slug_a[:8], slug_b[:8]
        owns = {a: set(ownership.get(a, [])), b: set(ownership.get(b, []))}

        rows = conn.execute(text("""
            SELECT id, "BOUT", "URL", fighter_a_id, fighter_b_id
            FROM fight_details
            WHERE fighter_a_id IN (:a, :b) OR fighter_b_id IN (:a, :b)
        """), {"a": a, "b": b}).fetchall()

        for fight_id, bout, url, fa, fb in rows:
            held = a if a in (fa, fb) else b
            on_a, on_b = url in owns[a], url in owns[b]
            if on_a == on_b:
                # Listed by both pages or by neither. Either way UFCStats does
                # not settle it, so leave it exactly as it is.
                unmatched.append((fight_id, bout, held,
                                  "on both pages" if on_a else "on neither page"))
                continue
            truth = a if on_a else b
            if truth != held:
                corrections.append((fight_id, bout, held, truth))

    return corrections, unmatched


def apply_corrections(conn, corrections):
    """Swap identity on one bout at a time, preserving winner/loser roles."""
    for fight_id, bout, wrong, right in corrections:
        # fight_details: whichever side holds the wrong id.
        for col in ("fighter_a_id", "fighter_b_id"):
            conn.execute(text(f"""
                UPDATE fight_details SET {col} = :right
                WHERE id = :fid AND {col} = :wrong
            """), {"right": right, "wrong": wrong, "fid": fight_id})

        # fight_results: fighter_id is the winner and opponent_id the loser.
        # Only the identity changes, never which column the fighter sits in,
        # so the result of the bout is untouched.
        for col in ("fighter_id", "opponent_id"):
            conn.execute(text(f"""
                UPDATE fight_results SET {col} = :right
                WHERE fight_id = :fid AND {col} = :wrong
            """), {"right": right, "wrong": wrong, "fid": fight_id})

        conn.execute(text("""
            UPDATE fight_stats SET fighter_id = :right
            WHERE fight_id = :fid AND fighter_id = :wrong
        """), {"right": right, "wrong": wrong, "fid": fight_id})

        for col in ("fighter_a_id", "fighter_b_id"):
            conn.execute(text(f"""
                UPDATE past_predictions SET {col} = :right
                WHERE fight_id = :fid AND {col} = :wrong
            """), {"right": right, "wrong": wrong, "fid": fight_id})

        log.info(f"  {bout[:52]:<52} {wrong} -> {right}")


def verify(conn, ownership):
    """Every fighter must now own exactly the bouts UFCStats says they own."""
    problems = []
    for name, slug_a, slug_b in PAIRS:
        for slug in (slug_a, slug_b):
            fid = slug[:8]
            # What UFCStats lists, restricted to bouts we actually hold.
            expected = conn.execute(text("""
                SELECT COUNT(*) FROM fight_details WHERE "URL" = ANY(:urls)
            """), {"urls": ownership.get(fid, []) or [""]}).scalar()
            actual = conn.execute(text("""
                SELECT COUNT(*) FROM fight_details
                WHERE fighter_a_id = :i OR fighter_b_id = :i
            """), {"i": fid}).scalar()
            if expected != actual:
                problems.append(
                    f"{name} {fid}: owns {actual} bout(s), UFCStats lists "
                    f"{expected} of them in our data")

    # Identity swaps must never leave a bout with one fighter on both sides.
    selfies = conn.execute(text("""
        SELECT COUNT(*) FROM fight_details
        WHERE fighter_a_id IS NOT NULL AND fighter_a_id = fighter_b_id
    """)).scalar()
    if selfies:
        problems.append(f"{selfies} bout(s) have one fighter on both sides")

    # fight_results must still agree with fight_details on who fought.
    mismatch = conn.execute(text("""
        SELECT COUNT(*) FROM fight_results fr
        JOIN fight_details fd ON fd.id = fr.fight_id
        WHERE fr.fighter_id IS NOT NULL AND fr.opponent_id IS NOT NULL
          AND fd.fighter_a_id IS NOT NULL AND fd.fighter_b_id IS NOT NULL
          AND ARRAY[fr.fighter_id, fr.opponent_id]::text[]
              <> ARRAY[fd.fighter_a_id, fd.fighter_b_id]::text[]
          AND ARRAY[fr.opponent_id, fr.fighter_id]::text[]
              <> ARRAY[fd.fighter_a_id, fd.fighter_b_id]::text[]
    """)).scalar()
    if mismatch:
        problems.append(
            f"{mismatch} fight_results row(s) disagree with fight_details "
            f"about who fought")

    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="execute the repair (default is a dry run)")
    ap.add_argument("--refresh", action="store_true",
                    help="re-scrape UFCStats instead of using the cache")
    args = ap.parse_args()

    ownership = fetch_ownership(refresh=args.refresh)

    with engine.begin() as conn:
        corrections, unmatched = build_corrections(conn, ownership)

        log.info("")
        log.info("=" * 78)
        log.info("  REPAIR PLAN")
        log.info("=" * 78)

        if unmatched:
            log.warning(f"\n  {len(unmatched)} bout(s) UFCStats does not settle, "
                        f"left untouched:")
            for fight_id, bout, held, why in unmatched:
                log.warning(f"    {fight_id}  {bout[:44]:<44} held by {held}  ({why})")

        if not corrections:
            log.info("\n  No misattributed bouts found. Nothing to do.")
            return 0

        log.info(f"\n  {len(corrections)} bout(s) to reassign:\n")
        for fight_id, bout, wrong, right in corrections:
            log.info(f"    {bout[:52]:<52} {wrong} -> {right}")

        if not args.apply:
            log.info("\n  DRY RUN — nothing written. Re-run with --apply.")
            return 0

        log.info("\n" + "=" * 78)
        log.info("  APPLYING")
        log.info("=" * 78)
        apply_corrections(conn, corrections)

        problems = verify(conn, ownership)
        if problems:
            log.error("\n  VERIFICATION FAILED — rolling back:")
            for p in problems:
                log.error(f"    {p}")
            raise RuntimeError("repair verification failed; rolled back")

        log.info("\n  Verification passed. Committing.")

    log.info("  Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
