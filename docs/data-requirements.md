# UFC Analytics Platform - Data Requirements Documentation

**Purpose:** Define exactly which data fields are required for the three core products and ML models, ensuring we only normalize what's necessary.

**Last Updated:** 2025-11-27

---

## Overview

This document maps database fields to product features and ML model requirements. Only fields marked as **REQUIRED** will be normalized in the initial migration.

---

## Product 1: Fight Outcome Predictor with Interactive Sliders

### Data Requirements

#### Fighter Physical Attributes (fighter_tott table)
| Field | Current Type | Normalized Type | Required | Usage |
|-------|-------------|-----------------|----------|-------|
| HEIGHT | TEXT | height_inches FLOAT | ✅ YES | Slider input, height differential feature |
| WEIGHT | TEXT | weight_lbs FLOAT | ✅ YES | Slider input, weight differential feature |
| REACH | TEXT | reach_inches FLOAT | ✅ YES | Slider input, reach differential feature |
| DOB | TEXT | dob_date DATE | ✅ YES | Calculate age at fight time |
| STANCE | TEXT | (keep as TEXT) | ✅ YES | Style feature (orthodox/southpaw) |

#### Fight Statistics (fight_stats table - per fighter, per round)
| Field | Current Type | Normalized Fields | Required | Usage |
|-------|-------------|-------------------|----------|-------|
| SIG.STR. | TEXT "X of Y" | sig_str_landed INT, sig_str_attempted INT | ✅ YES | Striking accuracy slider, performance metrics |
| SIG.STR.% | TEXT "X%" | sig_str_pct FLOAT | ✅ YES | Striking accuracy validation |
| TD | TEXT "X of Y" | td_landed INT, td_attempted INT | ✅ YES | Takedown accuracy slider |
| TD% | TEXT "X%" | td_pct FLOAT | ✅ YES | Takedown accuracy validation |
| KD | TEXT | knockdowns INT | ✅ YES | Knockdown rate slider |
| SUB.ATT | TEXT | sub_attempts INT | ✅ YES | Submission attempts slider, grappling style |
| CTRL | TEXT "M:SS" | control_time_seconds INT | ⚠️ MAYBE | Grappling control metric |
| REV. | TEXT | reversals INT | ❌ NO | Low priority for initial version |
| HEAD | TEXT "X of Y" | head_landed INT, head_attempted INT | ⚠️ MAYBE | Detailed striking breakdown |
| BODY | TEXT "X of Y" | body_landed INT, body_attempted INT | ⚠️ MAYBE | Detailed striking breakdown |
| LEG | TEXT "X of Y" | leg_landed INT, leg_attempted INT | ⚠️ MAYBE | Detailed striking breakdown |
| DISTANCE | TEXT "X of Y" | distance_landed INT, distance_attempted INT | ⚠️ MAYBE | Fighting style classification |
| CLINCH | TEXT "X of Y" | clinch_landed INT, clinch_attempted INT | ⚠️ MAYBE | Fighting style classification |
| GROUND | TEXT "X of Y" | ground_landed INT, ground_attempted INT | ⚠️ MAYBE | Grappling vs striking ratio |

#### Fight Results (fight_results table)
| Field | Current Type | Normalized Type | Required | Usage |
|-------|-------------|-----------------|----------|-------|
| OUTCOME | TEXT "W/L" | winner_fighter_id VARCHAR(6) | ✅ YES | ML training target variable |
| METHOD | TEXT | (keep as TEXT) | ✅ YES | Multi-class prediction (KO/SUB/DEC) |
| ROUND | TEXT | round_finished INT | ✅ YES | Round prediction feature |
| TIME | TEXT "M:SS" | finish_time_seconds INT | ⚠️ MAYBE | Finish time prediction |
| WEIGHTCLASS | TEXT | (keep as TEXT) | ✅ YES | Filter fights by weight class |

#### Event Data (event_details table)
| Field | Current Type | Normalized Type | Required | Usage |
|-------|-------------|-----------------|----------|-------|
| DATE | TEXT | date_proper DATE | ✅ YES | Calculate days between fights, temporal features |
| LOCATION | TEXT | (keep as TEXT) | ❌ NO | Not needed for predictions |

---

## Product 2: Style Evolution Timeline Analyzer

### Data Requirements

#### Aggregated Fight Statistics (by era/year)
| Metric | Source Fields | Required | Usage |
|--------|--------------|----------|-------|
| Finish Rate by Method | fight_results.METHOD | ✅ YES | KO vs Submission vs Decision trends over time |
| Average Fight Duration | fight_results.ROUND, TIME | ✅ YES | Trend in fight pacing over eras |
| Striking Accuracy Trends | fight_stats.SIG.STR.% | ✅ YES | Evolution of striking effectiveness |
| Takedown Success Trends | fight_stats.TD% | ✅ YES | Evolution of grappling effectiveness |
| Finish Rate by Round | fight_results.ROUND | ✅ YES | Early finisher vs late fight trends |

#### Temporal Grouping
| Field | Required | Usage |
|-------|----------|-------|
| event_details.date_proper | ✅ YES | Group fights by year, era |
| fight_results.WEIGHTCLASS | ✅ YES | Filter trends by weight class |

**Additional Requirements:**
- All normalized fight_stats fields needed for aggregation over time
- fight_results.METHOD must remain as TEXT for categorization

---

## Product 3: Fighter Endurance & Pacing Dashboard

### Data Requirements

