# UFC Analytics Platform — Sanity Check Ground Truths

Run these checks against Supabase after any major data overhaul (bulk reloads, FK re-population,
schema migrations). Add new cases whenever you discover an interesting edge case.

---

## Quick Reference: How to Compute a Fighter's UFC Record

**CRITICAL — the correct query pattern:**

```sql
-- Replace :fighter_id with the actual VARCHAR(8) id
SELECT
    COUNT(*) FILTER (WHERE fr.fighter_id  = :fighter_id AND fr.is_winner = TRUE)       AS wins,
    COUNT(*) FILTER (WHERE fr.opponent_id = :fighter_id AND fr.is_winner = TRUE)       AS losses,
    COUNT(*) FILTER (WHERE (fr.fighter_id = :fighter_id OR fr.opponent_id = :fighter_id)
                      AND fr."OUTCOME" = 'D/D')                                        AS draws,
    COUNT(*) FILTER (WHERE (fr.fighter_id = :fighter_id OR fr.opponent_id = :fighter_id)
                      AND fr."OUTCOME" = 'NC/NC')                                      AS nc
FROM fight_results fr;
```

**Why this works:**
- `fighter_id` is ALWAYS the winner (or fighter_a for NC/Draw).
- `opponent_id` is ALWAYS the loser (or fighter_b for NC/Draw).
- Wins  → rows where this fighter is `fighter_id` AND `is_winner = TRUE`.
- Losses → rows where this fighter is `opponent_id` AND `is_winner = TRUE` (i.e. their opponent won).
- Draws/NC → check both columns for `"OUTCOME"` = `'D/D'` or `'NC/NC'`.

**Common mistake:** checking `is_winner = FALSE` on `fighter_id` to find losses — this returns
NC/Draw rows, not losses.

---

## Part 1 — Fighter Record Ground Truths

These records are verified against the live Supabase data as of 2025-12.
Columns: **W – L – D – NC** (UFC fights only).

| Fighter | Expected Record | Notes |
|---------|----------------|-------|
| Khabib Nurmagomedov | 13 – 0 – 0 – 0 | Undefeated, retired champion |
| Conor McGregor | 10 – 4 – 0 – 0 | Includes Poirier trilogy |
| Jon Jones | 22 – 1 – 0 – 1 | 1 loss = DQ vs Hamill; 1 NC = Cormier 2 overturned |
| Petr Yan | 12 – 4 – 0 – 0 | All 4 losses post-2021 |
| Georges St-Pierre | 20 – 2 – 0 – 0 | Two-division champion (if MW title fight is included) |
| Anderson Silva | 17 – 7 – 0 – 1 | 1 NC = Sonnen 2 (PED) |
| Amanda Nunes | 15 – 2 – 0 – 0 | Two-division champion |
| Demetrious Johnson | 15 – 3 – 1 – 0 | 1 draw = Dodson 1 (majority draw) |

### How to look up a fighter's id

```sql
SELECT id, "FIRST", "LAST"
FROM fighter_details
WHERE "LAST" ILIKE 'nurmagomedov';
-- Then use that id in the record query above
```

### Python validation script

