# Tilburg University MMA Prediction Study — Comprehensive Summary

**Full title:** "Machine Learning approach to predicting Mixed Martial Arts matches"
**Author:** M. Turgut (student ID 2041954), Tilburg University
**Degree:** MSc Data Science & Society, Department of Cognitive Science & AI
**Date:** January 15, 2021
**Supervisor:** Dr. A.T. Hendrickson

---

## 1. Study Goal and Research Question

**Primary question:** What is the difference in predictive performance between DL models and traditional ML models when predicting MMA fight outcomes?

**Sub-questions:**
1. While preventing information leakage, which features can be used for prediction?
2. Which hyperparameters provide the best results for each model?
3. What happens if the same features are used but with information leakage built in?

**Key insight of the paper:** Without careful data engineering, models appear to achieve 65–69% accuracy. With proper leakage prevention, the realistic ceiling is ~59%. The paper explicitly demonstrates this gap with a controlled leakage experiment.

---

## 2. Data Sources

Two raw datasets scraped from **www.ufcstats.com** using Beautiful Soup 4 (Python 3.7.3).

### Dataset A: Athletes
- **3,559 athletes** sorted by last name
- **20 features** grouped into two categories:
  - *Personal*: first name, last name, nickname, DOB, height, weight, reach, stance
  - *Career summary*: wins, losses, draws, champion flag, SLpM, Str.Acc, SApM, Str.Def, TD Avg, TD Acc, TD Def, Sub.Avg
- **Critical note:** These career summary stats are computed over ALL historical fights — they are post-hoc summaries and cannot be used directly to predict any individual historical match (that is information leakage).

### Dataset B: Matches
- **5,615 matches**, October 1998 to September 2020, descending by date
- **62 features** including: date, location, attendance, weight class, championship flag, method, round, time, referee, details, and per-fighter stats (KD, sig. strikes, total strikes, TD, ctrl time, head/body/leg/distance/clinch/ground strikes)
- **Structure:** `fighter1` is **always the winner** (except draws/NCs)

---

## 3. Data Preprocessing

### 3.1 Athletes Dataset Cleaning

**Step 1: Convert missing values**
- Double dashes (`--`) → NaN throughout

**Step 2: Fix data types**
- DOB: string "13-Jul-78" → Pandas DateTime
- Height: "5' 11"" → inches (float)
- Weight: "155 lbs." → float
- Reach: "76.0"" → float
- Percentage stats like "38%" → float (0–1 range)

**Step 3: Create full name column**
- Concatenated first + last name for cross-dataset lookup

**Step 4: Remove Super Heavyweight athletes (no upper weight limit)**
- All athletes heavier than 265 lbs. removed
- Athletes with missing weight removed
- **121 entries removed** (75 for missing weight)

**Step 5: Remove non-UFC athletes**
- Fighters who never competed in an official UFC event removed
- **1,477 athletes removed**

**Step 6: Handle duplicate names**
- Three fighters had identical names; weight class appended to disambiguate:
  - "Joey Gomez" → "Joey Gomez" + "Joey Gomez 155"
  - "Michael McDonald" → "Michael McDonald" + "Michael McDonald 135"
  - "Bruno Silva" → "Bruno Silva" + "Bruno Silva 185"

**Athletes remaining after cleaning: 1,961**

**Step 7: Analyze missing data (Table 4.3)**

| Column   | Missing entries | Ratio |
|---|---|---|
| nickname | 668 | 0.34 |
| DOB      | 57  | 0.03 |
| height   | 3   | 0.00 |
| reach    | 538 | 0.27 |
| stance   | 51  | 0.03 |

**Step 8: Impute height and reach**
- Used **MICE (Multiple Imputation by Chained Equations)** — not simple median
- Checked that imputed distributions match original distributions via density plots
- Height imputation: only 3 entries, distribution unchanged
- Reach: 27% missing — most missingness correlates with DOB and stance also missing

