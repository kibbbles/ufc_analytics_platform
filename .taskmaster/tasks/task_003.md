# Task ID: 3

**Title:** ETL Pipeline for Historical Data

**Status:** done

**Dependencies:** 1 ✓, 2 ✓

**Priority:** high

**Description:** Transform and clean existing UFC data already in Supabase through 5 phases: FK resolution, quality cleanup, type parsing, new derived columns, and GitHub Actions automation. All work done in backend/scraper/ using raw sqlalchemy.text().

**Details:**

Work directly against existing Supabase tables. No JSON files, no Airflow, no Great Expectations. Five phases:

1. FK Resolution:
   - Parse BOUT strings in fight_details using rapidfuzz to match fighter names and populate fighter_a_id and fighter_b_id (currently 100% NULL)
   - Populate winner_id and loser_id FKs in fight_results using rapidfuzz name matching
   - Populate fighter_id FK in fight_stats (currently 100% NULL)
   - Scrape 8 career stat columns in fighter_tott that are missing

2. Quality Cleanup:
   - Replace '--' and '---' placeholder values with NULL across all relevant columns
   - Strip trailing spaces from METHOD column
   - Normalize WEIGHTCLASS values to a canonical set (e.g. 'Lightweight', 'Welterweight', etc.)

3. Type Parsing:
   - Parse 'X of Y' strike strings into integer pairs (landed, attempted)
   - Parse CTRL time strings (e.g. '2:34') into total seconds as integer
   - Parse physical attributes (height, weight, reach) from text to float values
   - Calculate total_fight_time_seconds from round and time columns

4. New Derived Columns:
   - Add is_title_fight BOOLEAN column derived from WEIGHTCLASS or bout context
   - Add fight_bonus STRING column for performance bonuses (POTN, FOTN, etc.)

5. GitHub Actions Automation:
   - Create backend/scraper/post_scrape_clean.py script that runs all cleanup phases
   - Wire into GitHub Actions workflow to run automatically after each scrape
   - Script must be idempotent (safe to rerun)

All database operations use raw sqlalchemy.text() queries. No ORM, no pandas required.

**Test Strategy:**

1. Unit test each parsing function (strike parsing, time parsing, physical attribute parsing) with edge cases and invalid inputs
2. Test rapidfuzz FK resolution with known fighter name variations and verify match accuracy
3. Verify quality cleanup replaces all '--'/'---' values and normalizes weightclass correctly
4. Test idempotency by running post_scrape_clean.py multiple times and verifying no data corruption
5. Validate FK resolution coverage (target: >95% of NULL FKs resolved)
6. Spot-check derived columns (is_title_fight, fight_bonus) against known fight records
7. Integration test the full post_scrape_clean.py script against a staging Supabase instance
8. Verify GitHub Actions workflow triggers correctly after scrape runs

## Subtasks

### 3.1. FK Resolution: Populate fighter_a_id and fighter_b_id in fight_details

**Status:** done  
**Dependencies:** None  

Use rapidfuzz to parse BOUT strings in the fight_details table and match fighter names against the fighters table to populate the currently NULL fighter_a_id and fighter_b_id foreign key columns.

**Details:**

1. Query all rows from fight_details where fighter_a_id IS NULL or fighter_b_id IS NULL.
2. For each row, parse the BOUT string (e.g. 'Fighter A vs. Fighter B') to extract two fighter name tokens.
3. Load all fighter names and IDs from the fighters table into memory.
4. Use rapidfuzz.process.extractOne with a score threshold (e.g. 85) to match each extracted name to a canonical fighter record.
5. Log any unmatched or low-confidence matches for manual review.
6. Execute UPDATE statements using sqlalchemy.text() to set fighter_a_id and fighter_b_id.
7. Wrap updates in transactions; rollback on error.
8. Acceptance criteria: fighter_a_id and fighter_b_id NULL rate reduced to <1% for parseable BOUT strings; all updates logged with match scores.
<info added on 2026-02-21T15:32:42.451Z>
COMPLETED. Script: backend/scraper/populate_fighter_fks.py. Results: 8,482/8,533 fight_details rows now have both fighter_a_id and fighter_b_id (99.4%). 16,961 exact matches, 3 fuzzy matches (score_cutoff=88, WRatio). 51 unresolved rows are all scraper placeholder rows ('win vs. ' / 'draw vs. ') â€” not real fights. Real fight coverage is 100%. rapidfuzz 3.14.3 installed. Unresolved names logged to backend/scraper/unresolved_fighter_names.log.
</info added on 2026-02-21T15:32:42.451Z>

