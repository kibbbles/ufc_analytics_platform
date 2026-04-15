# Kabe's Maybes — Project History & Architecture

A full account of how this project was built, every major decision made, and how all the pieces connect.

---

## What This Is

**Kabe's Maybes** (`kabes-maybes.vercel.app`) is a data journalism–style UFC analytics platform. It scrapes every UFC event from UFCStats.com, trains machine learning models on historical fight outcomes, and publishes weekly predictions for upcoming cards — complete with a transparency scorecard showing past accuracy.

The aesthetic is deliberately "analyst who loves MMA" rather than commercial product: numbers-forward, no marketing copy, dark mode by default.

---

## How It Started (Commits: `d1e4903` → `8ceb197`)

The project began as a pure data scraping exercise. The earliest commits show an evolving attempt to get UFC data from UFCStats.com — a site with no official API. The first approach used a third-party scraper (`scrape_ufc_stats` added as a git submodule, then immediately removed when it proved broken).

Key early decisions:
- **PostgreSQL on Supabase** — chosen for its free tier, built-in SQL editor, and direct `psycopg2` connection. No ORM at this stage — raw SQL inserts.
- **6-table schema** — `event_details`, `fighter_details`, `fight_details`, `fight_results`, `fighter_tott` (Tale of the Tape), `fight_stats` — mirroring exactly what UFCStats exposes.
- **GitHub Actions** for automation from day one — weekly scrape runs on Sunday 18:00 UTC, keepalive pings to prevent Supabase from sleeping.
- **VARCHARs everywhere for IDs** — UFCStats uses hex-style IDs in URLs (e.g. `/fighter-details/3b27d3e9`). These were preserved as-is rather than converting to integers, because they're the natural join keys between the scraper output and the database.

The scraper went through many iterations (`full_historical_scraper`, then `live_scraper.py`) before settling. The final `live_scraper.py` handles all 6 tables in one run.

---

## Data & ETL Pipeline (Task 3 — `2b689af` → `5e1144b`)

After the initial data load (756 events, 4,449 fighters, 8,482 fights, 39,912 fight stats), the raw data was messy:
- Stats stored as strings like `"17 of 37"` (sig strikes landed / attempted)
- Control time as `"3:42"` (not seconds)
- Heights as `"6' 1\""`, weights as `"185 lbs."`
- `"--"` placeholders wherever data was missing
- No foreign key relationships populated (fight_stats had no `fighter_id`)
- No derived columns (weight class, title fight flags)

**ETL pipeline** (`post_scrape_clean.py`) runs 4 phases in sequence:
1. **FK Resolution** — populate `fighter_a_id`, `fighter_b_id` on fight_details; `fighter_id`/`opponent_id` on fight_results; `fighter_id` on fight_stats (via fuzzy name matching with rapidfuzz, WRatio score ≥88)
2. **Quality Cleanup** — NULL out `"--"` placeholders, strip trailing spaces from METHOD
3. **Type Parsing** — parse `"X of Y"` strings into `sig_str_landed`/`sig_str_attempted` integers; `CTRL` → `ctrl_seconds`; height/weight/reach/dob into typed numeric columns
4. **Derived Columns** — `weight_class` (inferred from WEIGHTCLASS text), `is_title_fight`, `is_interim_title`, `is_championship_rounds`

This runs automatically after every weekly scrape via GitHub Actions chaining: scraper → ETL → feature engineering → model retrain.

**Critical query pattern discovered during ETL**: `fight_results` has one row per fight, where `fighter_id` = winner and `opponent_id` = loser. A naive `WHERE fighter_id = :id` returns wins only — losses are invisible. All fighter history queries use an OR pattern (`WHERE fighter_id = :id OR opponent_id = :id`).

---

## ML Models (Task 6 — `aee098c`)

**Feature engineering**: 30+ features built from fighter differentials:
- Physical: height diff, reach diff, weight diff, age diff
- Experience: UFC fights diff, win streak diff, finish rate diff
- Striking (rolling 5-fight windows): sig strike accuracy diff, head/body/leg distribution
- Grappling: takedown % diff, submission attempt rate diff, control time diff
- Derived: days since last fight, career KO% diff, career sub% diff

