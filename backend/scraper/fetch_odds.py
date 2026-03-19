"""scraper/fetch_odds.py — Task 27.2: Fetch Vegas odds from The Odds API.

Fetches MMA moneyline odds, fuzzy-matches fighter names to upcoming_fights
rows, computes vig-normalised implied probabilities, and upserts the DB.

Run from the backend/ directory:
    python scraper/fetch_odds.py
    python scraper/fetch_odds.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

import requests
from rapidfuzz import fuzz
from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, ".")
from core.config import settings
from db.database import SessionLocal

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

API_URL = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"
API_PARAMS = {
    "regions": "us",
    "markets": "h2h",
    "oddsFormat": "american",
}

# Bookmaker preference order — most UFC coverage first
BOOKMAKER_PRIORITY = [
    "betonlineag",   # BetOnline.ag — best coverage (68/71 events)
    "draftkings",    # DraftKings
    "fanduel",       # FanDuel
    "betmgm",        # BetMGM
    "betrivers",     # BetRivers
    "bovada",        # Bovada
]

FUZZY_CUTOFF = 82   # WRatio score threshold for name matching

# ── Odds math ─────────────────────────────────────────────────────────────────

def american_to_implied(odds: int) -> float:
    """Convert American moneyline odds to raw implied probability."""
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)


def vig_normalize(imp_a: float, imp_b: float) -> tuple[float, float]:
    """Remove the bookmaker's overround — normalise to sum to 1.0."""
    total = imp_a + imp_b
    if total <= 0:
        return 0.5, 0.5
    return imp_a / total, imp_b / total


# ── API fetch ─────────────────────────────────────────────────────────────────

def fetch_api_events(api_key: str) -> list[dict]:
    """Call The Odds API and return the list of MMA events."""
    params = {**API_PARAMS, "apiKey": api_key}
    resp = requests.get(API_URL, params=params, timeout=15)
    resp.raise_for_status()
    remaining = resp.headers.get("x-requests-remaining", "?")
    used = resp.headers.get("x-requests-used", "?")
    logger.info("Odds API: used=%s remaining=%s", used, remaining)
    print(f"  Odds API: {used} requests used, {remaining} remaining this month")
    return resp.json()


def best_odds_from_event(event: dict) -> Optional[tuple[str, str, int, int]]:
    """
    Return (home_name, away_name, home_odds, away_odds) from the best
    available bookmaker, or None if no bookmaker has h2h odds.
    """
    bookmakers = event.get("bookmakers", [])
    # Build a lookup by bookmaker key
    bk_map = {bk["key"]: bk for bk in bookmakers}

    # Try preferred bookmakers first, then any available
    ordered = [bk_map[k] for k in BOOKMAKER_PRIORITY if k in bk_map]
    ordered += [bk for bk in bookmakers if bk["key"] not in BOOKMAKER_PRIORITY]

    for bk in ordered:
        for market in bk.get("markets", []):
            if market["key"] != "h2h":
                continue
            outcomes = market.get("outcomes", [])
            if len(outcomes) != 2:
                continue
            # Map name → price
            prices = {o["name"]: o["price"] for o in outcomes}
            home = event["home_team"]
            away = event["away_team"]
            if home in prices and away in prices:
                return home, away, int(prices[home]), int(prices[away])

    return None


# ── Fighter name matching ─────────────────────────────────────────────────────

def fuzzy_match(name: str, candidates: list[str], cutoff: int = FUZZY_CUTOFF) -> Optional[str]:
    """Return the best fuzzy match from candidates, or None if below cutoff."""
    best_score = 0
    best_match = None
    for candidate in candidates:
        score = fuzz.WRatio(name, candidate)
        if score > best_score:
            best_score = score
            best_match = candidate
    if best_score >= cutoff:
        return best_match
    return None