### 3.2. FK Resolution: Populate winner_id and loser_id in fight_results

**Status:** done  
**Dependencies:** None  

Use rapidfuzz name matching to resolve winner and loser names in fight_results to fighter IDs and populate the winner_id and loser_id foreign key columns.

**Details:**

1. Query all fight_results rows where winner_id IS NULL or loser_id IS NULL.
2. Extract winner and loser name strings from existing text columns.
3. Load fighters table into memory (id, name).
4. Apply rapidfuzz.process.extractOne with threshold 85 to match each name.
5. For ambiguous matches (score between 75-85), log for manual review rather than auto-updating.
6. Execute batch UPDATE statements via sqlalchemy.text() to set winner_id and loser_id.
7. Verify referential integrity after updates.
8. Acceptance criteria: winner_id and loser_id populated for all rows with parseable name data; match confidence scores stored in a log file.
<info added on 2026-02-21T16:46:34.352Z>
COMPLETED. Script: backend/scraper/populate_result_fks.py. Results: 8,482/8,482 rows populated (100%). Breakdown: W/L: 5,369 rows, L/W: 2,963 rows, NC/Draw: 150 rows. is_winner=TRUE set for decisive results, FALSE for NC/Draw outcomes. Schema fix required prior to population: fight_results.fighter_id and opponent_id columns were VARCHAR(6) and widened to VARCHAR(8) to match Greko IDs; fight_stats.fighter_id also widened to VARCHAR(8).
</info added on 2026-02-21T16:46:34.352Z>

### 3.3. FK Resolution: Populate fighter_id in fight_stats and scrape missing fighter_tott columns

**Status:** done  
**Dependencies:** None  

Resolve the fighter_id FK in fight_stats (currently 100% NULL) using rapidfuzz matching, and scrape the 8 missing career stat columns in fighter_tott from UFCStats.com.

**Details:**

1. For fight_stats FK resolution: query rows where fighter_id IS NULL, extract fighter name text, match against fighters table using rapidfuzz, and UPDATE via sqlalchemy.text().
2. For fighter_tott: identify the 8 missing career stat columns (e.g. sig_str_landed_per_min, sig_str_absorbed_per_min, takedown_avg, submission_avg, sig_str_defense, takedown_defense, knockdown_avg, avg_fight_time).
3. Scrape each fighter's stats page on UFCStats.com using requests/BeautifulSoup.
4. Parse the 8 stat values and INSERT/UPDATE into fighter_tott using sqlalchemy.text().
5. Implement rate limiting (1 req/sec) and retry logic.
6. Acceptance criteria: fight_stats.fighter_id NULL rate <1%; all 8 fighter_tott columns populated for fighters with UFCStats profiles.

### 3.4. Quality Cleanup: Replace placeholder values, strip whitespace, and normalize WEIGHTCLASS

**Status:** done  
**Dependencies:** None  

Perform data quality cleanup across all relevant tables: replace '--' and '---' with NULL, strip trailing spaces from METHOD, and normalize WEIGHTCLASS to a canonical set of values.

**Details:**

1. Identify all columns across fight_details, fight_results, fight_stats, and fighter_tott that contain '--' or '---' placeholder strings.
2. Generate and execute UPDATE statements using sqlalchemy.text() to SET col = NULL WHERE col IN ('--', '---') for each identified column.
3. Strip trailing (and leading) spaces from the METHOD column in fight_results: UPDATE fight_results SET method = TRIM(method).
4. Define canonical WEIGHTCLASS values: ['Heavyweight', 'Light Heavyweight', 'Middleweight', 'Welterweight', 'Lightweight', 'Featherweight', 'Bantamweight', 'Flyweight', "Women's Strawweight", "Women's Flyweight", "Women's Bantamweight", "Women's Featherweight", 'Catch Weight', 'Open Weight'].
5. Build a mapping of known variants to canonical values and apply via UPDATE.
6. Log any unmapped WEIGHTCLASS values for manual review.
7. Acceptance criteria: zero '--'/'---' values remain; METHOD has no trailing spaces; WEIGHTCLASS values match canonical set or are NULL.