```python
"""
Run from backend/ directory: python -m scraper.validate_sanity_checks
(or just paste into a Python shell)
"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db.database import engine
from sqlalchemy import text

GROUND_TRUTHS = [
    # (last_name_search, expected_W, expected_L, expected_D, expected_NC)
    ("nurmagomedov", 13, 0, 0, 0),
    ("mcgregor",     10, 4, 0, 0),
    ("jones",        22, 1, 0, 1),   # Jon Jones — may need to filter by first name
    ("yan",          12, 4, 0, 0),   # Petr Yan
    ("st-pierre",    20, 2, 0, 0),
    ("silva",        17, 7, 0, 1),   # Anderson Silva — may need to filter by first name
    ("nunes",        15, 2, 0, 0),
    ("johnson",      15, 3, 1, 0),   # Demetrious Johnson — may need to filter by first name
]

RECORD_SQL = """
    SELECT
        COUNT(*) FILTER (WHERE fr.fighter_id  = :fid AND fr.is_winner = TRUE)      AS wins,
        COUNT(*) FILTER (WHERE fr.opponent_id = :fid AND fr.is_winner = TRUE)      AS losses,
        COUNT(*) FILTER (WHERE (fr.fighter_id = :fid OR fr.opponent_id = :fid)
                          AND fr."OUTCOME" = 'D/D')                                AS draws,
        COUNT(*) FILTER (WHERE (fr.fighter_id = :fid OR fr.opponent_id = :fid)
                          AND fr."OUTCOME" = 'NC/NC')                              AS nc
    FROM fight_results fr
"""

with engine.connect() as conn:
    passed = 0
    failed = 0
    for last_name, exp_w, exp_l, exp_d, exp_nc in GROUND_TRUTHS:
        # Look up fighter id
        fighters = conn.execute(text(
            'SELECT id, "FIRST", "LAST" FROM fighter_details WHERE "LAST" ILIKE :name'
        ), {"name": last_name}).fetchall()

        if not fighters:
            print(f"  MISSING  {last_name} — not found in fighter_details")
            failed += 1
            continue

        for fid, first, last in fighters:
            row = conn.execute(text(RECORD_SQL), {"fid": fid}).fetchone()
            w, l, d, nc = row
            ok = (w == exp_w and l == exp_l and d == exp_d and nc == exp_nc)
            status = "  PASS" if ok else "  FAIL"
            if ok:
                passed += 1
            else:
                failed += 1
            print(f"{status}  {first} {last}: "
                  f"got {w}W-{l}L-{d}D-{nc}NC  "
                  f"expected {exp_w}W-{exp_l}L-{exp_d}D-{exp_nc}NC")

    print(f"\n{'='*50}")
    print(f"  {passed} passed  /  {failed} failed")
```

---

## Part 2 — Fight-Level Spot Checks (BOUT / OUTCOME / fighter_a_id / fighter_b_id)

These verify that `populate_fighter_fks.py` and `populate_result_fks.py` produced correct
foreign keys for specific well-known fights.

**What to check per fight:**
1. `fight_details."BOUT"` matches the expected string exactly.
2. `fighter_a_id` and `fighter_b_id` resolve to the correct fighters.
3. `fight_results."OUTCOME"` is correct (`W/L` or `L/W`).
4. `fight_results.fighter_id` resolves to the actual winner.
5. `fight_results.opponent_id` resolves to the actual loser.

### Spot-check query template

```sql
-- Swap in the relevant BOUT substring
SELECT
    fd.id            AS fight_id,
    fd."BOUT",
    fa."FIRST" || ' ' || fa."LAST" AS fighter_a,
    fb."FIRST" || ' ' || fb."LAST" AS fighter_b,
    fr."OUTCOME",
    fw."FIRST" || ' ' || fw."LAST" AS winner,
    fo."FIRST" || ' ' || fo."LAST" AS loser,
    fr.is_winner
FROM fight_details fd
JOIN fight_results  fr ON fr.fight_id    = fd.id
JOIN fighter_details fa ON fa.id         = fd.fighter_a_id
JOIN fighter_details fb ON fb.id         = fd.fighter_b_id
JOIN fighter_details fw ON fw.id         = fr.fighter_id
JOIN fighter_details fo ON fo.id         = fr.opponent_id
WHERE fd."BOUT" LIKE '%<name_a>%' AND fd."BOUT" LIKE '%<name_b>%'
ORDER BY ev.date_proper DESC
LIMIT 5;
-- Add JOIN event_details ev ON ev.id = fd.event_id if you want to filter by year
```

### Known fights to spot-check

| BOUT (expected substring) | OUTCOME | Winner | Loser | Notes |
|--------------------------|---------|--------|-------|-------|
| McGregor vs. Khabib | L/W | Khabib | McGregor | UFC 229, Oct 2018, Sub R4 |
| McGregor vs. Poirier (2021-01) | L/W | Poirier | McGregor | UFC 257, KO R2 |
| McGregor vs. Poirier (2021-07) | L/W | Poirier | McGregor | UFC 264, TKO R1 (doctor) |
| McGregor vs. Poirier (2014) | W/L | McGregor | Poirier | UFC 178, KO R1 |
| Jones vs. Hamill | L/W | Hamill (DQ) | Jones | Jones DQ'd, only L on record |
| Nunes vs. Rousey | W/L | Nunes | Rousey | UFC 207, KO R1 |
| Silva vs. Weidman (2013) | L/W | Weidman | Silva | UFC 162, KO R2 |
| Johnson vs. Dodson (2012) | D/D | — | — | Majority draw — verify is_winner=FALSE for both |
| Cormier vs. Jones 2 (NC) | NC/NC | — | — | Jones tested positive — verify "OUTCOME"='NC/NC' |

### Verifying a draw or NC

