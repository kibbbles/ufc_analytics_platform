# ML Data Preparation Requirements

Standards and checklist for the UFC analytics training matrix before any model
training or feature selection is run.

---

## 1. Structure

**Requirement:** One row per fight (not per fighter-fight pair), one column per
feature, consistent dtypes throughout.

**What we have:**
- `training_data.parquet` — one row per fight_id (perspective-flipped ~50/50)
- Target: `fighter_a_wins` (int, 0 or 1 — draws and NCs excluded)
- No raw text columns; all IDs (`fight_id`, `fighter_a_id`, `fighter_b_id`) are
  in metadata columns that the model never sees

**Check before training:**
```python
assert df["fight_id"].nunique() == len(df), "duplicate fight_ids"
assert set(df["fighter_a_wins"].dropna().unique()) <= {0, 1}, "bad target values"
assert df.index.is_unique
```

---

## 2. Format

**Requirement:** All model inputs must be numeric or ordinally-encoded
categorical. No raw strings, no UUIDs as features.

**What we have:**
- All diff_* features are float64 (A minus B differentials)
- `weight_class` is the only categorical; it is OrdinalEncoded in the sklearn
  pipeline with a lightest→heaviest ordering so the encoding preserves meaning
- `is_title_fight`, `is_women_division` are already int (0/1)

**Not-a-feature columns** (present in the parquet, dropped by ColumnTransformer):
`fight_id`, `fighter_a_id`, `fighter_b_id`, `event_date`, `method`

---

## 3. Cleanliness

### 3.1 Duplicates

Root cause identified: `fighter_tott` can have multiple rows per `fighter_id`.
The LEFT JOIN in `get_fighters_df()` fans this out into downstream feature
modules (`time_features`, `differentials`).

**Fixes applied:**
- `get_fighters_df()` now uses `DISTINCT ON (fd.id)` — one tott row per fighter
- `pipeline.py` `build_training_matrix()` drops duplicate `fight_id` rows after
  all merges (safety net) and warns if any were found

**Check before training:**
```python
assert df["fight_id"].nunique() == len(df)
```

### 3.2 NaN Handling

High-NaN sources and how they are handled:

| Column group | NaN rate | Cause | Handling |
|---|---|---|---|
| `diff_roll*` (stats-based) | 25–44% | No fight_stats before ~2013 | Median imputed (sklearn pipeline) |
| `age_diff_days` | ~5% | Missing DOB in fighter_tott | Median imputed |
| `diff_td_pct`, `diff_sig_str_pct` | ~15% | Opponent had 0 attempts | Median imputed |
| `diff_days_in_weight_class` | <1% | NULL weight_class | Median imputed |

Imputation happens **inside the sklearn Pipeline** (after the train/val/test
split), so imputation parameters are learned only on train data — no leakage.

### 3.3 Pre-2013 Fights (Complete-Data Filter)

~2,175 rows (25.4% of training set) have **all** stats-based rolling features
as NaN because `fight_stats` doesn't exist before ~2013. Median imputation turns
these into zeros, adding noise rather than signal.

Stanford's approach filtered to complete samples only (5,144 → 3,355 fights).

**Current status:** Pre-2013 rows are included but all stats-based features are
median-imputed to effectively zero. This hurts model performance slightly.

**Optional future improvement:** Add a `--complete-only` flag to
`build_training_matrix` that filters rows where `diff_roll3_sig_str_landed`
is NaN before imputation.

---

## 4. Scale

**Requirement:** Distance- and gradient-based models (Logistic Regression,
XGBoost) require features on comparable scales. Tree-based models (RF) do not,
but standardization doesn't hurt them.

**What we have:**
- `StandardScaler` is applied inside the sklearn pipeline after median imputation
- Scaler is fit on `X_train` only, then applied to X_val and X_test — no leakage
- `OrdinalEncoder` handles the `weight_class` categorical separately

---

## 5. Consistency

### 5.1 Perspective Balance (Position Bias)

UFCStats lists the winner on the left side of the BOUT string, making
`fighter_a_id` systematically the winner (~64% before correction).

**Fix applied in `pipeline.py`:**
- Random 50% of rows are flipped: all differential columns are negated,
  `fighter_a_id`/`fighter_b_id` are swapped, `fighter_a_wins` is inverted
- Flip uses `seed=42` for reproducibility
- Final target balance: ~50% (verified by `build_training_matrix` log)
- Flip correctly identifies ALL differential columns using `"diff" in c` —
  catches both `diff_*` prefixed columns and physical columns like
  `height_diff_inches`, `weight_diff_lbs`, etc.

