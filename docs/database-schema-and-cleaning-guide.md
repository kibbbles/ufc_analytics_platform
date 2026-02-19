# UFC Analytics Platform — Database Schema & Data Preparation Guide

This document is the authoritative reference for the Supabase database schema and the
step-by-step plan to get data clean and ready for ML and analysis. Tackle Phase 1 before
Phase 2. Do not skip to type-parsing until every row that should exist actually exists.

---

## What Are fighter_a_id and fighter_b_id?

Every fight in `fight_details` stores the matchup as a raw text string in `BOUT`, e.g.:

```
"Conor McGregor vs. Dustin Poirier"
```

"Fighter A" is simply the first name listed (left of "vs.") and "Fighter B" is the second.
The labels carry no meaning — A is not the winner, not the favourite, just the left side.

`fighter_a_id` and `fighter_b_id` are supposed to be foreign keys into `fighter_details`
so you can JOIN a fight directly to each fighter's profile, physical stats, and other fights.
Right now they are **100% NULL** — the parsing was never run. Without them, linking any fight
to a fighter requires an unreliable name-string match, which is fragile and slow.

The same problem exists in `fight_results` (`fighter_id`, `opponent_id`, `is_winner`) and
`fight_stats` (`fighter_id`). Until these FK columns are populated, the tables are largely
isolated islands connected only by text.

---

## Schema Reference

### event_details — 761 rows

| Column        | Type         | Nullable | Notes                                                  |
|---------------|--------------|----------|--------------------------------------------------------|
| `id`          | VARCHAR(8)   | NO       | PK. 8-char hex for Greko CSV rows; 6-char alphanum for live scraper rows |
| `EVENT`       | TEXT         | YES      | Event name, e.g. "UFC 300: Pereira vs. Hill"          |
| `URL`         | TEXT         | YES      | UFCStats.com event URL                                 |
| `DATE`        | TEXT         | YES      | Raw text. Greko format: "March 11, 1994". Live scraper: "2026-02-07" |
| `LOCATION`    | TEXT         | YES      | City, State/Province, Country                          |
| `date_proper` | DATE         | YES      | Parsed date. **Now 100% populated (1994-03-11 to 2026-02-07)** |

**FK outbound:** None
**FK inbound:** `fight_details.event_id`, `fight_results.event_id`, `fight_stats.event_id`

---

### fighter_details — 4,449 rows

| Column     | Type       | Nullable | Notes                                                      |
|------------|------------|----------|------------------------------------------------------------|
| `id`       | VARCHAR(8) | NO       | PK                                                         |
| `FIRST`    | TEXT       | YES      | First name. NULL for 16 single-name fighters (Mongolian/Chinese) |
| `LAST`     | TEXT       | YES      | Last name                                                  |
| `NICKNAME` | TEXT       | YES      | NULL for 1,982 fighters (44.6%) — expected                |
| `URL`      | TEXT       | YES      | UFCStats.com fighter profile URL                           |

**FK outbound:** None
**FK inbound:** `fighter_tott.fighter_id`, `fight_details.fighter_a_id`, `fight_details.fighter_b_id`, `fight_results.fighter_id`, `fight_results.opponent_id`, `fight_stats.fighter_id`

---

### fighter_tott — 4,449 rows

Tale of the Tape — physical profile for each fighter. One row per fighter.

