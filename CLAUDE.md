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

## ✅ COMPLETED: Enhanced UFC Scraper (Task #2)

### Enhanced Scraper Implementation
- **Location**: `backend/scraper/` (3 consolidated files)
- **Schedule**: Weekly on Sunday 6 AM (perfect for UFC's ~2 events/month)
- **Data Coverage**: All available UFC Stats data (1994-2025, 744+ events)
- **Database Integration**: Direct PostgreSQL storage via Supabase

### Key Features Delivered
1. **✅ Rate Limiting & Retry Logic** - 0.5-2 second delays, 3 retry attempts
2. **✅ Comprehensive Error Handling** - Structured logging, progress tracking
3. **✅ Data Validation** - Statistical analysis, format validation, quality reports
4. **✅ Incremental Updates** - Smart state tracking, 14-day lookback window
5. **✅ Database Integration** - Direct PostgreSQL storage with existing models
6. **✅ Weekly Automation** - Sunday 6 AM scheduling optimized for UFC event frequency

### Files Created
- `backend/scraper/enhanced_scraper.py` - Main scraper with all enhancements
- `backend/scraper/database_integration.py` - PostgreSQL integration
- `backend/scraper/scheduler.py` - Weekly automation system

### Usage
```bash
# Start automated weekly scraping
cd backend/scraper
python scheduler.py --daemon

# Manual execution
python scheduler.py --action run-weekly
```

### Database Schema
- **Main Tables**: `fighters`, `events`, `fights`, `fight_stats` (normalized, connected)
- **Raw Tables**: `raw_fighter_details`, `raw_fight_stats` (staging, independent)
- **Integration**: Uses existing SQLAlchemy models, direct Supabase connection

### Next Task: ML Model Development
Ready to proceed with ML model implementation using the comprehensive UFC dataset.

## Database Schema

### Core Tables
```sql
-- Fighters table
fighters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    height_cm FLOAT,
    weight_lbs FLOAT,
    reach_inches FLOAT,
    stance VARCHAR(50),
    date_of_birth DATE
);

-- Events table  
events (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    date DATE,
    location VARCHAR(255),
    venue VARCHAR(255)
);

-- Fights table
fights (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id),
    fighter_a_id INTEGER REFERENCES fighters(id),
    fighter_b_id INTEGER REFERENCES fighters(id),
    weight_class VARCHAR(100),
    winner_id INTEGER REFERENCES fighters(id),
    method VARCHAR(100),
    round INTEGER,
    time_minutes FLOAT,
    title_fight BOOLEAN DEFAULT FALSE
);

-- Fight statistics table (detailed performance metrics)
fight_stats (
    id SERIAL PRIMARY KEY,
    fight_id INTEGER REFERENCES fights(id),
    fighter_id INTEGER REFERENCES fighters(id),
    round INTEGER,
    significant_strikes_landed INTEGER,
    significant_strikes_attempted INTEGER,
    takedowns_landed INTEGER,
    takedowns_attempted INTEGER,
    submission_attempts INTEGER,
    control_time_seconds INTEGER
);
```

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
