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
**⚠️ INCOMPLETE DATA - Needs Historical Backfill**
- **Current State**: 756 events, 4,429 fighters, 5,644 fight results
- **Issue**: Greko CSV had partial fighter histories (e.g., Petr Yan shows 8 fights instead of 25)
- **Date Range**: 1994-03-11 to 2025-12-06 (sparse coverage for many fighters)
- **Root Cause**: Initial CSV import was incomplete/sampled data

### Available Scrapers
- `backend/scraper/live_scraper.py` - For NEW events only (future updates)
- `backend/scraper/bulk_scrape_career_stats.py` - Career stats scraper
- `backend/scraper/bulk_scrape_physical_stats.py` - Physical stats scraper
- **NEEDED**: Historical backfill scraper to get complete fighter records

### Database Schema (Current)
```sql
-- Core tables
event_details (756 rows)       -- UFC events
fighter_details (4,429 rows)   -- Fighter profiles
fight_details (varies)         -- Fight matchups
fight_results (5,644 rows)     -- Fight outcomes (INCOMPLETE)
fighter_tott (4,435 rows)      -- Tale of the Tape
fight_stats (varies)           -- Round-by-round stats
```

### Automation
- `backend/scraper/scheduler.py` - Weekly automation for live_scraper
- Currently only monitors NEW events, not historical gaps


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

### Relationship Status
- ✅ **Working**: event_details ↔ all tables via event_id
- ✅ **Working**: fight_details ↔ fight_results via fight_id  
- ✅ **Working**: fighter_details ↔ fighter_tott via fighter_id
- ⚠️ **Partial**: fight_details ↔ fight_stats (64% have fight_id)
- ❌ **Missing**: fight_stats → fighter_details (only text names)
- ❌ **Missing**: fight_details → fighter_details (needs parsing BOUT)

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