| Column      | Type        | Nullable | Notes                                                         |
|-------------|-------------|----------|---------------------------------------------------------------|
| `id`        | VARCHAR(8)  | NO       | PK                                                            |
| `FIGHTER`   | TEXT        | YES      | Full name string                                              |
| `HEIGHT`    | TEXT        | YES      | Format: `"5' 11\""`. Missing stored as `"--"` (348 rows, 7.8%) |
| `WEIGHT`    | TEXT        | YES      | Format: `"155 lbs"`. Missing stored as `"--"` (86 rows, 1.9%) |
| `REACH`     | TEXT        | YES      | Format: `"70\""`. Missing stored as `"--"` (1,970 rows, 44.3%) |
| `STANCE`    | TEXT        | YES      | Orthodox / Southpaw / Switch / Open Stance / Sideways. NULL for 865 rows (19.4%) |
| `DOB`       | TEXT        | YES      | Format: `"Aug 24, 1972"`. Missing stored as `"--"` (762 rows, 17.1%) |
| `URL`       | TEXT        | YES      | UFCStats.com fighter profile URL                              |
| `fighter_id`| VARCHAR(8)  | YES      | FK → fighter_details. **99.75% populated (11 unmatched)**    |
| `tott_data` | JSONB       | YES      | Raw JSON blob (redundant with individual columns)             |
| `slpm`      | NUMERIC     | YES      | Sig. strikes landed per minute — **100% NULL, never scraped** |
| `str_acc`   | VARCHAR(10) | YES      | Striking accuracy % — **100% NULL, never scraped**           |
| `sapm`      | NUMERIC     | YES      | Sig. strikes absorbed per minute — **100% NULL, never scraped** |
| `str_def`   | VARCHAR(10) | YES      | Striking defence % — **100% NULL, never scraped**            |
| `td_avg`    | NUMERIC     | YES      | Takedown avg per 15 min — **100% NULL, never scraped**       |
| `td_acc`    | VARCHAR(10) | YES      | Takedown accuracy % — **100% NULL, never scraped**           |
| `td_def`    | VARCHAR(10) | YES      | Takedown defence % — **100% NULL, never scraped**            |
| `sub_avg`   | NUMERIC     | YES      | Submission attempts per 15 min — **100% NULL, never scraped** |

**FK outbound:** `fighter_id` → `fighter_details.id`

---

### fight_details — 8,533 rows

One row per fight. Acts as the central hub between events and per-fight data.

| Column        | Type       | Nullable | Notes                                                        |
|---------------|------------|----------|--------------------------------------------------------------|
| `id`          | VARCHAR(8) | NO       | PK                                                           |
| `EVENT`       | TEXT       | YES      | Event name (redundant with join to event_details)            |
| `BOUT`        | TEXT       | YES      | `"Fighter A vs. Fighter B"`. 52 rows have `"win vs. "` (placeholder) |
| `URL`         | TEXT       | YES      | UFCStats.com fight URL                                       |
| `event_id`    | VARCHAR(8) | YES      | FK → event_details. **100% populated**                       |
| `fighter_a_id`| VARCHAR(8) | YES      | FK → fighter_details (first name in BOUT). **100% NULL**     |
| `fighter_b_id`| VARCHAR(8) | YES      | FK → fighter_details (second name in BOUT). **100% NULL**    |

**FK outbound:** `event_id` → `event_details.id`
**FK inbound:** `fight_results.fight_id`, `fight_stats.fight_id`

---

### fight_results — 8,482 rows

One row per fight with outcome data. 51 fewer rows than fight_details (placeholder rows from newest live-scraped events have no result yet).

| Column        | Type       | Nullable | Notes                                                              |
|---------------|------------|----------|--------------------------------------------------------------------|
| `id`          | VARCHAR(8) | NO       | PK                                                                 |
| `EVENT`       | TEXT       | YES      | Event name (redundant)                                             |
| `BOUT`        | TEXT       | YES      | `"Fighter A vs. Fighter B"`                                        |
| `OUTCOME`     | TEXT       | YES      | `"W/L"` (fighter A won), `"L/W"` (fighter B won), `"NC/NC"`, `"D/D"` |
| `WEIGHTCLASS` | TEXT       | YES      | Weight class string. 110 distinct values — many are TUF/RTUF tournament labels |
| `METHOD`      | TEXT       | YES      | **Has trailing space on every value** (e.g., `"KO/TKO "`). Values: KO/TKO, Submission, Decision - Unanimous, Decision - Split, Decision - Majority, TKO - Doctor's Stoppage, Overturned, Could Not Continue, DQ, Other |
| `ROUND`       | BIGINT     | YES      | Round the fight ended. 1–5                                         |
| `TIME`        | TEXT       | YES      | Time within round, e.g. `"2:34"`                                   |
| `TIME FORMAT` | TEXT       | YES      | Round structure, e.g. `"3 Rnd (5-5-5)"`                           |
| `REFEREE`     | TEXT       | YES      | NULL for 26 rows                                                   |
| `DETAILS`     | TEXT       | YES      | Submission type or KO details. NULL for 78 rows                    |
| `URL`         | TEXT       | YES      |                                                                    |
| `event_id`    | VARCHAR(8) | YES      | FK → event_details. **100% populated**                             |
| `fight_id`    | VARCHAR(8) | YES      | FK → fight_details. **100% populated**                             |
| `fighter_id`  | VARCHAR(6) | YES      | FK → fighter_details (winner). **100% NULL**                       |
| `opponent_id` | VARCHAR(6) | YES      | FK → fighter_details (loser). **100% NULL**                        |
| `is_winner`   | BOOLEAN    | YES      | **100% NULL**                                                      |
| `result_data` | JSONB      | YES      | Raw JSON blob (redundant with individual columns)                  |

