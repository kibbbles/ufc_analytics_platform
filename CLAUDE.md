# UFC Analytics Platform

## Project Overview
Full-stack web application providing ML-powered UFC fight analytics with interactive visualizations. Built to demonstrate production-level data science and software engineering skills.

## Business Problem
UFC fans and analysts lack sophisticated tools to:
- Predict fight outcomes with interactive parameter exploration
- Understand evolution of fighting styles over time
- Analyze fighter endurance and pacing patterns

## Three Core Products

### 1. Fight Outcome Predictor with Interactive Sliders
**Description:** Real-time ML predictions with user-adjustable fighter attributes
**Features:**
- Interactive sliders for height, weight, reach, age, experience, striking accuracy
- Live win probability updates as users adjust parameters  
- Similar historical fights display based on current inputs
- Method prediction (KO/TKO, Submission, Decision) with confidence scores

**ML Approach:**
- Models: XGBoost, Random Forest, Logistic Regression
- Features: Physical differentials, performance metrics, experience gaps
- Target: Binary classification (Fighter A wins) + multi-class method prediction

### 2. Style Evolution Timeline Analyzer  
**Description:** Interactive timeline showing how fighting styles evolved in UFC history
**Features:**
- Timeline visualization of finish rates by method (KO/TKO vs Submission vs Decision)
- Filter by weight class, era, specific time ranges
- Trend analysis of striking vs grappling effectiveness over time
- Animated transitions between different eras

**ML Approach:**
- Time series analysis of style metrics by year
- Clustering fighters by fighting style patterns
- Regression models for trend forecasting
- Statistical analysis of style effectiveness changes

### 3. Fighter Endurance & Pacing Dashboard
**Description:** Round-by-round performance analysis and cardio predictions  
**Features:**
- Individual fighter endurance profiles showing performance by round
- Predictions of performance degradation in longer fights
- Comparison of cardio between different fighting styles
- Fight pacing analysis (early finisher vs marathon fighter classification)

**ML Approach:**
- Time series modeling of round-by-round performance
- Survival analysis for fight finish probability by round
- Regression models predicting cardio performance based on style/age

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

**Task status (Task 7 — React Frontend Foundation — ✅ COMPLETE 2026-03-08):**
- ✅ 7.1 Vite scaffold, path aliases, dev proxy, ESLint + Prettier
- ✅ 7.2 Tailwind v4 design tokens, dark mode (localStorage + prefers-color-scheme)
- ✅ 7.3 React Router v6, lazy-loaded routes, Layout + Header + LoadingSpinner
- ✅ 7.4 State management (Context API, useReducer, typed actions, localStorage persistence)
- ✅ 7.5 Axios API client, service classes, common UI components (Button, Card, Badge, Toast, etc.)
- ✅ 7.6 Data-connected pages: EventsPage, EventDetailPage, FightersPage, FighterDetailPage

**Frontend file structure:**
```
frontend/src/
├── components/
│   ├── common/          # LoadingSpinner, RouteGuard
│   ├── layout/          # ThemeProvider, Layout, Header
│   └── features/        # (Task 7.5+) feature-specific components
├── hooks/               # useDarkMode (+ future custom hooks)
├── pages/               # One file per route (lazy-loaded)
├── router/              # index.tsx — createBrowserRouter
├── services/            # (Task 7.5) Axios instances + API service classes
├── store/               # (Task 7.4) Context + reducers
├── types/               # Shared TypeScript interfaces
└── utils/               # Pure helpers
```

**Path aliases** (configured in `tsconfig.app.json` + `vite.config.ts`):
`@/` → `src/`, `@components/` → `src/components/`, `@pages/`, `@hooks/`, `@services/`, `@store/`, `@types/`, `@utils/`

### Data Pipeline
- **Source:** UFCStats.com via enhanced Greco scraper (744 events, 8287 fights, 4429 fighters available)
- **Processing:** Python pandas for cleaning and feature engineering
- **Storage:** PostgreSQL with SQLAlchemy ORM
- **Updates:** Automated weekly scraping optimized for UFC event schedule

