# UFC Analytics Platform

## Project Overview
Full-stack web application providing ML-powered UFC fight analytics with interactive visualizations.
Built to demonstrate production-level data science and software engineering skills.

## Technical Architecture

### Backend Stack
- **Framework:** FastAPI 0.115.5
- **Database:** PostgreSQL (Supabase for deployment)
- **ML Libraries:** scikit-learn, XGBoost, pandas, numpy
- **API Documentation:** Automatic OpenAPI/Swagger generation at `/docs`
- **Authentication:** None required (public analytics platform)
- **Middleware:** CORS, RequestID (X-Request-ID header), Timing (logs per-request duration)
- **Logging:** Structured JSON via python-json-logger, rotating file handler (`logs/app.log`)
- **Server:** Uvicorn (dev, `run_dev.py`) / Gunicorn + UvicornWorker (prod, `gunicorn.conf.py`)
- **Hosting:** Google Cloud Run (`kabes-maybes-api`, `us-central1`, `min-instances=1`); auto-deploys via `deploy-backend.yml` on push to `main`

### Frontend Stack
- **Framework:** React 19 with TypeScript 5.9 (Vite scaffold)
- **Visualization:** Recharts for standard charts, D3.js for custom visualizations
- **State Management:** React Context API + useReducer
- **Styling:** Tailwind CSS v4 (CSS-first — `@import "tailwindcss"` + `@theme` block; no `tailwind.config.js`)
- **HTTP Client:** Axios for API communication
- **Routing:** React Router v6 (`createBrowserRouter`, all pages lazy-loaded)

**Dev commands:**
```bash
cd frontend && npm run dev        # start dev server (port 3000, proxies /api → :8000)
cd frontend && npm run build      # production build
cd frontend && npm run type-check # TypeScript check (no emit)
cd frontend && npm run lint       # ESLint
cd frontend && npm run format     # Prettier
```

**Frontend file structure:**
```
frontend/src/
├── components/
│   ├── common/          # LoadingSpinner, RouteGuard
│   ├── layout/          # ThemeProvider, Layout, Header
│   └── features/        # feature-specific components
├── hooks/               # useDarkMode, useApi, useDebounce
├── pages/               # One file per route (lazy-loaded)
├── router/              # index.tsx — createBrowserRouter
├── services/            # Axios instances + API service classes
├── store/               # Context + reducers
├── types/               # Shared TypeScript interfaces
└── utils/               # Pure helpers
```

**Path aliases** (configured in `tsconfig.app.json` + `vite.config.ts`):
`@/` → `src/`, `@components/` → `src/components/`, `@pages/`, `@hooks/`, `@services/`, `@store/`, `@types/`, `@utils/`

### Data Pipeline
- **Source:** UFCStats.com — 756 events, 8,482 fights, 4,449 fighters
- **Processing:** Python pandas for cleaning and feature engineering
- **Storage:** PostgreSQL with SQLAlchemy ORM
- **Updates:** Automated weekly scraping optimized for UFC event schedule

## Database & Data Status

### Supabase Database Connection
**Project**: mklpmbqpegbsistkoskm.supabase.co
**Access Methods**:
1. **SQL Editor**: https://supabase.com/dashboard/project/mklpmbqpegbsistkoskm/sql
2. **Python (SQLAlchemy)**: Via `DATABASE_URL` in `.env`
3. **Direct Connection**: see `DATABASE_URL` in `.env` (never commit credentials)

### Quick Database Query Examples
```python
# From backend directory
from db.database import SessionLocal
from sqlalchemy import text

session = SessionLocal()
result = session.execute(text("SELECT COUNT(*) FROM fighter_details"))
print(f"Total fighters: {result.scalar()}")
session.close()
```

### Current Data Status
- **Current State**: 756 events, 4,449 fighters, 8,482 fight results, 39,912 fight stats
- **Validation**: Petr Yan verified with correct 16 UFC fights (12W-4L)
- **Date Range**: 1994-03-11 to 2025-12-07 (UFC Fight Night: Covington vs. Buckley)
- **Foreign Keys**: ✅ All relationships populated (99.75%+ coverage)
- **Typed columns**: fight_stats (sig_str_landed, ctrl_seconds, kd_int, etc.), fight_results (fight_time_seconds, total_fight_time_seconds), fighter_tott (height_inches, weight_lbs, reach_inches, dob_date)
- **Derived columns**: fight_results.weight_class, is_title_fight, is_interim_title, is_championship_rounds