### 3.5. Type Parsing: Parse strike strings, CTRL time, physical attributes, and fight time

**Status:** done  
**Dependencies:** None  

Implement parsing functions to convert text-encoded numeric data into proper integer/float types: 'X of Y' strike strings, CTRL time strings, physical attributes, and total fight time seconds.

**Details:**

1. Strike parsing: write parse_strikes(val) -> (int, int) that splits 'X of Y' into (landed, attempted); handle NULL/invalid input gracefully.
2. Apply to all strike columns in fight_stats, adding paired _landed and _attempted integer columns via ALTER TABLE and UPDATE using sqlalchemy.text().
3. CTRL time parsing: write parse_ctrl_time(val) -> int that converts 'M:SS' to total seconds; UPDATE ctrl_time_seconds column.
4. Physical attributes: write parse_height(val) -> float (cm), parse_weight(val) -> float (lbs), parse_reach(val) -> float (inches) for fighters table; UPDATE height_cm, weight_lbs, reach_inches.
5. Fight time: calculate total_fight_time_seconds from round number and time-in-round columns using formula: (round-1)*300 + parse_ctrl_time(time); UPDATE fight_results.
6. All operations use sqlalchemy.text(); functions are unit-testable in isolation.
7. Acceptance criteria: all parsed columns contain correct integer/float values; original text columns preserved; edge cases (NULL, '--', malformed) return NULL without crashing.

### 3.6. New Derived Columns: Add is_title_fight BOOLEAN and fight_bonus STRING

**Status:** done  
**Dependencies:** None  

Add and populate two new derived columns: is_title_fight (BOOLEAN) derived from WEIGHTCLASS or bout context, and fight_bonus (STRING) for performance bonuses like POTN and FOTN.

**Details:**

1. Add is_title_fight column: ALTER TABLE fight_results ADD COLUMN IF NOT EXISTS is_title_fight BOOLEAN DEFAULT FALSE using sqlalchemy.text().
2. Derive is_title_fight by checking if WEIGHTCLASS contains 'Title' or if BOUT string contains 'Championship'/'Title'; UPDATE accordingly.
3. Add fight_bonus column: ALTER TABLE fight_results ADD COLUMN IF NOT EXISTS fight_bonus VARCHAR(50).
4. Parse bonus indicators from available text fields; map to canonical values: 'POTN' (Performance of the Night), 'FOTN' (Fight of the Night), 'KOTN' (KO of the Night), 'SOTN' (Submission of the Night).
5. A fight may have multiple bonuses; store as comma-separated string or use the primary bonus.
6. All DDL and DML via sqlalchemy.text().
7. Acceptance criteria: is_title_fight correctly set for known title fights (spot-check 20 records); fight_bonus populated for events known to award bonuses; columns are idempotent on re-run (IF NOT EXISTS guards).

### 3.7. Unit Tests for All Parsing and Matching Functions

**Status:** done  
**Dependencies:** None  

Write comprehensive unit tests for all parsing functions (strike, time, physical attributes, fight time) and rapidfuzz FK resolution logic with edge cases and invalid inputs.

**Details:**

1. Create backend/scraper/tests/test_parsers.py covering:
   - parse_strikes: valid 'X of Y', '0 of 0', NULL, '--', malformed strings
   - parse_ctrl_time: '0:00', '5:00', '2:34', NULL, '--', invalid format
   - parse_height/weight/reach: various text formats, NULL, '--'
   - total_fight_time_seconds: all 5 rounds, partial rounds, NULL inputs
2. Create backend/scraper/tests/test_fk_resolution.py covering:
   - Exact name matches
   - Name variations (nicknames, abbreviations)
   - Low-confidence matches that should be skipped
   - Empty/NULL name inputs