def match_fight_to_api(
    api_home: str,
    api_away: str,
    upcoming: list[dict],
) -> Optional[tuple[dict, bool]]:
    """
    Find the best matching upcoming fight for an API event.
    Returns (fight_row, flipped) where flipped=True means the API home
    corresponds to fighter_b in our DB (i.e. order is reversed).
    Returns None if no match found above the cutoff.
    """
    best_score = 0
    best_match = None
    best_flipped = False

    for fight in upcoming:
        a = fight["fighter_a_name"] or ""
        b = fight["fighter_b_name"] or ""

        # Try normal order: home→a, away→b
        score_normal = (fuzz.WRatio(api_home, a) + fuzz.WRatio(api_away, b)) / 2
        # Try flipped order: home→b, away→a
        score_flipped = (fuzz.WRatio(api_home, b) + fuzz.WRatio(api_away, a)) / 2

        if score_normal >= score_flipped and score_normal > best_score:
            best_score = score_normal
            best_match = fight
            best_flipped = False
        elif score_flipped > score_normal and score_flipped > best_score:
            best_score = score_flipped
            best_match = fight
            best_flipped = True

    if best_score >= FUZZY_CUTOFF:
        return best_match, best_flipped
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def run(dry_run: bool = False) -> None:
    api_key = settings.odds_api_key
    if not api_key:
        print("ERROR: ODDS_API_KEY not set in environment / .env")
        sys.exit(1)

    print("Fetching odds from The Odds API...")
    events = fetch_api_events(api_key)
    print(f"  {len(events)} MMA events returned")

    db: Session = SessionLocal()
    try:
        # Load all upcoming fights that still have a future event date
        rows = db.execute(text("""
            SELECT uf.id, uf.fighter_a_name, uf.fighter_b_name,
                   uf.odds_a, uf.odds_b, uf.odds_scraped_at,
                   ue.date_proper
            FROM upcoming_fights uf
            JOIN upcoming_events ue ON ue.id = uf.event_id
            WHERE ue.date_proper >= CURRENT_DATE
              AND uf.fighter_a_name IS NOT NULL
              AND uf.fighter_b_name IS NOT NULL
        """)).mappings().all()

        upcoming = [dict(r) for r in rows]
        print(f"  {len(upcoming)} upcoming fights in DB to match against")

        matched = 0
        updated = 0
        skipped_unchanged = 0
        unmatched_api = []

        for event in events:
            result = best_odds_from_event(event)
            if result is None:
                continue
            api_home, api_away, home_odds, away_odds = result

            match = match_fight_to_api(api_home, api_away, upcoming)
            if match is None:
                unmatched_api.append(f"{api_home} vs {api_away}")
                continue

            fight, flipped = match
            matched += 1

            # Assign odds correctly based on match orientation
            if flipped:
                # API home = our fighter_b, API away = our fighter_a
                odds_a, odds_b = away_odds, home_odds
            else:
                odds_a, odds_b = home_odds, away_odds

            # Check if odds have actually changed
            existing_a = fight["odds_a"]
            existing_b = fight["odds_b"]
            if existing_a == odds_a and existing_b == odds_b:
                skipped_unchanged += 1
                continue

            # Compute vig-normalised implied probs
            raw_a = american_to_implied(odds_a)
            raw_b = american_to_implied(odds_b)
            imp_a, imp_b = vig_normalize(raw_a, raw_b)

            print(
                f"  {'[DRY]' if dry_run else 'UPDATE'} "
                f"{fight['fighter_a_name']} ({odds_a:+d}) vs "
                f"{fight['fighter_b_name']} ({odds_b:+d})  "
                f"implied: {imp_a:.1%}/{imp_b:.1%}"
            )

            if not dry_run:
                db.execute(text("""
                    UPDATE upcoming_fights
                    SET odds_a          = :odds_a,
                        odds_b          = :odds_b,
                        implied_prob_a  = :imp_a,
                        implied_prob_b  = :imp_b,
                        odds_scraped_at = :scraped_at
                    WHERE id = :fight_id
                """), {
                    "odds_a":     odds_a,
                    "odds_b":     odds_b,
                    "imp_a":      imp_a,
                    "imp_b":      imp_b,
                    "scraped_at": datetime.now(timezone.utc),
                    "fight_id":   fight["id"],
                })
                updated += 1
            else:
                updated += 1

        if not dry_run:
            db.commit()

        print(f"\nSummary:")
        print(f"  API events with odds : {len(events)}")
        print(f"  Matched to DB fights : {matched}")
        print(f"  Updated              : {updated}")
        print(f"  Skipped (unchanged)  : {skipped_unchanged}")
        print(f"  Unmatched API events : {len(unmatched_api)}")
        if unmatched_api:
            print("  Unmatched:")
            for name in unmatched_api:
                print(f"    - {name}")

    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