## Database & Data Status

### Supabase Database Connection
**Project**: mklpmbqpegbsistkoskm.supabase.co
**Access Methods**:
1. **SQL Editor**: https://supabase.com/dashboard/project/mklpmbqpegbsistkoskm/sql
2. **Python (SQLAlchemy)**: Via `DATABASE_URL` in `.env`
3. **Direct Connection**: `postgresql://postgres:p2GrvZEea/XEY%d@db.mklpmbqpegbsistkoskm.supabase.co:5432/postgres`

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
**✅ CLEAN DATA — ETL Pipeline Complete (Task 3 done 2026-02-23)**
- **Current State**: 756 events, 4,449 fighters, 8,482 fight results, 39,912 fight stats
- **Validation**: Petr Yan verified with correct 16 UFC fights (12W-4L)
- **Date Range**: 1994-03-11 to 2025-12-07 (UFC Fight Night: Covington vs. Buckley)
- **Foreign Keys**: ✅ All relationships populated (99.75%+ coverage)
- **Typed columns**: fight_stats (sig_str_landed, ctrl_seconds, kd_int, etc.), fight_results (fight_time_seconds, total_fight_time_seconds), fighter_tott (height_inches, weight_lbs, reach_inches, dob_date)
- **Derived columns**: fight_results.weight_class, is_title_fight, is_interim_title, is_championship_rounds

### FastAPI Backend (Task 4 — COMPLETE 2026-02-28)

**Entry point:** `cd backend && python run_dev.py` (dev) or `gunicorn api.main:app -c gunicorn.conf.py` (prod)

**All routes:**
```
GET  /health                                  liveness check
GET  /health/db                               DB readiness (503 on failure)
GET  /api/v1/fighters                         paginated list (?search= ?page= ?page_size=)
GET  /api/v1/fighters/{id}                    full profile + tott + record
GET  /api/v1/fights                           paginated list (filters: event_id, fighter_id, weight_class, method)
GET  /api/v1/fights/{id}                      fight detail + round-by-round stats
GET  /api/v1/events                           paginated list (?year=)
GET  /api/v1/events/{id}                      event + fight card
POST /api/v1/predictions/fight-outcome        win probability (XGBoost + RF ensemble — Task 6 complete)
GET  /api/v1/analytics/style-evolution        finish rates by year (?weight_class=)
GET  /api/v1/analytics/fighter-endurance/{id} round-by-round performance profile

# Phase 2 — Upcoming Events (Tasks 11-20, pending)
GET  /api/v1/upcoming/events                  list upcoming events (ordered by date ASC)
GET  /api/v1/upcoming/events/{id}             event card + fight list + pre-computed predictions
GET  /api/v1/upcoming/fights/{id}             single fight prediction + full feature differentials
POST /api/v1/admin/refresh-upcoming           manual trigger: re-scrape upcoming page + recompute
```

**Key files:**
- `backend/api/main.py` — app, middleware, exception handlers
- `backend/api/dependencies.py` — `get_db()` session dependency
- `backend/core/config.py` — settings singleton (`from core.config import settings`)
- `backend/core/middleware.py` — RequestIDMiddleware, TimingMiddleware
- `backend/schemas/` — Pydantic v2 schemas for all endpoints

### ETL Pipeline (Task 3 — COMPLETE)
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

**Workflows**:
- `.github/workflows/weekly-ufc-scraper.yml` — weekly scrape (live_scraper.py)
- `.github/workflows/post-scrape-clean.yml` — ETL + validation, triggered after scrape succeeds

### Available Scrapers
- `backend/scraper/live_scraper.py` — Active scraper; writes to all 6 tables (events, fights, results, stats, fighter profiles, tott)
- `backend/scraper/upcoming_scraper.py` — **Phase 2 (Task 13, pending)** Scrapes UFCStats /upcoming, stores in upcoming_events/upcoming_fights/upcoming_predictions tables
- `backend/scraper/run_upcoming.py` — **Phase 2 (Task 15, pending)** Entry point for upcoming scraper (mirrors live_scraper.py main)
- `backend/scraper/bulk_scrape_career_stats.py` — Career stats scraper (manual use)
- `backend/scraper/bulk_scrape_physical_stats.py` — Physical stats scraper (manual use)

