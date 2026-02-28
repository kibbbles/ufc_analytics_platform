# Task ID: 5

**Title:** Feature Engineering Pipeline

**Status:** in-progress

**Dependencies:** 3 ✓

**Priority:** high

**Description:** Develop a feature engineering pipeline to process raw UFC data into ML-ready features, including fighter differentials, rolling performance metrics, and style classifications.

**Details:**

Create a comprehensive feature engineering pipeline using pandas and numpy:

1. Fighter differential features:
   - Height differential (cm)
   - Weight differential (lbs)
   - Reach differential (inches)
   - Age differential (years)
   - Experience differential (fights)
   - Win streak differential

2. Rolling performance metrics:
   - 3-fight rolling average for strikes landed/minute
   - 3-fight rolling average for takedown accuracy
   - 3-fight rolling average for submission attempts
   - Exponentially weighted averages for recent performance

3. Style classification features:
   - Striking vs. grappling ratio
   - Aggression score (forward pressure)
   - Defensive metrics (strikes absorbed, takedown defense)
   - Finishing ability (KO/submission percentage)

4. Time-based features:
   - Days since last fight
   - Career length in days
   - Age at fight time
   - Time in specific weight class

5. Opponent quality metrics:
   - Opponent win percentage
   - Strength of schedule
   - Common opponents analysis

Implement feature selection using mutual information and correlation analysis. Create a pipeline that can be used both for batch processing historical data and real-time feature generation for predictions.

**Test Strategy:**

1. Unit test each feature calculation function
2. Verify feature distributions and ranges
3. Test with edge cases (debut fighters, long layoffs)
4. Validate feature importance with preliminary models
5. Benchmark processing time for large datasets
6. Test reproducibility with fixed random seeds
7. Verify handling of missing data

## Subtasks

### 5.1. Data extraction queries

**Status:** pending  
**Dependencies:** None  

Create backend/features/extractors.py with SQL queries that pull raw fight data into pandas DataFrames for feature engineering. Covers fight_results, fight_stats, fighter_details, fighter_tott, and event_details tables.

**Details:**

Implement get_fights_df(), get_stats_df(), get_fighters_df(), and get_events_df() functions. Each returns a DataFrame using the SQLAlchemy engine from db.database. Use parameterized queries to support date-range filtering for incremental builds. No data transformation here -- raw extraction only.

### 5.2. Physical and experience differential features

**Status:** pending  
**Dependencies:** 5.1  

Create backend/features/differentials.py that computes fighter-A minus fighter-B differentials for physical attributes and career experience.

**Details:**

Features to compute: height_diff_inches, weight_diff_lbs, reach_diff_inches, age_diff_days (at fight date using dob_date), experience_diff (total UFC fights), win_streak_diff, loss_streak_diff. Join fighter_tott for physical stats. Use fight_results ordered by event date to compute streaks. Handle NULLs gracefully -- impute with 0 or median where appropriate.

### 5.3. Rolling performance metrics

**Status:** pending  
**Dependencies:** 5.1  

Create backend/features/rolling_metrics.py computing rolling averages of striking and grappling performance over the last N fights, strictly using only pre-fight data to avoid leakage.

**Details:**

Metrics: 3-fight rolling avg for sig_str_pct, td_pct, kd_int, ctrl_seconds, sig_str_landed, sig_str_attempted. Also compute exponentially weighted averages (EWA) with alpha=0.5. Critical: shift(1) all rolling values so they reflect stats BEFORE the current fight. Merge on fighter_id and fight date order. Only use fight_stats rows where ROUND is numeric (already filtered in DB). Aggregate per fight first (sum across rounds), then roll.

### 5.4. Style classification features

**Status:** pending  
**Dependencies:** 5.3  

Create backend/features/style_features.py that derives fighting style metrics from career aggregated stats.

**Details:**

Features: striking_ratio (sig_str_landed / total_str_landed), grappling_ratio (td_landed / (td_landed + sig_str_landed)), aggression_score (sig_str_attempted per minute), defense_score (1 - opp_sig_str_pct against this fighter), finish_rate (KO+Sub wins / total wins), ko_rate (KO wins / total fights), sub_rate (Sub wins / total fights), decision_rate (decision wins / total fights). Compute over career history up to but not including current fight.

### 5.5. Time-based features

**Status:** pending  
**Dependencies:** 5.1  

Create backend/features/time_features.py that extracts temporal context features for each fight.

**Details:**

Features: days_since_last_fight (layoff duration), career_length_days (first UFC fight to current fight date), age_at_fight (computed from dob_date and event date_proper), days_in_weight_class (first fight in current weight class to current). All computed relative to the fight date -- not current date -- to keep the dataset point-in-time correct. Handle debut fights (days_since_last_fight = NULL -> encode as large value, e.g. 365).

### 5.6. Opponent quality metrics

**Status:** pending  
**Dependencies:** 5.1  

Create backend/features/opponent_quality.py computing strength-of-schedule metrics based on the quality of past opponents.

**Details:**

Features: avg_opponent_win_pct (avg win rate of past opponents at time of each fight), strength_of_schedule (sum of opponent win pcts normalized by number of fights), avg_opponent_losses (avg loss count of past opponents). Use only opponent records UP TO the date of each fight to avoid leakage. Merge on fight date ordering.

### 5.7. Feature selection analysis

**Status:** pending  
**Dependencies:** 5.2, 5.3, 5.4, 5.5, 5.6  

Create backend/features/selection.py that runs mutual information and correlation analysis to identify the most predictive features, outputting a curated feature list.

**Details:**

Steps: 1) Build full training matrix by calling pipeline.py. 2) Compute mutual information scores (sklearn mutual_info_classif) against the binary win/loss target. 3) Compute Pearson correlation matrix and flag highly correlated pairs (|r| > 0.9) for removal. 4) Output selected_features.json listing the final feature set to backend/features/selected_features.json. This file is then read by the ML training scripts in Task 6.

### 5.8. Pipeline assembly

**Status:** pending  
**Dependencies:** 5.2, 5.3, 5.4, 5.5, 5.6  

Create backend/features/pipeline.py that assembles all feature modules into a unified interface with both batch (training) and real-time (prediction) modes.

**Details:**

Two public functions: build_training_matrix(date_from=None, date_to=None) -> pd.DataFrame   - Calls all extractors, merges all feature DataFrames on fight_id,     adds binary target column (fighter_a_wins: 1 or 0), returns full matrix. build_prediction_features(fighter_a_id, fighter_b_id) -> dict   - Pulls latest stats for both fighters, computes all differentials     and rolling metrics on the fly, returns a flat dict of feature values     matching selected_features.json. Save the training matrix as a parquet file at backend/features/training_data.parquet for reuse across ML experiments.