3. Use pytest; mock database calls with unittest.mock.
4. Achieve >90% line coverage on all parsing modules.
5. Acceptance criteria: all tests pass; edge cases documented; CI runs tests on push.

### 3.8. Build post_scrape_clean.py Orchestration Script

**Status:** done  
**Dependencies:** None  

Create the backend/scraper/post_scrape_clean.py script that orchestrates all five ETL phases in sequence, is fully idempotent, and provides structured logging and error reporting.

**Details:**

1. Create backend/scraper/post_scrape_clean.py as the single entry point for all cleanup phases.
2. Structure as sequential phase runner: Phase 1 (FK Resolution) -> Phase 2 (Quality Cleanup) -> Phase 3 (Type Parsing) -> Phase 4 (Derived Columns).
3. Each phase wrapped in try/except with transaction rollback on failure; failed phase logs error and continues or halts based on severity flag.
4. Idempotency: all UPDATE/ALTER statements use IF NOT EXISTS, WHERE col IS NULL guards, or UPSERT patterns so re-running produces no duplicate work.
5. Accept --phase argument to run individual phases for debugging.
6. Use Python logging module; output structured logs with phase name, rows affected, duration, and error details.
7. Load DB connection string from environment variable SUPABASE_DB_URL.
8. Acceptance criteria: script runs end-to-end without error on clean and already-processed data; --phase flag works; all phases complete in <30 minutes on full dataset.

### 3.9. GitHub Actions Workflow for Automated Post-Scrape Cleanup

**Status:** done  
**Dependencies:** None  

Wire post_scrape_clean.py into a GitHub Actions workflow that triggers automatically after each scrape run, with proper secret management and failure notifications.

**Details:**

1. Create .github/workflows/post_scrape_clean.yml.
2. Trigger: workflow_run with workflows: ['Scrape UFC Data'] and types: [completed]; also support manual workflow_dispatch trigger.
3. Job steps:
   a. Checkout repo
   b. Set up Python 3.11
   c. Install dependencies from backend/scraper/requirements.txt
   d. Run python backend/scraper/post_scrape_clean.py with SUPABASE_DB_URL from GitHub Secrets
4. Add conditional: only run if triggering workflow succeeded (github.event.workflow_run.conclusion == 'success').
5. On failure: send notification via GitHub Actions built-in failure reporting; optionally post to Slack via webhook secret.
6. Cache pip dependencies for faster runs.
7. Acceptance criteria: workflow triggers correctly after scrape; SUPABASE_DB_URL secret used (never logged); workflow passes on successful scrape; skips on failed scrape; manual trigger works.

### 3.10. End-to-End Validation and Data Quality Report

**Status:** done  
**Dependencies:** None  

Implement a validation script that runs post-cleanup to verify data quality metrics, FK integrity, and column completeness, producing a summary report for each pipeline run.

**Details:**

1. Create backend/scraper/validate_etl.py that runs after post_scrape_clean.py.
2. Validation checks using sqlalchemy.text() queries:
   - FK completeness: % of fight_details rows with non-NULL fighter_a_id/fighter_b_id
   - FK completeness: % of fight_results rows with non-NULL winner_id/loser_id
   - FK completeness: % of fight_stats rows with non-NULL fighter_id
   - Zero '--'/'---' values across all cleaned columns
   - WEIGHTCLASS values all in canonical set
   - Strike columns: % non-NULL for _landed/_attempted pairs
   - is_title_fight: non-NULL rate
   - fight_bonus: distribution of bonus types
3. Output a JSON summary report to backend/scraper/reports/etl_validation_{timestamp}.json.
4. Define pass/fail thresholds (e.g. FK completeness >95% = pass).
5. Exit with non-zero code if any threshold fails (causes GitHub Actions job to fail).
6. Integrate validate_etl.py call at end of post_scrape_clean.py and in GitHub Actions workflow.
7. Acceptance criteria: validation report generated on every run; pipeline fails loudly if quality thresholds not met; report archived as GitHub Actions artifact.