---

### 3.2 Matches Dataset Cleaning

**Step 1: Fix data types**
- Dates: string → Pandas DateTime

**Step 2: Handle percentage columns**
- td% fighter1/2, sig.str% fighter1/2: missing when no attempts made → replace with **0** (not NaN, because 0 attempts = 0% is the correct interpretation)

**Step 3: Convert missing values**
- All `--` and empty values → NaN

**Step 4: Convert ctrl time**
- "ctrl fighter1/2": stored as "MM:SS" string → converted to **seconds (integer)**

**Step 5: Handle duplicate names in matches**
- One duplicate ("Michael McDonald") resolved: removed the duplicate from athletes dataset, kept original name in matches dataset

**Step 6: Mark matches with athletes missing from athletes dataset**
- 58 matches had at least one fighter not in the athletes dataset
- These were **flagged** (not removed yet) for removal after feature engineering

**Step 7: Remove Super Heavyweight and Open Weight matches**
- Open Weight = no upper weight limit (same as Super Heavyweight in practice)
- **4 matches removed**
- Catch Weight matches **retained** (weight limits between existing classes)

**Matches after cleaning: 5,611**

**Missing data in matches dataset (Table 4.5):**

| Column       | Missing | Ratio |
|---|---|---|
| referee      | 29      | 0.005 |
| details      | 46      | 0.008 |
| ctrl fighter1| 29      | 0.005 |
| ctrl fighter2| 29      | 0.005 |

- Referee and details columns **removed** (not predictive)
- ctrl missing entries: 29 rows missing both ctrl columns simultaneously (correlated)

---

## 4. Feature Engineering (Leakage-Free)

The core principle: **every match row should contain only information that was available BEFORE that match took place**. The athletes dataset contains current (present-day) summaries — these cannot be used directly.

### 4.1 Age Feature
- For each match, subtract the fighter's DOB from the match date
- Result: age in days/years at the time of the fight
- Available in each row because DOB and match date are both pre-fight data

### 4.2 Records Feature (wins, losses, draws)

**Method:** Iterate over all matches **backward in time** (from most recent to oldest):
- First appearance of a fighter: copy records from the athletes dataset (most recent state)
- Subsequent appearances (going backward): subtract outcomes of later matches to reconstruct the record at the time of that earlier match

**Implementation detail:**
- Must check whether fighter is fighter1 or fighter2 in each row when working backward
- Outcome column values: "win" (fighter1 won), "draw", "nc"

**Result:** Each row contains the fighter's W-L-D record AT THE TIME of that specific fight.

### 4.3 Win Rate Feature

Calculated after records are computed:

```
win_rate = wins / (wins + losses + draws)
```

- Debut fights (0 prior fights): win_rate = 0
- Inspired by Tian (2018)

### 4.4 Winning Streak Feature

**Method:** Iterate **backward** through matches (chronological order):
- All fighters start at 0 winning streak
- Increment if the previous match was a win
- Reset to 0 if the previous match was a loss or draw
- If previous match was NC: streak unchanged
- **Only UFC fights count** — pre-UFC career is ignored

### 4.5 Average Fight Statistics Feature

**Core idea:** Replace each row's in-match stats with the fighter's **historical averages** of those stats from all previous matches.

**Method:** Iterate through dataset backward (chronological order):
- First appearance: all averages set to **0**
- Subsequent appearances: compute mean over all previous matches

**Normalization for fight duration:** Averages are calculated **per minute** (not raw totals), because:
- MMA fights end early via KO/submission, unlike team sports where matches run the full time
- A fighter who finishes opponents in round 1 has fewer total strikes than one who goes 5 rounds — per-minute normalizes this
- Round number and time columns are used to calculate exact fight duration in minutes