### FastAPI Backend

**Entry point:** `cd backend && python run_dev.py` (dev) or `gunicorn api.main:app -c gunicorn.conf.py` (prod)

**All routes:**
```
GET  /health                                        liveness check
GET  /health/db                                     DB readiness (503 on failure)
GET  /api/v1/fighters                               paginated list (?search= ?page= ?page_size=)
GET  /api/v1/fighters/{id}                          full profile + tott + record
GET  /api/v1/fights                                 paginated list (filters: event_id, fighter_id, weight_class, method)
GET  /api/v1/fights/{id}                            fight detail + round-by-round stats
GET  /api/v1/events                                 paginated list (?year=)
GET  /api/v1/events/{id}                            event + fight card
POST /api/v1/predictions/fight-outcome              win probability (best-of-3 selection: LR, RF, XGBoost)
GET  /api/v1/analytics/style-evolution              finish rates + output metrics by year (?weight_class=)
GET  /api/v1/analytics/fighter-endurance/{id}       round-by-round performance profile
GET  /api/v1/analytics/betting-insights             model vs Vegas ROI summary + strategy leaderboard
GET  /api/v1/analytics/betting-insights/fights      fight-level model vs Vegas breakdown
GET  /api/v1/analytics/betting-roi                  aggregated ROI by strategy and conviction bucket
GET  /api/v1/upcoming/events                        list upcoming events (ordered by date ASC)
GET  /api/v1/upcoming/events/{id}                   event card + fight list + pre-computed predictions
GET  /api/v1/upcoming/fights/{id}                   single fight prediction + full feature differentials
GET  /api/v1/past-predictions                       model scorecard — summary + recent outcomes
GET  /api/v1/past-predictions/events                paginated past events with per-event accuracy
GET  /api/v1/past-predictions/events/{id}           all predictions for a specific past event
GET  /api/v1/past-predictions/fights                fight-level search across all past predictions
GET  /api/v1/past-predictions/fights/{id}           single past prediction by fight ID
POST /api/v1/chat                                   natural-language Q&A (Groq/llama-3.3-70b → SQL → answer)
```

**Key files:**
- `backend/api/main.py` — app, middleware, exception handlers
- `backend/api/dependencies.py` — `get_db()` session dependency
- `backend/core/config.py` — settings singleton (`from core.config import settings`)
- `backend/core/middleware.py` — RequestIDMiddleware, TimingMiddleware
- `backend/schemas/` — Pydantic v2 schemas for all endpoints

### ETL Pipeline
Post-scrape cleanup runs automatically via GitHub Actions after each weekly scrape.

**Scripts**:
- `backend/scraper/post_scrape_clean.py` — orchestrates all 4 ETL phases in sequence
- `backend/scraper/validate_etl.py` — post-ETL data quality validation; exits 1 if thresholds not met
- `backend/scraper/reports/` — JSON validation reports (archived as GitHub Actions artifacts)

**Phases**:
1. FK Resolution — fighter_a/b_id, winner/loser FKs, fight_stats.fighter_id
2. Quality Cleanup — NULL out `--` placeholders, strip METHOD trailing spaces
3. Type Parsing — parse "X of Y" strikes, CTRL time, height/weight/reach, fight time
4. Derived Columns — weight_class, is_title_fight, is_interim_title, is_championship_rounds

**Run manually**:
```bash
python backend/scraper/post_scrape_clean.py           # all phases + validation
python backend/scraper/post_scrape_clean.py --phase 2 # single phase, no validation
python backend/scraper/post_scrape_clean.py --dry-run  # preview without DB changes
python backend/scraper/validate_etl.py                # standalone validation
```

### Available Scrapers
- `backend/scraper/live_scraper.py` — Active scraper; writes to all 6 tables (events, fights, results, stats, fighter profiles, tott)
- `backend/scraper/upcoming_scraper.py` — Scrapes UFCStats /upcoming, stores in upcoming_events/upcoming_fights/upcoming_predictions tables
- `backend/scraper/run_upcoming.py` — Entry point for upcoming scraper
- `backend/scraper/compute_past_predictions.py` — Retroactive scorecard backfill (prediction_source='backfill')
- `backend/scraper/archive_completed_predictions.py` — Freezes pre-fight prediction snapshots before ETL runs (prediction_source='pre_fight_archive')
- `backend/scraper/bulk_scrape_career_stats.py` — Career stats scraper (manual use)
- `backend/scraper/bulk_scrape_physical_stats.py` — Physical stats scraper (manual use)

