# Tilburg Steps vs. Current Project Status

_Reference: Turgut (2021), Tilburg University — "Machine Learning approach to predicting MMA matches"_

---

## Phase 1: Athletes / Fighter Cleaning

| Tilburg Step | Our Status | Notes |
|---|---|---|
| Convert `--` to NaN | **Done** | ETL Phase 2 (`post_scrape_clean.py`) |
| Fix data types — DOB string → DateTime | **Done** | ETL Phase 3 (`dob_date` column) |
| Fix data types — height string → inches | **Done** | ETL Phase 3 (`height_inches` column) |
| Fix data types — weight string → float | **Done** | ETL Phase 3 (`weight_lbs` column) |
| Fix data types — reach string → float | **Done** | ETL Phase 3 (`reach_inches` column) |
| Fix data types — percentages string → float | **Done** | ETL Phase 3 (`str_acc`, `td_acc`, etc.) |
| Remove Super Heavyweight athletes (>265 lbs) | **Not done** | Very few fighters; minor impact |
| Remove non-UFC athletes (never fought in UFC) | **N/A** | Our DB only contains UFC fighters |
| Handle duplicate fighter names | **Done** | ETL Phase 1 (FK resolution by URL) |
| Impute reach / height using MICE | **Partial** | We use median imputation in the sklearn pipeline, not MICE; different method, same intent |

---

## Phase 2: Matches / Fights Cleaning

| Tilburg Step | Our Status | Notes |
|---|---|---|
| Convert date strings → DateTime | **Done** | `date_proper DATE` column |
| TD%/sig_str% = 0 when no attempts made | **Done** | ETL Phase 2 fills these with 0 |
| Convert `--` and empty → NaN | **Done** | ETL Phase 2 |
| Convert ctrl time "MM:SS" → seconds | **Done** | ETL Phase 3 (`ctrl_seconds` column) |
| Mark matches where fighter not in athlete DB | **Done (differently)** | FK resolution tracks unresolved fighters |
| Remove Super Heavyweight + Open Weight matches | **Not done** | A handful of fights (≤10); very minor |
| Analyze and remove irrelevant columns (referee, details) | **N/A** | We never include referee in features |
| Data cutoff — exclude before Oct 1998 | **Not done** | We include fights back to March 1994; ~130 extra fights with heavy missing data |

---

## Phase 3: Feature Engineering

| Tilburg Step | Our Status | Notes |
|---|---|---|
| **Age at fight** (fight date − DOB) | **Done** | `time_features.py` → `age_at_fight` (days) |
| **Records** — wins, losses, draws before fight | **Partial** | We have `experience_diff`, `win_rate_diff`; we do NOT store raw W/L/D counts per fighter separately |
| **Win rate** (wins / total fights, point-in-time) | **Done** | `differentials.py` → `win_rate_diff` |
| **Win streak** (UFC-only, backward iteration) | **Done** | `differentials.py` → `win_streak_diff` |
| **Loss streak** | **Done** | `differentials.py` → `loss_streak_diff` — goes beyond Tilburg |
| **Average fight stats per minute (backward iteration, all prior fights)** | **Different** | We use rolling windows (last 3/5/7 fights) instead of all-time career averages. Rolling windows are richer but are **NOT normalized per minute** — we aggregate raw totals |
| **Per-minute normalization of stats** | **Not done** | Tilburg divided all stats by fight duration in minutes. We use raw totals per fight period. This is a real gap, though rolling windows partially compensate |
| **Opponent quality features** | **Done (extra)** | `opponent_quality.py` — Tilburg had none of this |
| **Style features** (striking ratio, grappling ratio, finish rate, etc.) | **Done (extra)** | `style_features.py` — Tilburg had none of this |
| **Days since last fight / career length / days in weight class** | **Done (extra)** | `time_features.py` — Tilburg had none of these |

---

## Phase 4: Further Processing