**Statistics averaged (for each fighter):**
KD, sig_str_landed, sig_str_attempted, sig_str%, total_str_landed, total_str_attempted,
td_landed, td_attempted, td%, sub_att, reversals, ctrl_time,
head_landed, head_attempted, body_landed, body_attempted, leg_landed, leg_attempted,
distance_landed, distance_attempted, clinch_landed, clinch_attempted, ground_landed, ground_attempted

---

## 5. Further Processing (Final Cleaning)

After feature engineering, the following rows are removed:

**Step 1:** Remove matches flagged earlier where a fighter is missing from the athletes dataset (58 matches)

**Step 2:** Remove rows with any missing data in any column
- At this point: 5,553 matches remain
- 118 matches (~2%) have missing data in at least one column → **removed**

**Step 3:** Remove draws and No Contests
- Required for binary classification (win/loss only)

**Step 4:** Remove debut fights (first UFC fight for either fighter)
- These fighters have no previous match data; averages are all zero
- Including them would add noise — they are removed

**Final dataset before restructuring: not explicitly stated**

---

## 6. Dataset Restructuring

**Step 1: Perspective swap to balance target**
- Dataset is structured with fighter1 as always the winner → 100% class imbalance
- **Randomly swap fighter1 and fighter2 in 50% of rows** (random index selection)
- Add a binary `winner` column: 0 = fighter1 won, 1 = fighter2 won (answers "is fighter2 the winner?")

**Step 2: Reduce features by computing differentials**
- Replace 23 `stats fighter1` + 23 `stats fighter2` columns with 23 `diff_avg_*` columns
- `diff = stats fighter2 - stats fighter1`
- This halves the number of stat columns and removes redundancy
- The sign convention: positive diff means fighter2 performed better in that stat

**Final dataset: 3,925 rows, 35 features**

### Final Feature Set (Table 9.3)

| Feature | Type | Description |
|---|---|---|
| winner | int | Binary: 1 if fighter2 won |
| age_fighter1 | int | Age of fighter1 at fight date |
| age_fighter2 | int | Age of fighter2 at fight date |
| wins_fighter1 | int | Wins before this fight |
| losses_fighter1 | int | Losses before this fight |
| draws_fighter1 | int | Draws before this fight |
| win_streak_fighter1 | int | Win streak before this fight |
| win_rate_fighter1 | float | Win rate before this fight |
| wins_fighter2 | int | Wins before this fight |
| losses_fighter2 | int | Losses before this fight |
| draws_fighter2 | int | Draws before this fight |
| win_streak_fighter2 | int | Win streak before this fight |
| win_rate_fighter2 | float | Win rate before this fight |
| diff_avg_kd | float | Diff in avg KD per minute |
| diff_avg_sig_str_land_total | float | Diff in avg sig strikes landed/min |
| diff_avg_sig_str_att_total | float | Diff in avg sig strikes attempted/min |
| diff_avg_sig_str_pct | float | Diff in avg sig strike % |
| diff_avg_total_str_land_total | float | Diff in avg total strikes landed/min |
| diff_avg_total_str_att | float | Diff in avg total strikes attempted/min |
| diff_avg_td_land_total | float | Diff in avg TDs landed/min |
| diff_avg_td_att_total | float | Diff in avg TDs attempted/min |
| diff_avg_td_pct | float | Diff in avg TD% |
| diff_avg_sub_att | float | Diff in avg submission attempts/min |
| diff_avg_rev | float | Diff in avg reversals/min |
| diff_avg_head_land | float | Diff in avg head strikes landed/min |
| diff_avg_head_att | float | Diff in avg head strikes attempted/min |
| diff_avg_body_land | float | Diff in avg body strikes landed/min |
| diff_avg_body_att | float | Diff in avg body strikes attempted/min |
| diff_avg_leg_land | float | Diff in avg leg strikes landed/min |
| diff_avg_leg_att | float | Diff in avg leg strikes attempted/min |
| diff_avg_dis_land | float | Diff in avg distance strikes landed/min |
| diff_avg_dis_att | float | Diff in avg distance strikes attempted/min |
| diff_avg_clinch_land | float | Diff in avg clinch strikes landed/min |
| diff_avg_clinch_att | float | Diff in avg clinch strikes attempted/min |
| diff_avg_ground_land | float | Diff in avg ground strikes landed/min |
| diff_avg_ground_att | float | Diff in avg ground strikes attempted/min |

