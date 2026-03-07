# UFC Analytics Platform

ML-powered UFC fight analytics platform with interactive predictions and visualizations. Built to demonstrate production-level data science and software engineering skills.

## Features

- **Fight Outcome Predictor**: Interactive ML predictions with adjustable fighter parameters and live win probability
- **Style Evolution Timeline**: Visualize how fighting styles evolved throughout UFC history
- **Fighter Endurance Dashboard**: Round-by-round performance analysis and cardio predictions
- **Upcoming Event Predictions** *(Phase 2)*: Pre-computed predictions for next Saturday's card, refreshed every Friday

## Tech Stack

### Backend
- **Framework**: FastAPI 0.115.5
- **Database**: PostgreSQL (Supabase)
- **ML**: XGBoost, scikit-learn, Random Forest — test AUC 0.679, title fight accuracy 61.9%
- **ORM**: SQLAlchemy 2.0 (raw SQL queries, no ORM model layer)
- **Server**: Uvicorn (dev) / Gunicorn + UvicornWorker (production)

### Frontend *(Task 7 — pending)*
- **Framework**: React 18 + TypeScript
- **Visualization**: Recharts, D3.js
- **Styling**: Tailwind CSS

### Data Pipeline
- **Source**: UFCStats.com — 756 events (1994–2026), 4,449 fighters, 8,482 fights, 39,912 fight stats
- **Processing**: pandas + numpy with automated ETL pipeline
- **Storage**: PostgreSQL with 6 tables, fully resolved FK relationships (99.75%+ coverage)
- **Updates**: Automated via GitHub Actions — weekly scrape Sunday, upcoming predictions Friday

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL or Supabase account

### Backend Setup

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
```

**Development server:**
```bash
cd backend
python run_dev.py
# API:  http://localhost:8000
# Docs: http://localhost:8000/docs
```

**Production server:**
```bash
cd backend
gunicorn api.main:app -c gunicorn.conf.py
```

## API Endpoints

All data endpoints versioned under `/api/v1`.

### Phase 1 — Core Data & ML

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/health/db` | DB readiness (503 if unreachable) |
| GET | `/api/v1/fighters` | Paginated fighter list (`?search=`, `?page=`, `?page_size=`) |
| GET | `/api/v1/fighters/{id}` | Fighter profile: physical stats, career averages, record |
| GET | `/api/v1/fights` | Paginated fight list (filters: event, fighter, weight class, method) |
| GET | `/api/v1/fights/{id}` | Fight detail + round-by-round stats |
| GET | `/api/v1/events` | Paginated event list (`?year=`) |
| GET | `/api/v1/events/{id}` | Event detail + full fight card |
| POST | `/api/v1/predictions/fight-outcome` | Win probability + method breakdown (Random Forest) |
| GET | `/api/v1/analytics/style-evolution` | Finish rates by year (`?weight_class=`) |
| GET | `/api/v1/analytics/fighter-endurance/{id}` | Round-by-round performance profile |

### Phase 2 — Upcoming Events *(Tasks 11-20, pending)*

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/upcoming/events` | Upcoming UFC events ordered by date |
| GET | `/api/v1/upcoming/events/{id}` | Event card + pre-computed predictions |
| GET | `/api/v1/upcoming/fights/{id}` | Single fight prediction + full feature differentials |
| POST | `/api/v1/admin/refresh-upcoming` | Manual trigger: re-scrape + recompute predictions |

## Automation

Data is kept current via GitHub Actions:

```
Sunday  18:00 UTC  →  weekly-ufc-scraper      scrape completed events from UFCStats
                   →  post-scrape-clean        ETL: FK resolution, type parsing, derived columns
                   →  feature-engineering      rebuild training_data.parquet + feature selection
                   →  retrain                  retrain ML models + commit artefacts

Friday  12:00 UTC  →  upcoming-predictions     scrape next Saturday's card + pre-compute predictions
                                               (Phase 2, pending)