#### Round-by-Round Performance (fight_stats table)
| Field | Normalized Fields | Required | Usage |
|-------|-------------------|----------|-------|
| ROUND | (keep as TEXT) | ✅ YES | X-axis for round-by-round charts |
| SIG.STR. | sig_str_landed, sig_str_attempted | ✅ YES | Track striking output degradation by round |
| SIG.STR.% | sig_str_pct | ✅ YES | Track accuracy degradation by round |
| TD | td_landed, td_attempted | ✅ YES | Track takedown activity by round |
| TOTAL STR. | total_str_landed, total_str_attempted | ⚠️ MAYBE | Overall output tracking |
| CTRL | control_time_seconds | ⚠️ MAYBE | Control time by round for grapplers |

#### Fighter Metadata
| Field | Required | Usage |
|-------|----------|-------|
| fighter_tott.DOB | ✅ YES | Age impact on cardio |
| fight_results.ROUND (finished) | ✅ YES | Survival analysis by round |

**Key Insight:** This dashboard heavily relies on round-by-round fight_stats data, which is only available for ~2015+ fights.

---

## ML Model Feature Requirements

### Binary Win/Loss Prediction Model

#### Essential Features (Must Normalize)
1. **Fighter Differentials:**
   - Height differential (height_inches_a - height_inches_b)
   - Weight differential (weight_lbs_a - weight_lbs_b)
   - Reach differential (reach_inches_a - reach_inches_b)
   - Age differential (age_at_fight_a - age_at_fight_b)
   - Experience differential (total_fights_a - total_fights_b)

2. **Performance Metrics (Rolling Averages - Last 3 Fights):**
   - Striking accuracy (sig_str_pct)
   - Strikes landed per minute (sig_str_landed / fight_duration)
   - Takedown accuracy (td_pct)
   - Knockdown rate (knockdowns per fight)
   - Submission attempts per fight (sub_attempts)

3. **Win Streak & Momentum:**
   - Current win streak (derived from fight_results)
   - Last fight result (win/loss)

4. **Target Variable:**
   - fight_results.OUTCOME → binary (1 = fighter A wins, 0 = loses)

### Method Prediction Model (KO/Submission/Decision)

#### Essential Features
- All features from win/loss model PLUS:
- Historical finish rates by method per fighter
- Style matchup indicators (striker vs grappler)
- Average fight distance (distance_strikes vs clinch/ground)

---

## Normalization Priority

### Phase 1: CRITICAL (Do First - Needed for all 3 products)
```sql
-- fighter_tott table
height_inches FLOAT
weight_lbs FLOAT
reach_inches FLOAT
dob_date DATE

-- fight_stats table (per round)
sig_str_landed INT
sig_str_attempted INT
sig_str_pct FLOAT
td_landed INT
td_attempted INT
td_pct FLOAT
knockdowns INT
sub_attempts INT

-- fight_results table
round_finished INT

-- event_details table
date_proper DATE (already exists, just needs population)
```

### Phase 2: OPTIONAL (Add Later for Enhanced Features)
```sql
-- fight_stats table (detailed breakdown)
control_time_seconds INT
head_landed, head_attempted INT
body_landed, body_attempted INT
leg_landed, leg_attempted INT
distance_landed, distance_attempted INT
clinch_landed, clinch_attempted INT
ground_landed, ground_attempted INT
total_str_landed, total_str_attempted INT

-- fight_results table
finish_time_seconds INT
```

### Fields to Keep as TEXT (No Normalization Needed)
- fighter_tott.STANCE
- fight_results.METHOD
- fight_results.WEIGHTCLASS
- fight_stats.FIGHTER (name reference)
- fight_details.BOUT
- event_details.LOCATION

---

## Weekly Data Automation Requirements

### Trigger-Based Auto-Normalization

When new data arrives weekly from the scraper:

1. **Database Triggers** (PostgreSQL BEFORE INSERT/UPDATE):
   - Auto-populate normalized columns from TEXT columns
   - Apply parsing functions transparently
   - Log any parsing failures

2. **Parsing Functions Required:**
   ```sql
   parse_height(text) → float  -- "5' 11\"" → 71.0
   parse_weight(text) → float  -- "155 lbs" → 155.0
   parse_reach(text) → float   -- "74\"" → 74.0
   parse_date(text) → date     -- "January 25, 2025" → 2025-01-25
   parse_strikes(text) → (int, int)  -- "17 of 37" → (17, 37)
   parse_percentage(text) → float    -- "45%" → 0.45
   parse_time(text) → int      -- "2:34" → 154 seconds
   ```

3. **Validation:**
   - Track parsing success rates
   - Alert on parsing failures above threshold (>5%)
   - Log unparseable values for manual review

---

## Data Quality Checks (Great Expectations)

### Critical Validations
1. Height range: 60-84 inches
2. Weight range: 115-265 lbs
3. Reach range: 60-84 inches
4. Dates: 1993-present (UFC started 1993)
5. Percentages: 0.0-1.0
6. Knockdowns: 0-10 per round
7. Round numbers: 1-5

### Referential Integrity
- Every fight_stats.fighter_id exists in fighter_details
- Every fight_stats.event_id exists in event_details
- Every fight_stats.fight_id exists in fight_details

---

## Summary

**Total Normalized Columns to Add:**
- **Phase 1 (Critical):** 14 columns across 4 tables
- **Phase 2 (Optional):** 15 additional columns

**Automation Strategy:**
- Initial backfill: Python migration script
- Ongoing: PostgreSQL triggers for weekly data

**Estimated Coverage:**
- fighter_tott: ~4,429 fighters (100%)
- fight_stats: ~38,958 records (mainly 2015+)
- event_details: ~744 events (1994-2025)

---

## Next Steps

1. Review this document and confirm Phase 1 fields
2. Implement Task 3.3: Add normalized columns (Phase 1 only)
3. Implement Task 3.4: Create parsing functions
4. Implement Task 3.5: Migration script + triggers
5. Test with sample data
6. Run full migration on production database