**FK outbound:** `event_id` → `event_details.id`, `fight_id` → `fight_details.id`

---

### fight_stats — 39,912 rows

Per-fighter, per-round statistics. Two rows per round per fight (one per fighter).
Reliable full-card coverage starts ~2010. Data exists back to 1994 but is very sparse pre-2006.

| Column       | Type       | Nullable | Notes                                                               |
|--------------|------------|----------|---------------------------------------------------------------------|
| `id`         | VARCHAR(8) | NO       | PK                                                                  |
| `EVENT`      | TEXT       | YES      | Event name (redundant)                                              |
| `BOUT`       | TEXT       | YES      | `"Fighter A vs. Fighter B"` (redundant)                             |
| `ROUND`      | TEXT       | YES      | `"Round 1"` through `"Round 5"`. NULL for 42 rows (blank scraper rows) |
| `FIGHTER`    | TEXT       | YES      | Fighter name — text only, no FK. NULL for 42 rows                   |
| `KD`         | TEXT       | YES      | Knockdowns. Integer stored as text                                  |
| `SIG.STR.`   | TEXT       | YES      | `"X of Y"` — significant strikes landed of attempted               |
| `SIG.STR.%`  | TEXT       | YES      | `"0%"`–`"100%"` or `"---"` (204 rows where 0 attempted)            |
| `TOTAL STR.` | TEXT       | YES      | `"X of Y"` — total strikes                                         |
| `TD`         | TEXT       | YES      | `"X of Y"` — takedowns landed of attempted                         |
| `TD%`        | TEXT       | YES      | `"0%"`–`"100%"` or `"---"` (**18,550 rows = 46.5%** where 0 attempted) |
| `SUB.ATT`    | TEXT       | YES      | Submission attempts. Integer stored as text                         |
| `REV.`       | TEXT       | YES      | Reversals. Integer stored as text                                   |
| `CTRL`       | TEXT       | YES      | Control time `"MM:SS"`. `"--"` for 432 rows                        |
| `HEAD`       | TEXT       | YES      | `"X of Y"` — head strikes                                          |
| `BODY`       | TEXT       | YES      | `"X of Y"` — body strikes                                          |
| `LEG`        | TEXT       | YES      | `"X of Y"` — leg strikes                                           |
| `DISTANCE`   | TEXT       | YES      | `"X of Y"` — strikes at distance                                   |
| `CLINCH`     | TEXT       | YES      | `"X of Y"` — strikes in clinch                                     |
| `GROUND`     | TEXT       | YES      | `"X of Y"` — strikes on the ground                                 |
| `event_id`   | VARCHAR(8) | YES      | FK → event_details. **100% populated**                              |
| `fight_id`   | VARCHAR(8) | YES      | FK → fight_details. **100% populated**                              |
| `fighter_id` | VARCHAR(6) | YES      | FK → fighter_details. **100% NULL**                                 |

**FK outbound:** `event_id` → `event_details.id`, `fight_id` → `fight_details.id`

---

## Entity Relationship Map

```
event_details (761)
    │
    ├── fight_details (8,533)   ← event_id ✅
    │       │
    │       ├── fight_results (8,482)  ← fight_id ✅, event_id ✅
    │       │       fighter_id ❌  opponent_id ❌  is_winner ❌
    │       │
    │       └── fight_stats (39,912)   ← fight_id ✅, event_id ✅
    │               fighter_id ❌
    │
    fighter_details (4,449)
            │
            └── fighter_tott (4,449)  ← fighter_id ✅ (99.75%)
                    slpm/str_acc/sapm/str_def/td_avg/td_acc/td_def/sub_avg ❌
```

---

## Data Preparation TODOs

Work top-down. Phase 1 must be complete before Phase 2. Phase 2 before building features.

Legend: **[ONE-OFF]** = run once on historical data | **[ONGOING]** = must run after every scrape via GitHub Actions

---

### Phase 1 — Data Completeness (make sure the rows are there)

> FK columns are the foundation. Nothing can be joined cleanly until these are populated.

