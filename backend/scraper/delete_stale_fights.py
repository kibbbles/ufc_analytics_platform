"""scraper/delete_stale_fights.py — Delete stale upcoming fights and their predictions.

One-off cleanup: removes fights that were replaced/cancelled in the Adesanya/Pyfer card.

Fight IDs to delete:
  O19U7J — Tybura vs Valter Walker  (replaced by Tyrell Fortune)
  ZFKU1A — Zhu Kangjie vs Marcio Barbosa  (cancelled / not on UFCStats)
  JI0HLS — Michael Chiesa vs Carlston Harris  (replaced by Niko Price)

Uses the Supabase REST API (PostgREST) to avoid the free-tier statement timeout
that kills raw psycopg2 DELETE statements against large JSONB rows.

Run from the backend/ directory:
    python scraper/delete_stale_fights.py
    python scraper/delete_stale_fights.py --dry-run
"""

from __future__ import annotations

import argparse
import sys

import requests

sys.path.insert(0, ".")
from core.config import settings

STALE_FIGHT_IDS = ["O19U7J", "ZFKU1A", "JI0HLS"]


class SupabaseRest:
    def __init__(self, url: str, key: str) -> None:
        self.base = url.rstrip("/") + "/rest/v1"
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def select(self, table: str, **filters) -> list[dict]:
        params = {k: f"eq.{v}" for k, v in filters.items()}
        r = requests.get(f"{self.base}/{table}", headers=self.headers, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def delete(self, table: str, **filters) -> list[dict]:
        params = {k: f"eq.{v}" for k, v in filters.items()}
        r = requests.delete(f"{self.base}/{table}", headers=self.headers, params=params, timeout=30)
        r.raise_for_status()
        return r.json() if r.text else []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SupabaseRest(settings.supabase_url, settings.supabase_anon_key)

    for fight_id in STALE_FIGHT_IDS:
        rows = db.select("upcoming_fights", id=fight_id)
        if not rows:
            print(f"[SKIP] {fight_id} — not found")
            continue
        row = rows[0]
        print(f"[DELETE] {fight_id} — {row['fighter_a_name']} vs {row['fighter_b_name']}")

        if args.dry_run:
            continue

        # Delete child (prediction) first
        deleted_preds = db.delete("upcoming_predictions", fight_id=fight_id)
        print(f"         predictions deleted: {len(deleted_preds)}")

        # Delete the fight
        deleted_fights = db.delete("upcoming_fights", id=fight_id)
        print(f"         fight deleted: {len(deleted_fights)}")

    if args.dry_run:
        print("\n[dry-run] no changes made")
    else:
        print("\nDone.")


if __name__ == "__main__":
    main()