**Two-model ensemble**:
- **Random Forest** (primary) — `sklearn.ensemble.RandomForestClassifier`, trained on fights from Jan 2017 onward (earlier fights lack reliable stat coverage)
- **XGBoost** — used as a cross-check; RF ensemble is the production predictor

**Method prediction**: separate multi-class model predicting KO/TKO vs Submission vs Decision probability

**Training data**: built into `training_data.parquet` by `feature_engineering.py`, auto-rebuilt by GitHub Actions after each ETL run, then `retrain.yml` retrains and commits updated model artifacts

**Validation**: 62.4% overall accuracy on test set (Jan 2022 → present, 1716 fights). 84.2% accuracy on high-confidence predictions (≥65% win probability) — this is the headline number.

**Conviction bucket analysis** (added Mar 2026): The model scorecard originally grouped low-conviction predictions into a single "Under 20%" bucket. Splitting it into "Under 10%" and "10–20%" revealed a meaningful gradient:

| Conviction | Accuracy |
|------------|----------|
| Under 10% | 56.9% |
| 10–20% | 63.5% |
| 20–30% | — |
| 30%+ | — |

Conviction = `(max_win_prob − 0.5) × 2` — the model's normalized distance from a coin flip. The 6.6pp gap between the two lowest buckets confirms the score captures genuine signal even in the uncertain range. The scorecard UI now shows all four buckets.

---

## Backend — FastAPI (Task 4 → Tasks 11–19)

**Tech choice**: FastAPI was chosen over Flask for automatic OpenAPI docs (invaluable for frontend development) and Pydantic v2 validation.

**Structure**:
```
backend/
├── api/
│   ├── main.py              # App, CORS, middleware, exception handlers
│   ├── dependencies.py      # get_db() session dependency
│   └── v1/endpoints/        # One file per feature area
│       ├── fighters.py
│       ├── fights.py
│       ├── events.py
│       ├── predictions.py   # POST /predictions/fight-outcome
│       ├── upcoming.py      # Upcoming events/fights/predictions
│       ├── past_predictions.py
│       └── analytics.py
├── schemas/                 # Pydantic v2 response models
├── features/                # Feature extraction for ML inference
│   └── extractors.py        # get_fights_long_df(), build_feature_vector()
└── scraper/                 # All data pipeline scripts
```

**Middleware**: `RequestIDMiddleware` (adds `X-Request-ID` header), `TimingMiddleware` (logs request duration)

**Key design decisions**:
- All raw SQL via SQLAlchemy `text()` — no ORM models. The schema is legacy/append-only; defining ORM models would add maintenance burden with no benefit.
- Pydantic schemas defined separately from DB access — clean separation between "what the DB returns" and "what the API exposes"
- `get_db()` yields a session per request, closes on completion

**Important FastAPI routing lesson**: `GET /fights` must be registered *before* `GET /fights/{fight_id}` in the router. FastAPI matches routes in registration order — if `/{fight_id}` is first, the literal path `/fights` gets treated as a fight ID.

---

## Hosting Odyssey

The backend went through three hosting platforms before settling:

| Stage | Platform | Reason for Change |
|-------|----------|-------------------|
| Initial | Local only | Development |
| v1 | **Fly.io** | First deployment attempt; Docker-based, generous free tier |
| v2 | **Render** | Fly.io free tier was eliminated; Render offers free Web Services |
| v3 | **Google Cloud Run** | Render free tier spins down after 15 min inactivity (~30s cold start). Cloud Run has faster cold starts, is more production-grade, and integrates with GCP Secret Manager |

**Frontend**: always Vercel. Connected directly to the GitHub repo — every push to `main` triggers a deploy. Set `Root Directory = frontend` in Vercel settings. One env var: `VITE_API_BASE_URL`.

**Database**: always Supabase (PostgreSQL). Free tier, direct psycopg2 connection string, no changes needed as backend hosting changed.

Current production stack:
```
Browser → Vercel (React SPA, CDN) → Google Cloud Run (FastAPI, Docker) → Supabase (PostgreSQL)
```

---

## Frontend — React (Task 7 → Tasks 21–23)

**Tech choices**:
- **React 19 + TypeScript 5.9** via Vite scaffold
- **Tailwind CSS v4** — CSS-first configuration (`@import "tailwindcss"` + `@theme` block in `index.css`; no `tailwind.config.js`)
- **React Router v6** — all pages lazy-loaded (code-split per route)
- **Recharts** for standard charts, **Axios** for API calls
- **Context API + useReducer** for global state (theme, no auth needed)