- [ ] **[ONE-OFF]** Parse `fight_details.BOUT` ("Fighter A vs. Fighter B") and resolve each
  name against `fighter_details` (FIRST + LAST) to populate `fighter_a_id` and `fighter_b_id`.
  Use fuzzy matching (e.g. `rapidfuzz`) as a fallback for name discrepancies. Log any
  unresolved names for manual review.

- [ ] **[ONE-OFF]** Using the now-populated `fight_details.fighter_a_id/b_id` and the
  `fight_results.OUTCOME` ("W/L" or "L/W"), populate `fight_results.fighter_id` (winner),
  `fight_results.opponent_id` (loser), and `fight_results.is_winner = TRUE/FALSE`. This
  gives you a clean per-fighter win/loss record joinable by ID.

- [ ] **[ONE-OFF]** Populate `fight_stats.fighter_id` by matching the `FIGHTER` name column
  to `fighter_details` (FIRST + LAST). Same fuzzy-match approach as above.

- [ ] **[ONE-OFF]** Scrape the 8 career stat columns in `fighter_tott` from each fighter's
  UFCStats profile page. These are already on the page but were never scraped:
  `slpm`, `str_acc`, `sapm`, `str_def`, `td_avg`, `td_acc`, `td_def`, `sub_avg`.
  Use `bulk_scrape_physical_stats.py` as a reference — same pattern, different fields.

- [ ] **[ONE-OFF]** Fix the 52 placeholder `fight_details` rows where `BOUT = "win vs. "`.
  These belong to the two newest live-scraped events. Either scrape the real bout data or
  delete these rows if the fights have not yet occurred.

- [ ] **[ONE-OFF]** Investigate the 11 `fighter_tott` rows where `fighter_id IS NULL`
  (fighters in tott with no match in fighter_details). Either match them manually or note
  they are unclaimed profiles.

- [ ] **[ONGOING]** After each `live_scraper.py` run, execute a post-scrape FK resolution
  step that runs the same name-match logic on any newly inserted rows in `fight_details`,
  `fight_results`, and `fight_stats`.

---

### Phase 2 — Data Quality (formats, nulls, cleaning)

> Do this after Phase 1 so you're cleaning a complete dataset, not a partial one.

- [ ] **[ONE-OFF + ONGOING]** Replace all `"--"` and `"---"` values with `NULL` across:
  - `fighter_tott`: `HEIGHT`, `WEIGHT`, `REACH`, `DOB` (stored as "--" for missing)
  - `fight_stats`: `CTRL`, `SIG.STR.%`, `TD%` ("---" for zero-attempt calculations)
  - Any other text column where "--" means "no data"

- [ ] **[ONE-OFF + ONGOING]** Strip trailing spaces from `fight_results.METHOD`.
  Every value currently has a trailing space (e.g., `"KO/TKO "`). Apply `TRIM()` or
  a one-time UPDATE.

- [ ] **[ONE-OFF + ONGOING]** Standardise `fight_results.WEIGHTCLASS`. The 110 distinct
  values include many one-off TUF/Road to UFC tournament labels. Create a mapping to
  canonical weight classes (Strawweight, Flyweight, Bantamweight, Featherweight,
  Lightweight, Welterweight, Middleweight, Light Heavyweight, Heavyweight, Women's
  variants, Catch Weight, Open Weight) and store in a new `weight_class_clean` column
  or a lookup table.

- [ ] **[ONE-OFF]** Parse `"X of Y"` text columns in `fight_stats` into integer pairs.
  Add columns to the table (or a cleaned view/table):
  - `sig_str_landed`, `sig_str_attempted` (from `SIG.STR.`)
  - `total_str_landed`, `total_str_attempted` (from `TOTAL STR.`)
  - `td_landed`, `td_attempted` (from `TD`)
  - `head_landed`, `head_attempted`, `body_landed`, `body_attempted`
  - `leg_landed`, `leg_attempted`, `distance_landed`, `distance_attempted`
  - `clinch_landed`, `clinch_attempted`, `ground_landed`, `ground_attempted`

- [ ] **[ONE-OFF]** Parse `fight_stats.CTRL` (`"MM:SS"`) into `ctrl_seconds` (integer).
  NULL where original is NULL or "--".

- [ ] **[ONE-OFF]** Parse `fighter_tott` physical attributes into numeric columns:
  - `HEIGHT` → `height_inches` (FLOAT) e.g. `"5' 11\""` → `71.0`
  - `WEIGHT` → `weight_lbs` (FLOAT) e.g. `"155 lbs"` → `155.0`
  - `REACH` → `reach_inches` (FLOAT) e.g. `"70\""` → `70.0`
  - `DOB` → `dob_date` (DATE) e.g. `"Aug 24, 1972"` → `1972-08-24`