## Database Schema

```sql
-- Core historical tables
event_details (756 rows)
    id VARCHAR(6) PRIMARY KEY,
    "EVENT" TEXT,
    "URL" TEXT,
    date_proper DATE,
    "LOCATION" TEXT

fighter_details (4,449 rows)
    id VARCHAR(6) PRIMARY KEY,
    "FIRST" TEXT,
    "LAST" TEXT,
    "NICKNAME" TEXT,
    "URL" TEXT

fight_details (8,482 rows)
    id VARCHAR(6) PRIMARY KEY,
    "EVENT" TEXT,
    "BOUT" TEXT,  -- Format: "Fighter A vs. Fighter B"
    "URL" TEXT,
    event_id VARCHAR(6) REFERENCES event_details(id),
    fighter_a_id VARCHAR(6),
    fighter_b_id VARCHAR(6)

fight_results (8,482 rows)  -- ONE row per fight
    id VARCHAR(6) PRIMARY KEY,
    "EVENT" TEXT,
    "BOUT" TEXT,
    "OUTCOME" TEXT,  -- "W/L" or "L/W" (winner listed first)
    "WEIGHTCLASS" TEXT,
    "METHOD" TEXT,
    "ROUND" TEXT,
    "TIME" TEXT,
    event_id VARCHAR(6) REFERENCES event_details(id),
    fight_id VARCHAR(6) REFERENCES fight_details(id),
    fighter_id VARCHAR(6),      -- winner FK
    opponent_id VARCHAR(6),     -- loser FK
    fight_time_seconds INTEGER,
    total_fight_time_seconds INTEGER,
    weight_class TEXT,          -- derived
    is_title_fight BOOLEAN,     -- derived
    is_interim_title BOOLEAN,   -- derived
    is_championship_rounds BOOLEAN  -- derived

fighter_tott (4,435 rows)  -- Tale of the Tape
    id VARCHAR(6) PRIMARY KEY,
    "FIGHTER" TEXT,
    "HEIGHT" TEXT, "WEIGHT" TEXT, "REACH" TEXT, "STANCE" TEXT, "DOB" TEXT,
    "URL" TEXT,
    fighter_id VARCHAR(6) REFERENCES fighter_details(id),
    height_inches FLOAT, weight_lbs FLOAT, reach_inches FLOAT,
    dob_date DATE

fight_stats (39,912 rows)  -- per fighter, per round
    id VARCHAR(6) PRIMARY KEY,
    "EVENT" TEXT, "BOUT" TEXT, "ROUND" TEXT,
    "FIGHTER" TEXT,       -- name only, no FK
    "KD" TEXT,
    "SIG.STR." TEXT,      -- Format: "17 of 37" (landed of attempted)
    "SIG.STR.%" TEXT,
    "TOTAL STR." TEXT,
    "TD" TEXT,            -- Takedowns: "0 of 2" format
    "TD%" TEXT, "SUB.ATT" TEXT, "REV." TEXT, "CTRL" TEXT,
    "HEAD" TEXT, "BODY" TEXT, "LEG" TEXT,
    "DISTANCE" TEXT, "CLINCH" TEXT, "GROUND" TEXT,
    event_id VARCHAR(6) REFERENCES event_details(id),
    fight_id VARCHAR(6) REFERENCES fight_details(id),
    fighter_id VARCHAR(6) REFERENCES fighter_details(id),
    sig_str_landed INT, sig_str_attempted INT, sig_str_pct FLOAT,
    kd_int INT, ctrl_seconds INT

-- Live upcoming tables
upcoming_events
    id VARCHAR(6) PRIMARY KEY,
    event_name TEXT, date_proper DATE, location TEXT,
    ufcstats_url TEXT UNIQUE,
    is_numbered BOOLEAN,
    scraped_at TIMESTAMPTZ

upcoming_fights
    id VARCHAR(6) PRIMARY KEY,
    event_id VARCHAR(6) REFERENCES upcoming_events(id),
    fighter_a_name TEXT, fighter_b_name TEXT,
    fighter_a_id VARCHAR(6) REFERENCES fighter_details(id),  -- nullable
    fighter_b_id VARCHAR(6) REFERENCES fighter_details(id),  -- nullable
    fighter_a_url TEXT, fighter_b_url TEXT,
    weight_class TEXT, is_title_fight BOOLEAN,
    ufcstats_url TEXT,
    scraped_at TIMESTAMPTZ,
    UNIQUE(event_id, fighter_a_url, fighter_b_url)

upcoming_predictions
    id VARCHAR(6) PRIMARY KEY,
    fight_id VARCHAR(6) UNIQUE REFERENCES upcoming_fights(id),
    model_version TEXT,
    win_prob_a FLOAT, win_prob_b FLOAT,
    method_ko_tko FLOAT, method_sub FLOAT, method_dec FLOAT,
    features_json JSONB,
    feature_hash TEXT,
    predicted_at TIMESTAMPTZ

-- Model scorecard
past_predictions
    prediction_source: 'pre_fight_archive' | 'backfill'
    -- DISTINCT ON (fight_id) dedup prefers pre_fight_archive
```