**Note:** Physical features (height, weight, reach) are NOT in the final feature set. The paper did not include physical differentials. Records and win rate are NOT differenced — they are kept as raw values for both fighters.

---

## 7. Train / Validation / Test Split

- **No random shuffle** — matches kept in chronological order (oldest first)
- Reason: to avoid training on matches from the future relative to validation/test matches (Tax & Joustra 2015)
- Split ratios: **80% train / 20% test**, then train split again **80% / 20%** for validation:
  - Train: 64% of all data
  - Validation: 16% of all data
  - Test: 20% of all data (most recent matches)
- Both RF and ANN trained on the same split

---

## 8. Modeling

### 8.1 Random Forest (scikit-learn)

**Baseline (no tuning):** 57.32% validation accuracy

**Hyperparameter search:** RandomizedSearchCV (5 hyperparameters, see grid below)

| Hyperparameter | Search range |
|---|---|
| n_estimators | 100–500, step 20 |
| max_depth | 5–50, step 5 |
| min_samples_split | 1, 3, 5, 10, 20 |
| min_samples_leaf | 1, 3, 5, 10, 20 |
| bootstrap | True, False |

**Best hyperparameters:**

| Hyperparameter | Value |
|---|---|
| n_estimators | 310 |
| max_depth | 27 |
| min_samples_split | 3 |
| min_samples_leaf | 10 |
| bootstrap | True |

**Results:**
- Validation accuracy: **59.24%**
- Test accuracy: **58.98%**
- Train vs test gap: **-0.26%** (no overfitting)

### 8.2 Artificial Neural Network (Keras + Keras Tuner)

**Preprocessing:** StandardScaler applied before feeding to ANN (RF does not require scaling)

**Architecture search:** RandomizedSearchCV via Keras Tuner

**Search space:**

| Hyperparameter | Values |
|---|---|
| Optimizer | adagrad, adam, rmsprop |
| Activation (input + hidden) | ReLU, Leaky ReLU |
| Leaky ReLU alpha | 0.1, 0.2, 0.3 |
| Dropout rate | 0.0, 0.1, 0.2 |
| Batch Normalization | True, False |
| Nodes per hidden layer | 4–16, step 2 |
| Number of hidden layers | 1–10 |

**Best model:**
- Optimizer: RMSprop
- Activation: Leaky ReLU (alpha=0.3)
- No dropout, no batch normalization
- 6 hidden layers, nodes per layer: 6, 4, 10, 6, 12, 14
- Architecture: (35, 6, 4, 10, 6, 12, 14, 1)
- Regularization: **early stopping only** (patience=3)
- Output activation: sigmoid

**Results:**
- Validation accuracy: **61.62%**
- Test accuracy: **59.11%**
- Train vs test gap: **-2.51%** (slight underfit on test)

---

## 9. Information Leakage Experiment (Controlled)

To quantify the effect of leakage, two additional models were trained on a dataset where records, win rate, and fight statistics were **not** computed backward in time — identical to Tian (2018) and Pierce (2020).

### Results Comparison

| Model | Val Accuracy | Test Accuracy | Change vs leakage-free |
|---|---|---|---|
| Regular RF | 59.24% | 58.98% | — |
| RF with leakage | 62.70% | 65.11% | **+6.13%** |
| Regular ANN | 61.62% | 59.11% | — |
| ANN with leakage | 68.65% | 68.59% | **+9.48%** |

**Conclusion:** Not accounting for leakage inflates accuracy by 6–10%. This matches the gap between Tian (69%) and this study (59%).