**Design system**: All colors, fonts, and shadows as CSS custom properties in `frontend/src/index.css` `@theme` block. Components never hardcode values — they reference `var(--color-accent)` etc.

**Dark / light mode**: `ThemeProvider` reads `localStorage` on mount, falls back to `prefers-color-scheme`. Toggle in header. Both modes equally polished.

---

## Page-by-Page History

### Home (`/`)
Started as a placeholder. Grew to host the **ModelScorecard** — the most complex component on the site. Scorecard shows:
- Compact accuracy stats: `62.4% accurate · 1071/1716 fights (84.2% when ≥65% confident)`
- One-sentence model description
- **Events tab**: browse all past events the model was evaluated on, with per-event accuracy, search + year filter + pagination
- **Fight Search tab**: search any fighter name to see all predictions involving them; defaults to 10 most recent fights

### Upcoming (`/upcoming`)
The centrepiece. Accordion-style: event rows expand to show the full fight card. Per-fight row shows fighter names, win probability bar, method chip. Design iterations visible in git history — went through many layouts (centered name, arrows, badges) before landing on the current clean version where:
- Badges (NEXT / numbered event) are always on their own line above event name
- Winner is indicated by full-contrast name vs muted loser — no arrow needed
- Date + location on line 2, bout count on line 3 — consistent wrapping on all screens

Fight rows link to the matchup page.

### Fight Matchup (`/upcoming/fights/:id` and `/past-predictions/fights/:id`)
Dedicated page per fight. Same layout for both upcoming and past predictions. Built to mirror how you'd read a fight preview:

```
[Fighter A]          [Fighter B]
     Win probability bar (dominant visual)
     Method: KO/TKO 32% | Sub 18% | Dec 50%

     Tale of the Tape (height / weight / reach / age / stance)
     Striking (sig strikes, accuracy, head/body/leg)
     Grappling (TD%, sub attempts, control time)
     Top model features (what drove the prediction)
     Recent fights for each fighter
```

For **past predictions**, an additional `ActualResultCard` appears at the top:
- Green border + "✓ Correct" — model called it right
- Red border + "✗ Incorrect" — model was wrong
- Amber border + "~ Upset" — model was wrong AND the underdog won

### Events (`/events`)
Historical events list. Added Completed / Upcoming toggle (reuses `/upcoming` data) and event name search filter. Clicking an event goes to the event detail page (fight card for that event).

### Past Prediction Event (`/past-predictions/events/:event_id`)
Shows all model predictions for a completed event. Each row: ✓/✗/~ indicator, Fighter A vs Fighter B, predicted winner + confidence + method, actual winner + method. Rows are clickable links to the fight matchup page.

### Fighter Lookup (`/fighters` + `/fighters/:id`)
List page with search. Detail page shows tale of the tape, career record (W-L-D), fight history table.

### About (`/about`)
Personal intro page. Casual tone. Explains the project, the data source, the model approach, the tech stack.

---