### Database Schema (Current)
```sql
-- Phase 1 core tables
event_details (756 rows)       -- UFC events
fighter_details (4,449 rows)   -- Fighter profiles
fight_details (~8,482 rows)    -- Fight matchups
fight_results (8,482 rows)     -- Fight outcomes + typed/derived columns
fighter_tott (4,435 rows)      -- Tale of the Tape + typed columns
fight_stats (39,912 rows)      -- Round-by-round stats + typed columns

-- Phase 2 upcoming tables (Tasks 11-20, to be created)
upcoming_events                -- Booked UFC events not yet completed
upcoming_fights                -- Announced bouts with fighter FK refs (nullable for new fighters)
upcoming_predictions           -- Pre-computed ML predictions + full feature differential JSON
```

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
- `.github/workflows/weekly-ufc-scraper.yml` — Sunday 18:00 UTC: live_scraper.py → completed events
- `.github/workflows/post-scrape-clean.yml` — ETL cleanup + validation, auto-triggered after scrape
- `.github/workflows/feature-engineering.yml` — Rebuild training matrix, auto-triggered after ETL
- `.github/workflows/retrain.yml` — Retrain ML models, auto-triggered after feature engineering
- `.github/workflows/upcoming-predictions.yml` — **Phase 2 (Task 15, pending)** Friday 12:00 UTC: upcoming_scraper + pre-compute predictions

**Weekly automation chain:**
```
Sunday 18:00 UTC  → weekly-ufc-scraper    (scrape new completed events)
                  → post-scrape-clean     (ETL cleanup)
                  → feature-engineering  (rebuild training_data.parquet)
                  → retrain              (retrain + commit model artefacts)

Friday 12:00 UTC  → upcoming-predictions  (scrape next Saturday's card + pre-compute)
```


## Database Schema & Relationships

### Actual Production Tables (Supabase)
```sql
-- Core tables with actual column names
event_details (
    id VARCHAR(6) PRIMARY KEY,  -- Alphanumeric ID
    "EVENT" TEXT,
    "URL" TEXT, 
    date_proper DATE,
    "LOCATION" TEXT
);

fighter_details (
    id VARCHAR(6) PRIMARY KEY,  -- Alphanumeric ID
    "FIRST" TEXT,
    "LAST" TEXT,
    "NICKNAME" TEXT,
    "URL" TEXT
);

fight_details (
    id VARCHAR(6) PRIMARY KEY,  -- Alphanumeric ID
    "EVENT" TEXT,
    "BOUT" TEXT,  -- Format: "Fighter A vs. Fighter B"
    "URL" TEXT,
    event_id VARCHAR(6) REFERENCES event_details(id),
    fighter_a_id VARCHAR(6),  -- Parsed from BOUT
    fighter_b_id VARCHAR(6)   -- Parsed from BOUT
);

fight_results (
    id VARCHAR(6) PRIMARY KEY,
    "EVENT" TEXT,
    "BOUT" TEXT,
    "OUTCOME" TEXT,  -- Format: "W/L" or "L/W" (winner/loser)
    "WEIGHTCLASS" TEXT,
    "METHOD" TEXT,
    "ROUND" TEXT,
    "TIME" TEXT,
    event_id VARCHAR(6) REFERENCES event_details(id),
    fight_id VARCHAR(6) REFERENCES fight_details(id),
    result_data JSONB  -- Stores additional result data
);

fighter_tott (  -- Tale of the Tape
    id VARCHAR(6) PRIMARY KEY,
    "FIGHTER" TEXT,
    "HEIGHT" TEXT,
    "WEIGHT" TEXT,
    "REACH" TEXT,
    "STANCE" TEXT,
    "DOB" TEXT,
    "URL" TEXT,
    fighter_id VARCHAR(6) REFERENCES fighter_details(id),  -- ✅ Connected
    tott_data JSONB
);

fight_stats (  -- Per fighter, per round statistics
    id VARCHAR(6) PRIMARY KEY,
    "EVENT" TEXT,
    "BOUT" TEXT,
    "ROUND" TEXT,
    "FIGHTER" TEXT,  -- Fighter name (text only, no FK)
    "KD" TEXT,
    "SIG.STR." TEXT,  -- Format: "17 of 37" (landed of attempted)
    "SIG.STR.%" TEXT,
    "TOTAL STR." TEXT,
    "TD" TEXT,  -- Takedowns: "0 of 2" format
    "TD%" TEXT,
    "SUB.ATT" TEXT,
    "REV." TEXT,
    "CTRL" TEXT,
    "HEAD" TEXT,
    "BODY" TEXT,
    "LEG" TEXT,
    "DISTANCE" TEXT,
    "CLINCH" TEXT,
    "GROUND" TEXT,
    event_id VARCHAR(6) REFERENCES event_details(id),
    fight_id VARCHAR(6) REFERENCES fight_details(id)  -- 64% connected
);
```

