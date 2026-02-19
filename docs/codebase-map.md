# UFC Analytics Platform — Codebase Map

Reference for every `.py` file in the project: what it does, whether you need it,
and where the important documentation lives.

---

## API Query Strategy: Raw SQL + Pydantic (no ORM models)

`backend/db/models.py` has been deleted. It defined SQLAlchemy ORM models that were
completely out of sync with the actual Supabase schema (snake_case vs. uppercase columns,
integer vs. VARCHAR(8) PKs). Nothing in the active codebase used it.

All working scripts query the database using raw SQL via `sqlalchemy.text()`. The FastAPI
layer (to be built) should follow the same pattern: raw SQL queries in service functions,
with Pydantic models in `backend/schemas/` for request/response serialisation.

---

## Python Files — Three Categories

### CRITICAL — Keep and Do Not Break

These files are actively running in production or are the foundation everything else depends on.

---

#### `backend/db/database.py` — DB Connection
Manages the SQLAlchemy engine, session factory, and connection pool to Supabase PostgreSQL.
Loads `DATABASE_URL` from `.env`. Every script that touches the database imports from here.
**This is the single most important file in the project.**

```python
from backend.db.database import SessionLocal, engine
```

---

#### `backend/scraper/live_scraper.py` — Active Weekly Scraper
Scrapes new UFC events from UFCStats.com every Sunday via GitHub Actions. Checks for events
not already in the database before inserting. Uses `DatabaseIntegration` to save results.
473 lines. This is the file GitHub Actions runs at `0 18 * * 0`.

---

#### `backend/scraper/database_integration.py` — Scraper → DB Bridge
The `DatabaseIntegration` class used by `live_scraper.py` to write scraped DataFrames into
Supabase. Handles saving events, fight stats, and fighter data. 217 lines.

---

#### `backend/scraper/keepalive_ping.py` — Supabase Keep-Alive
Runs a simple `COUNT(*)` query daily (3 AM UTC via GitHub Actions) to prevent Supabase
free tier from auto-pausing after 7 days of inactivity. This is the file that
`daily-keepalive.yml` calls — it is not `backend/utils/keep_alive.py`.

---

#### `backend/scraper/populate_new_foreign_keys.py` — Incremental FK Population
Fast script that resolves FK columns (`event_id`, `fight_id`, `fighter_id`, etc.) only for
rows where they are currently NULL. Safe to run repeatedly. 200 lines. Intended to be called
after `live_scraper.py` in the GitHub Actions workflow (currently it is not — this is a gap
that Phase 4 of the cleaning guide addresses).

---

### IMPORTANT — Understand These

These files are not running on a schedule but are essential for understanding the system,
running data cleaning tasks (see `database-schema-and-cleaning-guide.md`), or will be needed
when building the API.

---

#### `backend/db/__init__.py` — Package Exports
Exports `SessionLocal`, `engine`, `Base`, and `get_db` from `database.py`.
Import from here rather than importing `database.py` directly. 10 lines.

---

#### `backend/scraper/populate_foreign_keys.py` — Full Historical FK Population
The heavyweight version of `populate_new_foreign_keys.py`. Resolves all six FK relationships
across the entire dataset (not just NULL rows). Includes disable/enable of triggers.
Use this if you need to re-run FK population on all historical data (Phase 1 of the
cleaning guide). 415 lines.

---

#### `backend/scraper/bulk_scrape_career_stats.py` — Career Stats Scraper
One-time bulk scraper that hits each fighter's UFCStats.com profile page to pull career
averages (`slpm`, `str_acc`, `sapm`, `str_def`, `td_avg`, `td_acc`, `td_def`, `sub_avg`).
These 8 columns exist in `fighter_tott` but are 100% NULL — they were never populated.
Expected runtime ~3-4 hours for 4,449 fighters with rate limiting. 299 lines.
**This is needed for Phase 1 of the data cleaning plan.**

---

#### `backend/scraper/bulk_scrape_physical_stats.py` — Physical Stats Scraper
One-time scraper for HEIGHT, WEIGHT, REACH, STANCE, DOB from fighter profile pages.
Only updates NULL/missing fields — does not overwrite existing values. 371 lines.
Useful for backfilling the 44% missing REACH and 17% missing DOB values.

---

#### `backend/scraper/validate_greko_data.py` — Data Validator
Runs a comprehensive audit on the database: row counts, duplicate IDs, NULL checks,
spot-check of known fighters (Petr Yan), and relationship integrity. Run this after
any major data operation to confirm nothing is broken. 400 lines.