| Tilburg Step | Our Status | Notes |
|---|---|---|
| Remove matches where fighter not in athletes DB | **Done** | Handled by FK resolution and `fighter_id IS NOT NULL` filter in extractors |
| **Remove rows with any NaN** after feature engineering | **Not done** | We use median imputation inside the sklearn pipeline instead of hard-dropping. Tilburg removed ~2% of rows this way. Different philosophy. |
| Remove draws and No Contests | **Done** | `fighter_a_wins.notna()` filter in `pipeline.py` |
| **Remove debut fights** (either fighter's first UFC fight) | **Not done** | This is the most important gap. Tilburg explicitly dropped all fights where either fighter had zero prior fights. We currently include debuts, where all feature values are zero — adding noise |
| **Perspective swap** — randomly swap fighter1/fighter2 in 50% of rows | **Done** | `pipeline.py` with `seed=42`, negates all diff columns |
| Compute A-B differentials for stats | **Done** | All feature modules output diffs via `_add_fighter_diffs()` |

---

## Phase 5: Final Dataset and Split

| Tilburg Step | Our Status | Notes |
|---|---|---|
| Final row count: **3,925 fights** | **8,409 fights** | We have ~2× the data because: (a) 5 more years of fights, (b) we include debuts and pre-2013 fights that Tilburg excluded |
| Feature count: **35 features** | **25 selected features** | Different feature set — ours has rolling windows, time features, opponent quality; Tilburg has raw records |
| Temporal split, no shuffle — test set = most recent | **Done** | `train.py` sorts by `event_date` before splitting |
| 80/20 train/test, then 80/20 train/val | **Done (different ratio)** | We use 70/15/15 instead of 64/16/20 — minor |
| StandardScaler on numeric features | **Done** | Inside sklearn Pipeline |
| Random search for hyperparameters | **Partial** | We used fixed hyperparameters with manual tuning, not RandomizedSearchCV |

---

## Summary of Genuine Gaps

These are the only things Tilburg did that we haven't done:

| Gap | Severity | Fix |
|---|---|---|
| **Debut fights not removed** | High | Drop fights where either fighter has 0 prior fights in `build_training_matrix()` |
| **Rolling stats not per-minute normalized** | Medium | Join fight duration and divide each stat by minutes; affects pre-2013 data most |
| **Pre-1998 / pre-2013 data included** | Medium | Either cut at 1998 like Tilburg, or filter to complete-stats-only rows |
| Super Heavyweight / Open Weight fights not removed | Low | ~10 fights total; negligible |
| MICE vs median imputation | Low | Tilburg used MICE for height/reach; we use median; functionally similar |

---

## Should You Restart from Scratch?

**No.**

A restart means throwing away the ETL pipeline, the database schema, the FastAPI backend, the feature engineering modules, and the model training infrastructure — none of which need to change. The gaps above are all confined to **a few dozen lines of filtering logic** in `pipeline.py` and `rolling_metrics.py`.

Here is what the database and infrastructure look like compared to what Tilburg had:

| Layer | Tilburg | This project |
|---|---|---|
| Data storage | CSV files | PostgreSQL (Supabase), typed columns, FK-linked |
| ETL pipeline | Manual pandas scripts | Automated ETL with 4 phases + validation |
| Feature engineering | Single script, career averages | 6 modular files, rolling windows + EWA + style + opponent quality |
| Models | RF + ANN | RF + XGBoost + LR, early stopping, experiment log |
| API | None | FastAPI with 10+ endpoints |
| Feature selection | None (all 35 used) | MI-based collinearity-filtered selection (25 features) |

The infrastructure is better. The data is richer. The only real issue is that **debut fights and pre-2013 fights are included as training rows**, and those rows have all stats features set to zero via imputation rather than being excluded. That is a targeted fix, not a rebuild.

**The targeted path forward:**

1. Add a `prior_fights_min` parameter to `build_training_matrix()` that filters out any fight where either fighter had fewer than N prior fights (Tilburg used N=1, i.e., drop debuts)
2. Optionally add `complete_stats_only=True` that drops rows where all rolling stat features are NaN before imputation
3. Rebuild the parquet with those filters applied
4. Retrain

That is 20–30 lines of Python, not a restart.