### Phase 2 Tables (to be created — Tasks 11-20)
```sql
upcoming_events (
    id            VARCHAR(6) PRIMARY KEY,
    event_name    TEXT,
    date_proper   DATE,
    location      TEXT,
    ufcstats_url  TEXT UNIQUE,       -- used for upsert deduplication
    is_numbered   BOOLEAN,           -- TRUE if "UFC [number]:" format
    scraped_at    TIMESTAMPTZ DEFAULT now()
);

upcoming_fights (
    id              VARCHAR(6) PRIMARY KEY,
    event_id        VARCHAR(6) REFERENCES upcoming_events(id),
    fighter_a_name  TEXT,
    fighter_b_name  TEXT,
    fighter_a_id    VARCHAR(6) REFERENCES fighter_details(id),  -- nullable (new fighters)
    fighter_b_id    VARCHAR(6) REFERENCES fighter_details(id),  -- nullable (new fighters)
    fighter_a_url   TEXT,            -- UFCStats profile URL, used for fighter matching
    fighter_b_url   TEXT,
    weight_class    TEXT,
    is_title_fight  BOOLEAN DEFAULT FALSE,
    ufcstats_url    TEXT,            -- fight-details page URL
    scraped_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(event_id, fighter_a_url, fighter_b_url)  -- idempotent upsert key
);

upcoming_predictions (
    id             VARCHAR(6) PRIMARY KEY,
    fight_id       VARCHAR(6) UNIQUE REFERENCES upcoming_fights(id),
    model_version  TEXT DEFAULT 'win_loss_v1',
    win_prob_a     FLOAT,            -- P(fighter_a wins)
    win_prob_b     FLOAT,            -- P(fighter_b wins)
    method_ko_tko  FLOAT,
    method_sub     FLOAT,
    method_dec     FLOAT,
    features_json  JSONB,            -- full 31-feature differential dict
    feature_hash   TEXT,             -- hash of feature vector for staleness detection
    predicted_at   TIMESTAMPTZ DEFAULT now()
);
```

**Fighter Matching Logic (upcoming_scraper.py):**
UFCStats event page cell[1] contains `<a href="http://ufcstats.com/fighter-details/XXXXX">`.
This URL matches `fighter_details."URL"` exactly.
Primary: `SELECT id FROM fighter_details WHERE "URL" = :ufcstats_url`
Fallback: fuzzy FIRST+LAST name match if URL not found.
If no match: store fight with fighter_a_id/b_id = NULL, skip prediction.

### Relationship Status (Updated 2026-02-23)
- ✅ **Complete**: event_details ↔ fight_details via event_id (100%)
- ✅ **Complete**: event_details ↔ fight_results via event_id (100%)
- ✅ **Complete**: event_details ↔ fight_stats via event_id (100%)
- ✅ **Complete**: fight_details ↔ fight_results via fight_id (100%)
- ✅ **Complete**: fight_details ↔ fight_stats via fight_id (100%)
- ✅ **Complete**: fighter_details ↔ fighter_tott via fighter_id (99.75%)
- ✅ **Complete**: fight_stats.fighter_id → fighter_details (99.8%+ coverage)
- ✅ **Complete**: fight_results.fighter_id / opponent_id → fighter_details (100%)

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