---

## 10. Feature Importance Findings (Top 5, Regular RF)

1. win_rate_fighter2
2. diff_avg_td_att_total
3. diff_avg_td_landed_total
4. diff_avg_ground_land
5. diff_avg_sub_att

**Pattern:** The leakage-free model relies almost entirely on **wrestling/grappling output metrics** (4 out of 5 top features are grappling). The leakage model relies more on **records** (wins, win rate — 3 out of 5).

---

## 11. Final Results Summary

| Model | Val Accuracy | Test Accuracy |
|---|---|---|
| Baseline Decision Tree | 51.59% | — |
| Baseline Random Forest | 57.32% | — |
| Tuned RF (no leakage) | 59.24% | **58.98%** |
| Tuned ANN (no leakage) | 61.62% | **59.11%** |
| RF with leakage | 62.70% | 65.11% |
| ANN with leakage | 68.65% | 68.59% |

**Both leakage-free models achieved ~59% accuracy** — nearly identical performance, suggesting RF and ANN have roughly equal predictive capacity for this problem size.

---

## 12. Comparison to Other Studies

| Study | Approach | Accuracy | Leakage? |
|---|---|---|---|
| Tian (2018) | ANN, UFCStats | 69% | Yes |
| Pierce (2020) | ANN, UFCStats | 86% | Yes |
| McQuaide/Stanford (2019) | GB, UFCStats | 61.2% (test) | Unclear |
| McCabe & Trevathan (2008) | ANN, team sports | 54.6–67.5% | No |
| Tax & Joustra (2015) | Football, Netherlands | 54.7–56.1% | No |
| **Tilburg (2021)** | RF + ANN, UFCStats | **58.98–59.11%** | **No** |

---

## 13. What Tilburg Did That We Should Replicate

### Data cleaning decisions:
1. **Cut off before October 1998** — frequent missing data in older matches
2. **Remove Super Heavyweight and Open Weight fights** — too few / no weight limit
3. **Remove debut fights for both fighters** — no historical data exists; averages are all zero
4. **Remove rows with any NaN after feature engineering** (~2% of data)
5. **Remove draws and No Contests** — binary classification only
6. **Impute reach/height with MICE** (not median) — preserves distribution

### Feature engineering decisions:
1. **Per-minute normalization** of all fight stats — corrects for shorter fights having less total output
2. **Backward iteration** to compute records and averages — strictly point-in-time
3. **Win streak resets on draw or loss** — NC leaves streak unchanged
4. **Physical features (height, weight, reach) were NOT used** — Tilburg excluded them entirely
5. **Average over ALL previous fights** (not rolling window of last N) — simpler but still leakage-free
6. **Perspective swap: random 50% of rows** — prevents position bias

### What Tilburg did NOT do:
- No rolling windows (e.g., last 3 fights) — just career averages
- No opponent quality features
- No time-since-last-fight feature
- No weight class encoding as a feature
- No style cluster features

---

## 14. Key Quotes for Reference

**On leakage:** "Tian (2018) and Pierce (2020) both used athlete summary data, which are calculated using all historical matches of a certain athlete to predict those individual matches." (p.10)

**On debut removal:** "All matches in which either athlete is competing for the first time are removed from the dataset as well. Since these athletes do not have any previous data available their average fight statistics were set to zero." (p.31)

**On per-minute normalization:** "To normalize this data, the averages are calculated per minute. The 'round' and 'time' columns are used to calculate the amount of time each match took." (p.30)

**On temporal split:** "As in the study of Tax & Joustra (2015), the matches are not randomly shuffled. This is done to avoid training on matches that happened later compared to matches in the validation and test sets." (p.32)

**On leakage inflation:** "Adding information leakage to the Random Forest model increased accuracy on the test set by 6.13%. Adding information leakage to the ANN model caused an increase of 9.48%." (p.39)