```sql
-- Dodson vs Johnson majority draw
SELECT fr."BOUT", fr."OUTCOME", fr.is_winner,
       fa."FIRST" || ' ' || fa."LAST" AS fighter_a,
       fb."FIRST" || ' ' || fb."LAST" AS fighter_b
FROM fight_results fr
JOIN fight_details fd ON fd.id = fr.fight_id
JOIN fighter_details fa ON fa.id = fd.fighter_a_id
JOIN fighter_details fb ON fb.id = fd.fighter_b_id
WHERE fr."BOUT" LIKE '%Dodson%' AND fr."BOUT" LIKE '%Johnson%'
  AND fr."OUTCOME" = 'D/D';
-- Expected: is_winner = FALSE, fighter_a = whoever was listed first in BOUT
```

---

## Part 3 — FK Coverage Checks

Quick counts to verify FK population completeness. Run after any bulk reload.

```sql
-- fight_details: both fighter IDs populated
SELECT
    COUNT(*)                                                           AS total_fight_details,
    COUNT(fighter_a_id)                                                AS has_fighter_a,
    COUNT(fighter_b_id)                                                AS has_fighter_b,
    COUNT(*) FILTER (WHERE fighter_a_id IS NOT NULL
                       AND fighter_b_id IS NOT NULL)                   AS both_populated,
    ROUND(100.0 * COUNT(fighter_a_id) / NULLIF(COUNT(*), 0), 2)       AS pct_a
FROM fight_details
WHERE "BOUT" NOT LIKE '%win vs.%'      -- exclude placeholder rows
  AND "BOUT" NOT LIKE '%draw vs.%';

-- fight_results: fighter_id / opponent_id / is_winner populated
SELECT
    COUNT(*)                                                           AS total_fight_results,
    COUNT(fighter_id)                                                  AS has_fighter_id,
    COUNT(opponent_id)                                                 AS has_opponent_id,
    ROUND(100.0 * COUNT(fighter_id) / NULLIF(COUNT(*), 0), 2)         AS pct_populated
FROM fight_results;

-- event_id coverage across all tables
SELECT 'fight_details'  AS tbl, COUNT(*) total, COUNT(event_id) populated FROM fight_details
UNION ALL
SELECT 'fight_results',          COUNT(*), COUNT(event_id) FROM fight_results
UNION ALL
SELECT 'fight_stats',            COUNT(*), COUNT(event_id) FROM fight_stats;

-- fight_stats: fight_id coverage
SELECT COUNT(*) total, COUNT(fight_id) populated,
       ROUND(100.0 * COUNT(fight_id) / NULLIF(COUNT(*), 0), 2) AS pct
FROM fight_stats;
```

**Expected thresholds (as of 2025-12 baseline):**
| Check | Minimum Acceptable |
|-------|-------------------|
| fight_details both FKs | ≥ 99.5% of real bouts |
| fight_results fighter_id | 100% |
| fight_results opponent_id | 100% |
| event_id across all tables | 100% |
| fight_stats fight_id | ≥ 64% (known gap pre-2015) |

---

## Part 4 — Edge Cases to Watch

| Scenario | Why It's Tricky | How to Check |
|----------|----------------|--------------|
| Single-name fighters | `"FIRST"` is NULL in fighter_details; lookup uses `"LAST"` only | Check `WHERE "FIRST" IS NULL` in fighter_details |
| Placeholder BOUT rows | `"BOUT"` = `'win vs. '` or `'draw vs. '` — no real fighters | `WHERE "BOUT" LIKE '%win vs.%'` — should have NULL fighter_a_id |
| Jones DQ vs Hamill | `OUTCOME` = `'L/W'` even though Jones was listed first | Verify Jones is fighter_a, OUTCOME='L/W', Hamill is winner |
| Jones/Cormier 2 NC | `OUTCOME` = `'NC/NC'`, is_winner = FALSE for both | fighter_id=Jones (fighter_a), opponent_id=Cormier (fighter_b) |
| METHOD trailing spaces | `"METHOD"` has trailing space: `'KO/TKO '` not `'KO/TKO'` | `SELECT DISTINCT "METHOD" FROM fight_results` — should be trimmed after Phase 2 cleaning |
| Duplicate fighter names | Two fighters with same name → wrong ID assigned | Check `unresolved_fighter_names.log` after each FK population run |

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12 | Initial file created. Fighter records verified against Supabase after Task 3.1 + 3.2 completion. |