## How a User Click Triggers the Full Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│  USER ACTION                                                        │
│  e.g. opens /upcoming, clicks "UFC 315" accordion row               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  REACT (Vercel CDN)                                                 │
│                                                                     │
│  UpcomingPage.tsx                                                   │
│  └── pastPredictionsService / upcomingService                       │
│      └── apiClient.get('/upcoming/events/{id}')   ← Axios           │
│          └── VITE_API_BASE_URL + '/upcoming/events/{id}'            │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  HTTP GET (JSON)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FASTAPI (Google Cloud Run — Docker container)                      │
│                                                                     │
│  api/v1/endpoints/upcoming.py                                       │
│  └── get_upcoming_event_detail(event_id, db)                        │
│      ├── SQLAlchemy Session                                         │
│      └── text("SELECT ... FROM upcoming_fights                      │
│               JOIN upcoming_predictions ...")                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  SQL query (psycopg2 / SQLAlchemy)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  POSTGRESQL (Supabase)                                              │
│                                                                     │
│  upcoming_fights  (scraped from UFCStats /upcoming)                 │
│  upcoming_predictions  (pre-computed by compute_predictions.py)     │
│  fighter_details, fighter_tott  (historical fighter data)           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  Result rows
                           ▼
                  FastAPI serialises to JSON
                  (Pydantic v2 response model)
                           │
                           ▼
                  Axios parses response
                  React re-renders accordion
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  USER SEES                                                          │
│  Fight card expanded — fighter names, win% bar, method chip         │
│  Clicks a fight row → navigates to /upcoming/fights/:id             │
└─────────────────────────────────────────────────────────────────────┘
```

### Deeper: How a Prediction is Generated (Weekly Automation)

```
Saturday 15:00 UTC
       │
       ▼
GitHub Actions: upcoming-predictions.yml
       │
       ├── run_upcoming.py
       │   ├── upcoming_scraper.py
       │   │   ├── GET ufcstats.com/statistics/events/upcoming
       │   │   ├── Parse event rows → upcoming_events (upsert)
       │   │   ├── Parse fight rows → upcoming_fights (upsert)
       │   │   └── Match fighter URLs → fighter_details.id (FK)
       │   │
       │   └── compute_predictions.py
       │       ├── For each upcoming_fight with both fighter FKs:
       │       │   ├── features/extractors.py → build_feature_vector()
       │       │   │   ├── Query fight_stats for rolling 5-fight window
       │       │   │   ├── Query fighter_tott for physical attributes
       │       │   │   └── Compute 30 differential features
       │       │   ├── Load trained RandomForest model (models/*.pkl)
       │       │   ├── model.predict_proba(features) → win_prob_a, win_prob_b
       │       │   ├── method_model.predict_proba() → ko_tko, sub, dec
       │       │   └── UPSERT into upcoming_predictions
       │       └── Fights with NULL fighter FK → skipped (debuting fighters)
       │
Sunday 14:00 UTC
       │
       ▼
weekly-ufc-scraper.yml → post-scrape-clean.yml → feature-engineering.yml → retrain.yml
(completed events flow into training data, model auto-retrains)
```

---

## Database Schema (Final State)

```
event_details (756 rows)
    id VARCHAR(6) PK
    "EVENT", "URL", date_proper, "LOCATION"

fighter_details (4,449 rows)
    id VARCHAR(6) PK
    "FIRST", "LAST", "NICKNAME", "URL"

fight_details (8,482 rows)
    id VARCHAR(6) PK
    event_id → event_details
    fighter_a_id, fighter_b_id → fighter_details
    "BOUT", "URL"

fight_results (8,482 rows — one per fight)
    id VARCHAR(6) PK
    fight_id → fight_details, event_id → event_details
    fighter_id → fighter_details (WINNER)
    opponent_id → fighter_details (LOSER)
    "METHOD", "ROUND", "TIME", "WEIGHTCLASS"
    fight_time_seconds, total_fight_time_seconds (parsed)
    weight_class, is_title_fight, is_interim_title (derived)

fighter_tott (4,435 rows)
    id VARCHAR(6) PK
    fighter_id → fighter_details
    height_inches, weight_lbs, reach_inches, dob_date (parsed)
    "STANCE"

fight_stats (39,912 rows — one per fighter per round)
    id VARCHAR(6) PK
    fight_id → fight_details, fighter_id → fighter_details
    sig_str_landed, sig_str_attempted, ctrl_seconds, kd_int (parsed)
    "ROUND", "KD", "TD", "SUB.ATT", "REV."

-- Upcoming / prediction tables
upcoming_events    (event_name, date_proper, location, ufcstats_url)
upcoming_fights    (event_id, fighter_a/b_id, weight_class, is_title_fight)
upcoming_predictions (fight_id UNIQUE, win_prob_a/b, method probs, features_json JSONB)

-- Past predictions (model scorecard)
past_predictions   (fight_id VARCHAR(8), event_id VARCHAR(6), all prediction + actual columns)
```

---

## UFC Stats Assistant — Natural Language Chat (Task 30)

The most technically distinctive feature: a floating chat widget on every page that lets users ask natural-language questions about fighters and fights, answered from live database queries.

**How it works (text-to-SQL pipeline)**:
1. User types a question (e.g. "How did the Adesanya vs Pyfer fight end?")
2. Frontend sends `POST /api/v1/chat` with `{ question, history }`
3. Backend sends the question + conversation history + a detailed `SCHEMA` system prompt to **Groq** (llama-3.3-70b-versatile) — the fastest publicly available LLM, chosen for low latency
4. LLM returns a SQL query against the UFC database
5. Backend executes the SQL on Supabase, passes the results back to the LLM
6. LLM formats a natural-language answer
7. Response includes the answer, the raw SQL (collapsible in the UI), and a status flag

**Frontend** (`ChatWidget` + `ChatPanel`):
- Fixed bottom-right bubble on every page (same row as the odds calculator button)
- Click-outside-to-close, chat history preserved within a session
- User messages: red right-aligned bubbles. Assistant: grey left-aligned bubbles
- Collapsible "View SQL" block under each answer for transparency
- Typing indicator (bouncing dots) while waiting
- Rate-limit banner + disabled input once daily limit is reached
- Mobile-first: `w-[calc(100vw-24px)] max-w-[360px]` — fits any phone screen

**Rate limiting**: 20 questions per IP per day (tracked in-memory on the backend), protecting the Groq API key from abuse.

**SCHEMA system prompt engineering**: The hardest part. The LLM needs to know the full table structure, column names (many are quoted uppercase e.g. `fd."LAST"`), join patterns, and dozens of UFC-specific rules. Key rules developed iteratively:
- Fighter first names: never assume if uncertain — search by `LAST` name only
- ROUND column: stores both `'1'` and `'Round 1'` formats — filter with `NOT ILIKE '%total%'` not regex
- fight_results has one row per fight: always use `WHERE fighter_id = :id OR opponent_id = :id`
- Chronological ordering: NEVER use id columns (alphanumeric, no time ordering) — always use `date_proper`
- ESPN MMA glossary: ~60 fighter nicknames mapped to real names, weight class aliases, method synonyms

**Production secret management**: GROQ_API_KEY is stored as a GitHub Actions secret and injected into the Cloud Run environment via `--set-env-vars` during deploy. Cloud Run secrets were attempted first (Secret Manager) but the deployer service account lacked the required IAM roles.

---

## Key Engineering Decisions & Lessons

| Decision | Why |
|----------|-----|
| Raw SQL via `text()` instead of ORM models | Schema is append-only and legacy-shaped; ORMs would add complexity without benefit |
| VARCHAR IDs (not integers) | UFCStats hex IDs are natural PKs; converting to int would break scraper FK resolution |
| fight_id = VARCHAR(8) in past_predictions | Fight IDs are 8-char hex (e.g. `3738135e`); original table used VARCHAR(6) which caused truncation |
| Pydantic v2 for all API responses | Automatic validation, free OpenAPI docs, type-safe frontend |
| Axios interceptor error normalisation | FastAPI 422 errors return `detail` as array; guard `typeof rawDetail === 'string'` prevents `[object Object]` |
| `useRef` for debounce timers | `setTimeout` in a closure captures stale state; ref persists across renders |
| `div+onClick` instead of nested `<Link>` | `<a>` inside `<a>` is invalid HTML; browsers break the outer link unpredictably |
| `Promise.resolve(null)` in `useApi` | Skip API call when a tab is inactive without breaking the hook's dependency array |
| Render free tier accepted | Cold start ~30s is fine for a portfolio project; upgrade path is Firebase/Cloud Run |
| FastAPI route order matters | `/fights` must be registered before `/fights/{fight_id}` — FastAPI matches in registration order |

---

## Analytics Page — "How the UFC Has Changed"

The analytics page (`/analytics`) is the most data-dense page on the site. It runs a single endpoint — `GET /api/v1/analytics/style-evolution` — that executes 8 aggregate queries and returns them in one JSON response. The page has no user-submitted data; it's a read-only window into UFC history.

### The 8 sections and their queries

| Section | Chart component | Query grain | Raw tables touched |
|---|---|---|---|
| How fights end | `FinishRateChart` | year (× weight_class optional) | `fight_results`, `event_details` |
| How fighters fight | `FighterOutputChart` | year (× weight_class optional) | `fight_stats`, `fight_details`, `fight_results`, `event_details` |
| When finishes happen | `RoundDistributionChart` | year (× weight_class optional) | `fight_results`, `event_details` |
| Finish rate by weight class | `WeightClassHeatmap` | year × weight_class (all divisions) | `fight_results`, `event_details` |
| Athlete body sizes | `PhysicalStatsChart` | year × weight_class (all divisions) | `fight_results`, `event_details`, `fighter_tott` |
| Fighter age by weight class | `AgeByWeightClassChart` | year × weight_class (all divisions) | `fight_results`, `event_details`, `fighter_tott` |
| Fighting style (snapshot) | `FighterStatsByWeightClassTable` | weight_class only | `fight_results`, `fighter_tott` |
| Fighting style (time series) | `FighterStatsTimeSeriesChart` | year × weight_class (all divisions) | `fight_stats` self-join, `fight_results`, `event_details` |

The heaviest query is the style time series (Query 8) — it self-joins `fight_stats` (39,912 rows) to itself to derive opponent-based metrics (strikes absorbed per minute, strike defense, TD defense). Query 2 (fighter output) is the second heaviest: nested aggregation per-fighter per-fight across all of fight_stats.

### Partial year handling

The current year (2026) is included in all queries but flagged as `is_partial_year = True` in the API response. Charts render the current year's data point as an open circle (hollow dot) rather than a solid point, with a footnote "○ Open circle = 2026 (partial year, fights still ongoing)." This pattern is consistent across `FinishRateChart`, `PhysicalStatsChart`, `AgeByWeightClassChart`, and `FighterStatsTimeSeriesChart`.

### Weight class filter

A sticky filter bar at the top of the page lets users pick a single weight class. When selected:
- Queries 1, 2, 3 add `AND fr.weight_class = :weight_class` — the charts narrow to that division's history.
- Queries 4, 5, 6, 7, 8 always return all divisions regardless — the heatmap, physical stats, and age charts show all divisions and the filter is noted in the UI as not applying.
- The "Fighting style" section switches from the snapshot table (all divisions) to a time series chart for the selected division.

### Materialized views (added April 2026)

**Problem:** With `min-instances=0` on Cloud Run, cold starts meant the analytics page ran all 8 queries fresh against 8,000+ fight results and 39,000+ fight stats rows on every visit. Even with `min-instances=1`, each page load fired 8 sequential round trips to Supabase (~40–80ms each).

**Insight:** The data has a natural immutability boundary. Once a year ends and the ETL runs, that year's aggregated results never change. 2025 and everything before it is frozen permanently. Only the current partial year (2026) changes week-to-week.

**Solution:** 8 materialized views defined in `backend/db/migrations/003_materialized_views.sql`:

```
mv_finish_rates         — ~400 rows  (year × weight_class, incl. all-divisions NULL rows)
mv_fighter_output       — ~140 rows  (2015+, year × weight_class)
mv_round_distribution   — ~400 rows  (year × weight_class)
mv_heatmap              — ~400 rows  (year × weight_class, UFC divisions only)
mv_physical_stats       — ~300 rows  (year × weight_class, HAVING >= 5 fighters)
mv_age_data             — ~300 rows  (year × weight_class, HAVING >= 5 fighters)
mv_fighter_stats_by_wc  —  ~13 rows  (weight_class only, career snapshot)
mv_style_stats          — ~140 rows  (year × weight_class)
```

Total storage: well under 1 MB. On load, the endpoint does `SELECT * FROM mv_xxx WHERE ...` — instant reads on tiny pre-computed tables instead of full aggregations over raw data.

**Refresh:** `post_scrape_clean.py` Phase 5 (added alongside the views) calls `REFRESH MATERIALIZED VIEW` for all 8 views after Phase 4 completes. This runs every Sunday after the weekly scrape and ETL, so the views are always current within one week. The current year's rows are at most 6 days stale between refreshes — acceptable for an analytics showcase.

**Cold start behaviour:** Unlike in-process Python caching (which resets on every container restart), materialized views live in Supabase. A cold start doesn't matter — the pre-computed data is always there waiting, regardless of whether the container was running.

---

## What's Next (Post-MVP)

1. **Fight Outcome Predictor (Task 8)**: Interactive sliders — adjust fighter attributes and see win probability update in real time.

2. **Style Evolution Timeline (Task 9)**: Finish rate trends by year and weight class. Are KOs getting rarer? Is wrestling dominant now?

3. **Fighter Endurance Dashboard (Task 10)**: Round-by-round performance profiles. Which fighters fade in the championship rounds?

4. **Chat improvements**: Streaming responses, richer answer formatting (markdown tables), session persistence across page navigation.

5. **Custom domain**: `kabesmaybes.com` or similar.