## Hosting & Deployment

### Architecture
```
User's browser → Vercel (frontend, free)
                      ↓ API calls
                 Render (FastAPI backend, free tier — 512MB)
                      ↓ SQL
                 Supabase (PostgreSQL, already live ✅)
```

### Frontend — Vercel (free)
- Connect GitHub repo at vercel.com → auto-deploys on every `git push`
- Set Root Directory to `frontend` in Vercel project settings
- Set one env var in Vercel dashboard: `VITE_API_BASE_URL=https://ufc-analytics-platform.onrender.com/api/v1`
- Project name: `kabes-maybes` → URL: `kabes-maybes.vercel.app`

### Backend — Render (free tier, 512MB RAM)
Deployment files:
- `Dockerfile` — builds the FastAPI container (Python 3.12-slim, 1 gunicorn worker)
- `.dockerignore` — excludes frontend, tests, logs, .env from container
- `render.yaml` — Render IaC config: service name, Dockerfile path, health check, env vars

**Tradeoff:** Render's free tier spins down after 15 minutes of inactivity (cold start ~30s on next request). Acceptable for a portfolio project; upgrade to $7/month paid tier to eliminate cold starts when actively job hunting.

**One-time setup (in browser at render.com):**
1. Sign in with GitHub at render.com
2. New → Web Service → connect `ufc_analytics_platform` repo
3. Render auto-detects `render.yaml` — confirm settings
4. Add environment variables in Render dashboard:
   - `DATABASE_URL` = `postgresql://postgres:p2GrvZEea/XEY%d@db.mklpmbqpegbsistkoskm.supabase.co:5432/postgres`
   - `ALLOWED_ORIGINS` = `["https://kabes-maybes.vercel.app","http://localhost:3000"]`
   - `ENVIRONMENT` = `production`
5. Click Deploy

**URL:** `https://ufc-analytics-platform.onrender.com`
**Verify:** `/health` → `{"status":"ok"}` | `/docs` → Swagger UI

**Subsequent deploys:** automatic on every `git push` to `main`

## Frontend Design Philosophy

**Aesthetic direction: Analytics Showcase / Learning Tool**

This is a portfolio project that demonstrates data science and engineering skill — not a commercial product for sale. It should feel like high-quality editorial data journalism (FiveThirtyEight, The Pudding, NYT data desk) with a UFC subject matter.

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

**Routing approach: page-based navigation (already implemented)**

Each feature is a separate route with its own lazy-loaded JS chunk. This is the right pattern for a data analytics platform — each tool is a complete independent experience, not a scroll section.

**Adding new features:** two steps, no architectural changes needed:
1. Create `frontend/src/pages/YourNewPage.tsx`
2. Add the route to `frontend/src/router/index.tsx`

**Sub-tabs within a page:** For related views (e.g., an `/analytics` page with style-evolution and endurance as tabs), use a tab component rendered inside the page, keeping the parent route at `/analytics` and the tab state in URL params (`?tab=style-evolution`). Do not nest routes unless the sub-pages are truly independent experiences.

**Component organization:**
- `components/common/` — reusable primitives (Button, Card, Badge, Modal)
- `components/layout/` — page shell (Header, Layout, ThemeProvider)
- `components/features/` — feature-specific components (FighterCard, FightCard, PredictionSlider, etc.)
- Each feature page imports from `components/features/` — not from other pages

**State philosophy:** Local state first (useState), Context for truly cross-cutting state (theme, auth if added). Avoid global stores for page-specific data — use fetch-on-mount with loading/error states per page.

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
- **Track progress**: Update task status in task-master when completing work

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
When creating .md files, place them in the docs/ directory (C:\Users\kabec\Documents\ufc_analytics_platform\docs).

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