### Fighter Matching Logic (upcoming_scraper.py)
UFCStats event page cell[1] contains `<a href="http://ufcstats.com/fighter-details/XXXXX">`.
This URL matches `fighter_details."URL"` exactly.
Primary: `SELECT id FROM fighter_details WHERE "URL" = :ufcstats_url`
Fallback: fuzzy FIRST+LAST name match if URL not found.
If no match: store fight with fighter_a_id/b_id = NULL, skip prediction.

### Relationship Status
- ✅ event_details ↔ fight_details via event_id (100%)
- ✅ event_details ↔ fight_results via event_id (100%)
- ✅ event_details ↔ fight_stats via event_id (100%)
- ✅ fight_details ↔ fight_results via fight_id (100%)
- ✅ fight_details ↔ fight_stats via fight_id (100%)
- ✅ fighter_details ↔ fighter_tott via fighter_id (99.75%)
- ✅ fight_stats.fighter_id → fighter_details (99.8%+)
- ✅ fight_results.fighter_id / opponent_id → fighter_details (100%)

### Data Format Notes
- **Stats Format**: "X of Y" means X landed, Y attempted
- **Winner Logic**: In OUTCOME "W/L", first fighter in BOUT won
- **Coverage**: Detailed stats (fight_stats) mainly available 2015+
- **2014 and earlier**: Limited to basic fight results only

### CRITICAL: fight_results Query Pattern
fight_results has ONE row per fight. `fighter_id` = winner, `opponent_id` = loser.
Querying only `WHERE fighter_id = :id` returns WINS ONLY — losses are invisible.

**Always use the OR pattern for full fight history:**
```sql
SELECT
    e.date_proper,
    fr."BOUT",
    fr."METHOD",
    (fr.fighter_id = fd.id) AS is_win
FROM fight_results fr
JOIN fighter_details fd ON fd.id = :fighter_id
JOIN event_details e ON e.id = fr.event_id
WHERE fr.fighter_id = fd.id OR fr.opponent_id = fd.id
ORDER BY e.date_proper
```
`get_fights_long_df()` in `backend/features/extractors.py` handles this correctly
via UNION ALL — training pipeline is unaffected. The OR pattern is only needed
for ad-hoc queries and API endpoints that return fighter history.

### Data Loading Procedure
**To reload database from Greko CSVs:**
```bash
cd backend/scraper
python load_greko_csvs.py          # Clear & load CSVs
python fix_foreign_key_columns.py  # Fix column types to VARCHAR(8)
python populate_foreign_keys.py    # Populate relationships
python validate_greko_data.py      # Verify data integrity
python post_scrape_clean.py        # Run full ETL pipeline + validation
```

### Automation
```
Daily    03:00 UTC  → daily-keepalive       (keep Supabase alive)

Saturday 15:00 UTC  → upcoming-predictions  (scrape same-day card + pre-compute)

Sunday   14:00 UTC  → weekly-ufc-scraper    (scrape new completed events)
                    → post-scrape-clean     (ETL cleanup + archive pre-fight predictions)
                    → feature-engineering   (rebuild training_data.parquet)
                    → retrain               (retrain + commit model artefacts)
                    → deploy-backend        (build + deploy updated image to Cloud Run)
```

## Hosting & Deployment

### Architecture
```
User's browser → Vercel — kabes-maybes.vercel.app (frontend) ✅ LIVE
                      ↓ API calls
                 Google Cloud Run — kabes-maybes-api (FastAPI, Docker, us-central1) ✅ LIVE
                      ↓ SQL
                 Supabase (PostgreSQL) ✅ LIVE
```