**Verify symmetry:** Running inference on (A vs B) and (B vs A) should give
probabilities that sum to ~1.0. Gap > 1% indicates a missing negation.

### 5.2 Point-in-Time Correctness (No Leakage)

All features use only information available **before** the fight:
- Rolling metrics: `rolling(N).mean().shift(1)` — excludes the current fight
- Career stats: `cumcount()` / `cumsum()` with `.shift(1)` — excludes current
- `days_since_last_fight`: gap to the fight before the current one
- Age: computed at `date_proper`, not at any post-fight date

**What is NOT allowed as a feature:**
- Round-by-round stats from the fight being predicted
- Post-fight records (win/loss updated after the fight)
- Opponent stats from fights after the current fight date

### 5.3 Encoding Consistency Across Splits

The `ColumnTransformer` is fit inside `Pipeline.fit(X_train, y_train)`. When
the pipeline is serialized with `joblib.dump`, the fit state (imputer medians,
scaler mean/std, ordinal categories) is embedded — prediction-time data is
transformed using the exact same parameters as training.

---

## 6. Split

**Requirement:** Temporal split — train on past fights, test on future fights.
Never shuffle before splitting (prevents leakage via future fight stats
appearing in training set for the same era).

**Current split:**
```
Train: 70%  (fights up to ~2021)
Val:   15%  (fights ~2021–2023)  ← used for model selection only
Test:  15%  (fights ~2023–2026)  ← final holdout, never used for selection
```

Split is implemented as row index positions after `df.sort_values("event_date")`.

**Why not k-fold?** Standard k-fold with shuffle would allow 2023 fights to
appear in the training fold when predicting 2020 fights — a severe temporal
leakage. The Stanford paper used time-series k-fold (no shuffle, gap between
folds) to get more stable estimates; our single temporal split is simpler but
equivalent for deployment evaluation.

---

## 7. Common Pitfalls

### 7.1 Data Leakage

| Leakage type | Risk | Status |
|---|---|---|
| **Target leakage** | Using post-fight info (e.g. round stats) to predict outcome | Not applicable — all features are pre-fight |
| **Temporal leakage** | Future fights' stats in training fold | Prevented by temporal sort + no shuffle |
| **Imputation leakage** | Imputing NaN using the full dataset mean | Prevented — `SimpleImputer` is inside Pipeline, fit on X_train only |
| **Scaler leakage** | Standardising using full dataset mean/std | Prevented — `StandardScaler` inside Pipeline |
| **Feature selection leakage** | Running MI/collinearity on full dataset | **Watch:** `select_features.py` currently runs on the full training parquet. Should run on X_train only. Acceptable given the large dataset (MI on full set introduces minor optimistic bias). |

### 7.2 Imbalanced Target

Before perspective flipping, ~64% of rows have `fighter_a_wins=1` (UFCStats
winner-on-left bias). After flipping: ~50%.

Logistic Regression uses `class_weight="balanced"` as an additional safeguard.
XGBoost and RF can also use `scale_pos_weight` if imbalance recurs.

**Check after building parquet:**
```python
print(df["fighter_a_wins"].value_counts(normalize=True))
# Should be ~0.50 / 0.50
```

### 7.3 Overfitting Detection

Monitor the train/test gap for each model:

| Model | Acceptable gap | Red flag |
|---|---|---|
| Logistic Regression | ≤ 3% | > 5% |
| XGBoost | ≤ 5% | > 8% |
| Random Forest | ≤ 5% | > 8% |

Current baselines (post early-stopping fix):
- LR: -1.5% (slight underfit — healthy)
- XGB: 5.4% (acceptable)
- RF: 6.0% (acceptable)

### 7.4 Fighter Identity as a Proxy Feature

Fighter IDs must never be fed to the model. If they were, the model would
learn "Fighter X always wins" — a memorisation of historical record, not a
generalizable pattern. Any new fighter would have no representation.

All features are computed as **A minus B differentials**, making them
independent of which specific fighter holds which ID.

---

## Pre-Training Checklist

```
[ ] fight_id is unique (no duplicate rows)
[ ] fighter_a_wins is 0 or 1 only (NaN rows for draws/NCs already dropped)
[ ] Target balance is ~50/50 (perspective flip applied)
[ ] No ID columns in feature_names (selected_features.json)
[ ] Temporal split used (not random shuffle)
[ ] train_date_max < val_date_min < test_date_min
[ ] Pipeline includes imputer → scaler inside fit (not fit on full data)
[ ] Experiment log entry saved after each training run
[ ] Train/test AUC gap < 8% for tree models
```