```

**Manual ETL run:**
```bash
python backend/scraper/post_scrape_clean.py           # all phases
python backend/scraper/post_scrape_clean.py --dry-run # preview only
python backend/scraper/validate_etl.py                # standalone validation
```

**Manual model retrain:**
```bash
cd backend && python -m ml.run_train
```

## ML Model Performance

| Subset | Correct | Total | Accuracy | AUC |
|--------|---------|-------|----------|-----|
| All fights (test set) | 597 | 935 | 63.85% | 0.679 |
| Numbered events (PPV) | 226 | 327 | 69.11% | 0.728 |
| Fight Night cards | 371 | 608 | 61.02% | 0.651 |
| Title fights only | 26 | 42 | 61.90% | 0.716 |

Test period: Dec 2023 – Feb 2026. Best model: Random Forest (selected by validation AUC).

## Project Status

### Phase 1 — Core Platform

| Task | Description | Status |
|------|-------------|--------|
| 1 | Database schema & Supabase setup | ✅ Done |
| 2 | Data scraping pipeline (live_scraper.py) | ✅ Done |
| 3 | ETL pipeline (post_scrape_clean.py) | ✅ Done |
| 4 | FastAPI backend (all Phase 1 routes) | ✅ Done |
| 5 | Feature engineering pipeline | ✅ Done |
| 6 | ML model training & serialization | ✅ Done |
| 7 | React frontend foundation | ⏳ Next |
| 8 | Interactive fight predictor UI | ⏳ Pending |
| 9 | Style evolution timeline UI | ⏳ Pending |
| 10 | Fighter endurance dashboard UI | ⏳ Pending |

### Phase 2 — Upcoming Events & Pre-Computed Predictions

| Task | Description | Status |
|------|-------------|--------|
| 11 | Supabase tables: upcoming_events, upcoming_fights, upcoming_predictions | ⏳ Pending |
| 12 | Fighter URL-based matching (UFCStats URL → DB ID) | ⏳ Pending |
| 13 | upcoming_scraper.py | ⏳ Pending |
| 14 | Prediction computation pipeline | ⏳ Pending |
| 15 | run_upcoming.py + GitHub Actions Friday workflow | ⏳ Pending |
| 16 | Pydantic schemas for upcoming endpoints | ⏳ Pending |
| 17-19 | FastAPI upcoming endpoints | ⏳ Pending |
| 20 | Integration testing & monitoring | ⏳ Pending |

## Project Structure

```
ufc_analytics_platform/
├── backend/
│   ├── api/
│   │   ├── main.py             # FastAPI app, middleware, exception handlers
│   │   ├── dependencies.py     # get_db() session dependency
│   │   ├── routers/
│   │   │   └── health.py       # /health, /health/db
│   │   └── v1/
│   │       ├── router.py       # Aggregates all v1 routers
│   │       └── endpoints/      # fighters, fights, events, predictions, analytics
│   ├── core/
│   │   ├── config.py           # Pydantic settings (reads .env)
│   │   ├── logging.py          # Structured JSON logging
│   │   └── middleware.py       # RequestID + Timing middleware
│   ├── db/
│   │   └── database.py         # SQLAlchemy engine + SessionLocal
│   ├── features/               # Feature engineering pipeline
│   │   ├── pipeline.py         # build_prediction_features()
│   │   ├── extractors.py       # get_fights_long_df() — UNION ALL for full history
│   │   └── run_build.py        # Entry point
│   ├── ml/                     # Trained models + evaluation
│   │   ├── train.py            # Training, evaluation, SHAP
│   │   ├── run_train.py        # Entry point
│   │   ├── win_loss_v1.joblib  # Random Forest win/loss classifier
│   │   ├── method_v1.joblib    # Method classifier (KO/TKO, Sub, Dec)
│   │   ├── metrics.json        # Test set metrics
│   │   ├── feature_importance.json
│   │   ├── experiment_log.json # All training runs
│   │   └── shap_summary.json
│   ├── schemas/                # Pydantic v2 request/response models
│   ├── scraper/                # Scrapers + ETL scripts
│   │   ├── live_scraper.py     # Weekly scraper (completed events)
│   │   ├── post_scrape_clean.py
│   │   └── validate_etl.py
│   ├── run_dev.py              # Dev server launcher
│   └── gunicorn.conf.py        # Production server config
├── frontend/                   # React app (Task 7)
├── docs/                       # Technical documentation + analysis
└── .taskmaster/                # Task management (tasks.json, PRDs)
```

## Author

**kabec** — [@kibbbles](https://github.com/kibbbles)

## Acknowledgments

- UFCStats.com for fight data
- Greko scraper for initial data collection

---

**Last Updated:** 2026-03-07