### Frontend — Vercel
- Auto-deploys on every push to `main`
- Root Directory: `frontend`
- Env var: `VITE_API_BASE_URL=https://kabes-maybes-api-417674442311.us-central1.run.app/api/v1`
- CORS regex in `main.py` covers all Vercel preview URLs: `kabes-maybes(-git-.*-kibbbles-projects)?\.vercel\.app`
- URL: `https://kabes-maybes.vercel.app` ✅ LIVE

### Backend — Google Cloud Run
- Project: `kabes-maybes` (GCP, `kabe.chin@gmail.com`)
- Service: `kabes-maybes-api`, region `us-central1`, `min-instances=1`
- Image: `us-central1-docker.pkg.dev/kabes-maybes/kabes-maybes/api:latest`
- Secrets via Google Cloud Secret Manager: `DATABASE_URL`, `ALLOWED_ORIGINS`
- Auto-deploys via `deploy-backend.yml` GitHub Actions on push to `main` (backend paths)
- URL: `https://kabes-maybes-api-417674442311.us-central1.run.app` ✅ LIVE
- Verify: `/health` → `{"status":"ok"}` | `/docs` → Swagger UI

## Frontend Design Philosophy

**Aesthetic direction: Analytics Showcase / Learning Tool**

This is a portfolio project that demonstrates data science and engineering skill — not a commercial product for sale.
It should feel like high-quality editorial data journalism (FiveThirtyEight, The Pudding, NYT data desk) with a UFC subject matter.

**Core visual principles:**
- **Purpose over polish**: Content and data legibility come first. Every design decision should make the data easier to read and understand, not impress with visual effects
- **Mobile-first**: All layouts must be fully usable on a phone screen. Design at 375px, enhance upward
- **Background**: `#0f1117` dark base (dark mode) / `#ffffff` clean white (light mode) — both equally polished
- **Accent**: `#e63946` UFC red — used for active state indicators, key stats, primary actions only. Not decorative
- **Typography**: Clear hierarchy — bold heading for section titles, readable body size (14-16px), monospace for stats/numbers (`font-mono tabular-nums` for all numerical data)
- **Data visualization**: Data-ink ratio over decoration. No chart junk. Color used to encode meaning only, not to fill space. Animation should communicate change, not entertain
- **Avoid**: Dramatic shadows for their own sake, glassmorphism, gradient meshes, premium-product marketing patterns (hero sections with taglines, "Get started" CTAs, pricing-table layouts)
- **Look like**: A well-crafted data analysis that someone built because they love MMA and data — approachable, credible, technically impressive

**Design token source of truth:** `frontend/src/index.css` `@theme` block
All colors, shadows, and fonts are defined as CSS custom properties — never hardcode values in components.

## Frontend Architecture & Scalability

**Routing approach: page-based navigation**

Each feature is a separate route with its own lazy-loaded JS chunk.
This is the right pattern for a data analytics platform — each tool is a complete independent experience, not a scroll section.

**Adding new features:** two steps, no architectural changes needed:
1. Create `frontend/src/pages/YourNewPage.tsx`
2. Add the route to `frontend/src/router/index.tsx`

**Sub-tabs within a page:** use a tab component rendered inside the page, keeping the parent route stable and tab state in URL params (`?tab=style-evolution`).
Do not nest routes unless the sub-pages are truly independent experiences.

**Component organization:**
- `components/common/` — reusable primitives (Button, Card, Badge, Modal)
- `components/layout/` — page shell (Header, Layout, ThemeProvider)
- `components/features/` — feature-specific components (FighterCard, FightCard, PredictionSlider, etc.)
- Each feature page imports from `components/features/` — not from other pages

**State philosophy:** Local state first (useState), Context for truly cross-cutting state (theme, auth if added).
Avoid global stores for page-specific data — use fetch-on-mount with loading/error states per page.

**Mobile patterns:**
- Header: logo + toggle visible always; hamburger on < md; full nav on md+
- Pages: single-column on mobile, 2-col on sm, multi-col on lg
- Touch targets: minimum 44×44px for all interactive elements
- No horizontal scroll at any breakpoint

## Documentation Guidelines
- All .md files should be placed in the `docs/` directory
- Keep documentation organized and up-to-date with code changes
- **Auto-update README.md**: Update README.md whenever significant project changes occur
- **Auto-update requirements.txt**: Add new dependencies immediately when introduced

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
When creating .md files, place them in the docs/ directory.

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