---

#### `backend/scraper/load_greko_csvs.py` — Historical CSV Loader
One-time script that loaded Greko's CSV files into Supabase (already ran — this is how
the 8,482 fights got into the DB). Keep as reference for the data loading procedure,
but do not run again — it clears all existing data before loading. 235 lines.

---

#### `eda/run_correlation_analysis.py` — Exploratory Data Analysis
Standalone analysis script. Loads `fighter_tott` and `fight_stats`, parses strings to
numerics, computes correlations between physical attributes and fight performance.
References findings from DeepUFC and Stanford CS229 papers. 283 lines.
Not part of the live system — run manually in a notebook or terminal for research.

---

#### `backend/scraper/full_historical_scraper.py` — Historical Scraper (already ran)
The 1,046-line scraper that originally populated all 8,482 fights from UFCStats.com.
This is how the full history was built before Greko's CSVs superseded it. The data
is already in the DB, so this file is for reference only. Do not re-run.

---

#### `backend/test_models.py` — Basic Connectivity Test
Validates that SQLAlchemy can connect and run simple model queries. Note: because
`models.py` is out of sync with the actual schema, these tests may pass connection
but return unexpected results. 55 lines.

---

### DELETED — Removed From Project

---

#### ~~`backend/db/models.py`~~ — DELETED
Out-of-sync ORM models (snake_case columns, integer PKs) that didn't match the actual
Supabase schema. Nothing in the active codebase used them. `database_integration.py` and
`__init__.py` were updated to remove the dependency before deletion.

---

#### ~~`backend/utils/keep_alive.py`~~ — DELETED
Duplicate of `backend/scraper/keepalive_ping.py`. GitHub Actions uses `keepalive_ping.py`.
This file was never called by anything.

---

#### ~~`backend/test_models.py`~~ — DELETED
Test file that validated the now-deleted ORM models. No longer relevant.

---

#### ~~`scrape_ufc_stats/*.py`~~ — DELETED (Python files only)
All Python files from the legacy Greko library directory have been removed:
`scrape_ufc_stats_library.py`, `incremental_scraper.py`, `scheduler.py`,
`scraper_utils.py`, `data_validation.py`, `database_integration.py`,
`scrape_ufc_stats_unparsed_data.py`. None were imported by any active file.

**Note:** `scrape_ufc_stats/` still exists and contains the original Greko CSV files
and Jupyter notebooks. These are the source backup for the entire database — do not
delete them unless you are certain Supabase has all the data and you have another backup.

---

#### `backend/scraper/__init__.py` — Empty Marker
1-line package marker. Harmless, not worth deleting.

---

## Empty Placeholder Directories

These directories exist but contain zero files. They are where the FastAPI API will live.

| Directory            | Intended Purpose                                      |
|----------------------|-------------------------------------------------------|
| `backend/app/`       | FastAPI application — routes, main.py, middleware     |
| `backend/schemas/`   | Pydantic request/response models for the API          |
| `backend/services/`  | Business logic layer between routes and database      |

---

## GitHub Actions — What Runs Automatically

| Workflow                    | Schedule         | Script Called                                  |
|-----------------------------|------------------|------------------------------------------------|
| `weekly-ufc-scraper.yml`    | Every Sunday 6PM UTC | `backend/scraper/live_scraper.py`          |
| `daily-keepalive.yml`       | Every day 3AM UTC    | `backend/scraper/keepalive_ping.py`        |

---

## Documentation — Where Things Live

| Document | Location | What It Covers |
|----------|----------|----------------|
| **Database schema + cleaning TODOs** | `docs/database-schema-and-cleaning-guide.md` | Full schema reference, FK map, step-by-step data cleaning plan, one-off vs ongoing tasks |
| **Codebase map** (this file) | `docs/codebase-map.md` | Every .py file explained, what to keep/delete, GitHub Actions overview |
| **Data requirements** | `docs/data-requirements.md` | Feature requirements for the three ML products |
| **Research references** | `docs/research-references.md` | External papers and sources referenced in the EDA |
| **Project overview + DB access** | `CLAUDE.md` | Business goals, DB connection strings, schema summary, scraper inventory |
| **Task list** | `.taskmaster/tasks/tasks.json` | Full breakdown of 10 tasks and subtasks with status |
| **Scraper README** | `backend/scraper/README_SCRAPER.md` | Scraper-specific setup and usage notes |
| **GitHub Actions setup** | `backend/scraper/GITHUB_ACTIONS_SETUP.md` | How the automation workflows are configured |
