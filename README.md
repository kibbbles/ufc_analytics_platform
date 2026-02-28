# UFC Analytics Platform

ML-powered UFC fight analytics platform with interactive predictions and visualizations. Built to demonstrate production-level data science and software engineering skills.

## Features

- **Fight Outcome Predictor**: Interactive ML predictions with adjustable fighter parameters
- **Style Evolution Timeline**: Visualize how fighting styles evolved throughout UFC history
- **Fighter Endurance Dashboard**: Round-by-round performance analysis and cardio predictions

## Tech Stack

### Backend
- **Framework**: FastAPI 0.115.5
- **Database**: PostgreSQL (Supabase)
- **ML**: XGBoost, scikit-learn
- **ORM**: SQLAlchemy 2.0 (raw SQL queries, no ORM model layer)
- **Server**: Uvicorn (dev) / Gunicorn + UvicornWorker (production)

### Frontend (Coming Soon)
- **Framework**: React 18 + TypeScript
- **Visualization**: Recharts, D3.js
- **Styling**: Tailwind CSS

### Data Pipeline
- **Source**: UFCStats.com — 756 events (1994–2025), 4,449 fighters, 8,482 fights, 39,912 fight stats
- **Processing**: pandas + numpy with automated ETL pipeline
- **Storage**: PostgreSQL with 6 tables, fully resolved FK relationships

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend, when built)
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
# or: uvicorn api.main:app --reload --port 8000
```

**Production server:**
```bash
cd backend
gunicorn api.main:app -c gunicorn.conf.py
```

API: `http://localhost:8000`
Docs: `http://localhost:8000/docs`

## API Endpoints

All data endpoints are versioned under `/api/v1`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/health/db` | DB readiness check (503 if unreachable) |
| GET | `/api/v1/fighters` | Paginated fighter list (`?search=`, `?page=`, `?page_size=`) |
| GET | `/api/v1/fighters/{id}` | Fighter profile: physical stats, career averages, record |
| GET | `/api/v1/fights` | Paginated fight list (filters: event, fighter, weight class, method) |
| GET | `/api/v1/fights/{id}` | Fight detail + round-by-round stats |
| GET | `/api/v1/events` | Paginated event list (`?year=`) |
| GET | `/api/v1/events/{id}` | Event detail + full fight card |
| POST | `/api/v1/predictions/fight-outcome` | Win probability prediction (ML stub until Task 6) |
| GET | `/api/v1/analytics/style-evolution` | Finish rates by year (`?weight_class=`) |
| GET | `/api/v1/analytics/fighter-endurance/{id}` | Round-by-round performance profile |

## Data Updates

Data is kept current via GitHub Actions:

**Weekly scrape** (every Sunday):
```bash
cd backend/scraper
python live_scraper.py
```

**Manual ETL run:**
```bash
python backend/scraper/post_scrape_clean.py
```

## Project Status

| Task | Description | Status |
|------|-------------|--------|
| 1 | Database schema | ✅ Done |
| 2 | Data scraping pipeline | ✅ Done |
| 3 | ETL pipeline | ✅ Done |
| 4 | FastAPI backend | ✅ Done |
| 5 | ML feature engineering | ⏳ Next |
| 6 | ML models | ⏳ Planned |
| 7–8 | Analytics (style evolution, endurance) | ⏳ Planned |
| 9 | React frontend | ⏳ Planned |
| 10 | Deployment | ⏳ Planned |

## Project Structure

```
ufc_analytics_platform/
├── backend/
│   ├── api/
│   │   ├── main.py           # FastAPI app, middleware, exception handlers
│   │   ├── dependencies.py   # get_db() session dependency
│   │   ├── routers/
│   │   │   └── health.py     # /health, /health/db
│   │   └── v1/
│   │       ├── router.py     # Aggregates all v1 routers
│   │       └── endpoints/    # fighters, fights, events, predictions, analytics
│   ├── core/
│   │   ├── config.py         # Pydantic settings (reads .env)
│   │   ├── logging.py        # Structured JSON logging
│   │   └── middleware.py     # RequestID + Timing middleware
│   ├── db/
│   │   └── database.py       # SQLAlchemy engine + SessionLocal
│   ├── schemas/              # Pydantic request/response models
│   ├── scraper/              # Live scraper + ETL scripts
│   ├── ml/                   # ML models (Task 6)
│   ├── main.py               # Uvicorn entry point re-export
│   ├── run_dev.py            # Dev server launcher
│   └── gunicorn.conf.py      # Production server config
├── frontend/                 # React app (Task 9)
├── docs/                     # Technical documentation
└── .taskmaster/              # Task management
```

## Author

**kabec** — [@kibbbles](https://github.com/kibbbles)

## Acknowledgments

- UFCStats.com for fight data
- Greko scraper for initial data collection

---

**Last Updated:** 2026-02-28
