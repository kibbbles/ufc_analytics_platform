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
- **Framework:** FastAPI 0.104.1
- **Database:** PostgreSQL (Supabase for deployment)
- **ML Libraries:** scikit-learn, XGBoost, pandas, numpy
- **API Documentation:** Automatic OpenAPI/Swagger generation
- **Authentication:** None required (public analytics platform)

### Frontend Stack
- **Framework:** React 18 with TypeScript
- **Visualization:** Recharts for standard charts, D3.js for custom visualizations
- **State Management:** React Context API
- **Styling:** Tailwind CSS
- **HTTP Client:** Axios for API communication

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
- `.github/workflows/scraper.yml` — weekly scrape (live_scraper.py)
- `.github/workflows/post-scrape-clean.yml` — ETL + validation, triggered after scrape succeeds

### Available Scrapers
- `backend/scraper/live_scraper.py` — Active scraper; writes to all 6 tables (events, fights, results, stats, fighter profiles, tott)
- `backend/scraper/bulk_scrape_career_stats.py` — Career stats scraper (manual use)
- `backend/scraper/bulk_scrape_physical_stats.py` — Physical stats scraper (manual use)

### Database Schema (Current)
```sql
-- Core tables
event_details (756 rows)       -- UFC events
fighter_details (4,449 rows)   -- Fighter profiles
fight_details (~8,482 rows)    -- Fight matchups
fight_results (8,482 rows)     -- Fight outcomes + typed/derived columns
fighter_tott (4,435 rows)      -- Tale of the Tape + typed columns
fight_stats (39,912 rows)      -- Round-by-round stats + typed columns
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
- `.github/workflows/scraper.yml` — Weekly scrape via live_scraper.py (GitHub Actions)
- `.github/workflows/post-scrape-clean.yml` — ETL cleanup + validation, auto-triggered after scrape


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
