# Kabe's Maybes — UFC Analytics Platform

ML-powered UFC fight analytics. Scrapes every UFC event from UFCStats.com, trains machine learning models on historical outcomes, and publishes weekly predictions for upcoming cards with a full transparency scorecard.

**Live site:** [kabes-maybes.vercel.app](https://kabes-maybes.vercel.app)

## What's on the site

- **Upcoming Card** — pre-computed win probability + method breakdown for this weekend's fights, refreshed every Saturday
- **Model Scorecard** — past prediction accuracy with per-event breakdown and fight search; predictions are frozen before each event to prevent data leakage
- **Fighter Lookup** — search any fighter, view career record, physical stats, and fight history
- **Completed Events** — browse all historical UFC events and fight cards
- **Style Evolution** — interactive timeline of how UFC fighting styles have changed since 1994; finish rates, fighter output metrics, physical stat trends by weight class, and a year-by-weight-class heatmap
- **Fighter Endurance** — round-by-round performance profiles and cardio prediction for individual fighters
- **Betting Insights** — five-tab dashboard comparing model picks against Vegas closing lines; strategy leaderboard with ROI breakdown, calibration chart, upset gallery, and a custom strategy builder
- **UFC Stats Assistant** — floating chat widget on every page; ask natural-language questions about any fighter or fight and get answers powered by live SQL queries against the full database (e.g. "What is Khabib's UFC record?", "Who has the most KO wins at lightweight?", "How did the Adesanya vs Pyfer fight end?")

## Tech Stack

### Backend
- **Framework**: FastAPI 0.115.5
- **Database**: PostgreSQL (Supabase)
- **ML**: Win/loss classifier auto-selected each retrain by validation AUC from logistic regression, random forest, and gradient boosting (XGBoost); method classifier (KO/Sub/Dec) is random forest — 63.57% test accuracy (958 fights, Apr 2024 - Jun 2026)
- **ORM**: SQLAlchemy 2.0 (raw SQL via `text()`, no ORM model layer)
- **Server**: Uvicorn (dev) / Gunicorn + UvicornWorker (prod)
- **Hosting**: Google Cloud Run (`kabes-maybes-api`, `us-central1`)

### Frontend
- **Framework**: React 19 + TypeScript 5.9 (Vite)
- **Styling**: Tailwind CSS v4 (CSS-first, `@theme` block in `index.css`)
- **Routing**: React Router v6, all pages lazy-loaded
- **HTTP**: Axios with error-normalising interceptor
- **Hosting**: Vercel (auto-deploys on push to `main`)

### Data Pipeline
- **Source**: UFCStats.com — 756 events (1994–present), 4,449 fighters, 8,482 fights, 39,912 fight stats
- **ETL**: 4-phase pipeline — FK resolution, quality cleanup, type parsing, derived columns
- **Updates**: Fully automated via GitHub Actions (7 workflows)

## API Endpoints

All endpoints versioned under `/api/v1`. Swagger docs at `/docs`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/health/db` | DB readiness (503 if unreachable) |
| GET | `/api/v1/fighters` | Paginated fighter list (`?search=`, `?page=`, `?page_size=`) |
| GET | `/api/v1/fighters/{id}` | Fighter profile + physical stats + career record |
| GET | `/api/v1/fights` | Paginated fight list (filters: event, fighter, weight class, method) |
| GET | `/api/v1/fights/{id}` | Fight detail + round-by-round stats |
| GET | `/api/v1/events` | Paginated event list (`?year=`) |
| GET | `/api/v1/events/{id}` | Event detail + full fight card |
| POST | `/api/v1/predictions/fight-outcome` | Win probability + method breakdown |
| POST | `/api/v1/chat` | Natural-language Q&A — converts question to SQL, executes, returns formatted answer (Groq/llama-3.3-70b) |
| GET | `/api/v1/analytics/style-evolution` | Finish rates, output metrics, and physical stats by year (`?weight_class=`) |
| GET | `/api/v1/analytics/fighter-endurance/{id}` | Round-by-round performance profile |
| GET | `/api/v1/analytics/betting-insights` | Model vs Vegas ROI summary, strategy leaderboard, calibration data |
| GET | `/api/v1/analytics/betting-insights/fights` | Fight-level model vs Vegas breakdown (filterable by conviction, weight class) |
| GET | `/api/v1/analytics/betting-roi` | Aggregated ROI by strategy and conviction bucket |
| GET | `/api/v1/upcoming/events` | Upcoming UFC events ordered by date |
| GET | `/api/v1/upcoming/events/{id}` | Upcoming event card + pre-computed predictions |
| GET | `/api/v1/upcoming/fights/{id}` | Single upcoming fight + full feature differentials |
| GET | `/api/v1/past-predictions` | Model scorecard — summary stats + recent outcomes |
| GET | `/api/v1/past-predictions/events` | Paginated past events with per-event accuracy |
| GET | `/api/v1/past-predictions/events/{id}` | All predictions for a specific past event |
| GET | `/api/v1/past-predictions/fights` | Fight-level search across all past predictions |
| GET | `/api/v1/past-predictions/fights/{id}` | Single past prediction by fight ID |

## Automation

7 GitHub Actions workflows keep everything current:

```
Daily    03:00 UTC  →  daily-keepalive          ping Supabase to prevent free tier pause

Saturday 15:00 UTC  →  upcoming-predictions     scrape announced fights + compute predictions

Sunday   14:00 UTC  →  weekly-ufc-scraper       scrape completed events from UFCStats
                    →  post-scrape-clean         ETL (FK resolution, type parsing, derived cols)
                                                 + archive pre-fight predictions before features change
                    →  feature-engineering       rebuild training_data.parquet
                    →  retrain                   retrain models + commit artefacts
                    →  deploy-backend            build Docker image + deploy to Cloud Run
```

## ML Model Performance

| Subset | Accuracy | Fights |
|--------|----------|--------|
| All fights (test set) | **63.57%** | 958 |

Test period: Apr 2024 - Jun 2026.
Model: the win/loss classifier is re-selected on every retrain by validation AUC from three candidates - logistic regression, random forest, and gradient boosting (XGBoost).
The three sit within noise of each other, so the selected model varies retrain to retrain.

Features: 30 differentials across physical attributes, rolling striking/grappling metrics, experience, and time-based features.
Full per-event and conviction-bucket breakdowns are live on the Betting Insights page.

## Local Development

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL or Supabase account

### Backend

```bash
git clone https://github.com/kibbbles/ufc_analytics_platform.git
cd ufc_analytics_platform

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

Create `.env` in the project root:
```
DATABASE_URL=postgresql://...
ENVIRONMENT=development
LOG_LEVEL=DEBUG
ALLOWED_ORIGINS=["http://localhost:3000"]
```

```bash
cd backend && python run_dev.py
# API:  http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Frontend

```bash
cd frontend && npm install
npm run dev       # http://localhost:3000 (proxies /api → :8000)
npm run build     # production build
npm run type-check
npm run lint
```

## Project Structure

```
ufc_analytics_platform/
├── backend/
│   ├── api/
│   │   ├── main.py                    # FastAPI app, CORS, middleware, exception handlers
│   │   ├── dependencies.py            # get_db() session dependency
│   │   ├── routers/health.py          # /health, /health/db
│   │   └── v1/endpoints/              # fighters, fights, events, predictions, upcoming,
│   │                                  # past_predictions, analytics, chat
│   ├── core/                          # config, logging, middleware
│   ├── db/                            # SQLAlchemy engine + SessionLocal
│   ├── features/                      # Feature engineering pipeline
│   │   ├── pipeline.py                # build_prediction_features(fighter_a_id, fighter_b_id, as_of)
│   │   ├── extractors.py              # get_fights_long_df(), get_stats_df()
│   │   ├── rolling_metrics.py         # 3/5/7-fight rolling averages + EWA
│   │   └── run_build.py               # Entry point → training_data.parquet
│   ├── ml/                            # Models + evaluation
│   │   ├── win_loss_v1.joblib         # Win/loss classifier (best of LR / RF / XGBoost by val AUC)
│   │   ├── method_v1.joblib           # Method classifier (KO/TKO, Sub, Dec)
│   │   ├── metrics.json               # Test set metrics
│   │   └── run_train.py               # Entry point
│   ├── schemas/                       # Pydantic v2 request/response models
│   ├── scraper/
│   │   ├── live_scraper.py            # Weekly scraper — all 6 core tables
│   │   ├── upcoming_scraper.py        # Upcoming events + fighter matching
│   │   ├── run_upcoming.py            # Entry point for upcoming scraper
│   │   ├── compute_past_predictions.py # Retroactive scorecard backfill
│   │   ├── archive_completed_predictions.py # Freeze pre-fight snapshots (Task 26)
│   │   ├── post_scrape_clean.py       # ETL orchestrator (4 phases)
│   │   └── validate_etl.py            # Data quality validation
│   ├── db/migrations/                 # SQL migration files
│   ├── run_dev.py                     # Dev server launcher
│   └── gunicorn.conf.py               # Production server config (reads $PORT)
├── frontend/
│   └── src/
│       ├── components/                # common/, layout/, features/
│       ├── hooks/                     # useApi, useDarkMode, useDebounce
│       ├── pages/                     # One file per route (lazy-loaded)
│       ├── router/index.tsx           # createBrowserRouter
│       ├── services/                  # Axios client + API service classes (chatService, etc.)
│       ├── types/api.ts               # TypeScript interfaces mirroring Pydantic schemas
│       └── utils/                     # Pure helpers
├── .github/workflows/                 # 7 automation workflows
├── Dockerfile                         # Python 3.12-slim, Gunicorn
├── render.yaml                        # Render IaC (fallback config)
└── docs/                              # project_history.ipynb, project_writeup.ipynb
```

## Author

**Kabe** (kay-bee) — [@kibbbles](https://github.com/kibbbles)

---

**Last Updated:** 2026-07-03