- [ ] **[ONE-OFF]** Parse `fight_results.TIME` (`"MM:SS"`) into `time_seconds` (integer)
  for computing fight duration.

- [ ] **[ONE-OFF]** Delete or flag the 42 NULL-ROUND / NULL-FIGHTER rows in `fight_stats`
  (blank header rows inserted by the scraper).

---

### Phase 3 — Additional Data to Add

> Add these while the cleaning pipeline is open. They are high-value for ML and analysis.

- [ ] **[ONE-OFF + ONGOING]** Add `is_title_fight` boolean to `fight_results`.
  Can be inferred from `WEIGHTCLASS` containing "Title" or "Championship".
  Alternatively scrape directly — UFCStats labels title fights on event pages.

- [ ] **[ONE-OFF + ONGOING]** Add `fight_bonus` column to `fight_results`.
  Values: `NULL`, `"FOTN"` (Fight of the Night), `"POTN"` (Performance of the Night),
  `"SOTN"` (Submission of the Night), `"KOTN"` (KO of the Night).
  UFCStats event pages list bonus winners. This is a useful target/feature variable.

- [ ] **[ONE-OFF + ONGOING]** Add `total_fight_time_seconds` to `fight_results`.
  Computable from `ROUND` and `TIME`: `(ROUND - 1) * 300 + time_seconds`.

- [ ] **[ONGOING]** Consider adding a `fighter_record_at_fight` snapshot table or columns
  (`wins`, `losses`, `draws`, `nc` at the time of each fight). This is derivable from
  fight history order but useful to pre-compute for ML features.

---

### Phase 4 — GitHub Actions Automation (keeping future data clean)

> Every task marked [ONGOING] above needs to be wired into a post-scrape pipeline.

- [ ] Create `backend/scraper/post_scrape_clean.py` — a single script that runs all
  ongoing cleaning steps on newly inserted rows only (filter by rows where FK columns
  are NULL or inserted_at > last run timestamp):
  1. FK resolution for new fight_details, fight_results, fight_stats rows
  2. "--" → NULL replacement on new rows
  3. METHOD trailing space strip on new rows
  4. Parsed integer columns for new fight_stats rows
  5. `is_title_fight` flag on new fight_results rows

- [ ] Add a step to `.github/workflows/weekly-ufc-scraper.yml` that runs
  `post_scrape_clean.py` immediately after `live_scraper.py` succeeds:
  ```yaml
  - name: Run post-scrape cleaning
    run: |
      cd backend/scraper
      python post_scrape_clean.py
  ```

- [ ] Add logging to `post_scrape_clean.py` so GitHub Actions artifacts capture
  how many rows were cleaned each run.

---

## One-Off vs Ongoing Summary

| Task                                      | Type        | Blocker for ML? |
|-------------------------------------------|-------------|-----------------|
| Populate fighter_a_id / fighter_b_id      | ONE-OFF     | YES — critical  |
| Populate fight_results fighter/winner FKs | ONE-OFF     | YES — critical  |
| Populate fight_stats fighter_id           | ONE-OFF     | YES — critical  |
| Scrape fighter_tott career stats          | ONE-OFF     | High value      |
| Fix 52 placeholder BOUT rows              | ONE-OFF     | Low             |
| Investigate 11 unmatched fighter_tott     | ONE-OFF     | Low             |
| "--" / "---" → NULL                       | ONE-OFF + ONGOING | YES        |
| Strip METHOD trailing spaces              | ONE-OFF + ONGOING | YES        |
| Normalise WEIGHTCLASS                     | ONE-OFF + ONGOING | Medium      |
| Parse "X of Y" → integer columns         | ONE-OFF     | YES — for ML    |
| Parse CTRL → ctrl_seconds                 | ONE-OFF     | YES — for ML    |
| Parse physical attrs → numeric            | ONE-OFF     | YES — for ML    |
| Add is_title_fight                        | ONE-OFF + ONGOING | Medium      |
| Add fight_bonus                           | ONE-OFF + ONGOING | Medium      |
| Add total_fight_time_seconds              | ONE-OFF     | Low             |
| post_scrape_clean.py + GitHub Actions     | ONGOING     | Future proofing |
