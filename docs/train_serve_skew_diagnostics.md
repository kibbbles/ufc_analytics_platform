# Diagnosing a Train/Serve Skew in the Fight Predictor

## Bottom line

A user-reported wrong number led to two inference bugs that silently corrupted every live and upcoming prediction the model has ever made.
The bugs were fixed and the fix was verified against an independent reference implementation (a 111/111 exact feature match).
The honest outcome: the corrected model still does not beat the Vegas favorite baseline.
On the live track record it scores 56.3% against the favorite's 66.2%, and when it disagrees with the market it is right about a third of the time.
This document records what broke, why it was invisible, how it was verified fixed, and what the fix did and did not change.

## The reported symptom

The upcoming-fight prediction for Paddy Pimblett showed a +6.00 win-streak differential in his favor.
Pimblett had just lost to Justin Gaethje, so his current win streak was zero.
A feature that is supposed to encode "who is on a better run" was reporting the opposite of reality.

## Bug 1: sorting fights by hash instead of date

`build_prediction_features` selected a fighter's "current" career state by sorting their fights and taking the last row.
It sorted by `fight_id`, which is an alphanumeric hash, not by date.
Legacy fight IDs are lowercase hex strings; newer UFCStats IDs are uppercase six-character strings.
Uppercase characters sort before lowercase ones, so a fighter's most recent fight frequently did not land last.
For Pimblett the code selected a 2025 fight as "most recent" and read his win streak from it, ignoring the later loss.
The correct sort key is `date_proper`, with `fight_id` only as a tiebreaker.

## Bug 2: the pre-fight lag and the train/serve skew

The deeper bug was structural and affected far more than streaks.

Every per-fighter feature - streaks, rolling striking and grappling metrics, style ratios, opponent quality - is computed with a one-fight shift.
For a given fight, the feature value reflects the fighter's history strictly before that fight.
This is correct and deliberate for training: the model must not see a fight's own outcome when predicting it.

At inference the old code read each fighter's features from their most recent existing fight row.
Because that row is itself shifted, the value excluded the fighter's most recent fight.
So the model was trained on features that include a fighter's latest fight and served features that exclude it.
That is a train/serve skew: the input distribution at serving time differed from the input distribution the model learned on.
The skew applied to the entire feature vector, not just streaks.

## Why `win_rate_diff` was worse

`win_rate_diff` is one of the model's selected features.
The inference code never assigned it.
The final step filters the feature dictionary to the selected features with `feat.get(key)`, so a key that is never produced becomes `None`.
A `None` feature is then imputed to the training median by the model pipeline's imputer.
The result was not a missing value or an error.
It was a plausible, middle-of-the-distribution number fed to the model on every single prediction, in place of a real signal.

## Why none of this was visible

None of these bugs threw an error or produced an obviously broken output.
The sort bug returned a real fighter's real streak, just from the wrong fight.
The lag returned real rolling statistics, just one fight stale.
The null `win_rate_diff` returned the training median, a perfectly reasonable-looking value.
Every prediction came out as a normal probability between zero and one.
The only way to catch this class of bug is to check specific values against ground truth, which is what the Pimblett report forced.
"Silently plausible" is the failure mode, not "loud and broken."

## The fix

The fix reuses the existing shift-based feature builders instead of adding a parallel code path that could drift from them.
For each fighter it appends a synthetic "upcoming fight" row dated as of the prediction, then runs the normal builders and selects that row.
Because every builder shifts a row's own values out, the synthetic row aggregates all of a fighter's completed fights - the correct current state - using the exact math the training matrix uses.
No feature builder and no training code was modified.
This also resolves `win_rate_diff`, which falls out of the same career-statistics row that produces the streaks.

## Verification

The corrected inference path was checked against the training matrix, which is the independent implementation that builds the model's training data and the backtest.
For historical fights, the two should produce identical feature values, because both compute a fighter's state from the same prior fights.
Across the non-streak features they matched exactly: 111 of 111 cells within two percent, largest gap 0.0%.
The Pimblett streak differential moved from -6 to +4, which matches the fighters' actual records.
A structural guard was added to `build_prediction_features` that raises if any selected feature is not produced, and a completeness check was wired into retraining that fails if a feature is null across every one of several veteran matchups.
These turn the silent-null failure mode into a loud one.

## What the fix did and did not change

The fix corrected the features. It did not make the model good.

The bug lived only in the inference path, which powers live and upcoming predictions.
The backtest reads features from the training matrix, which was never affected, so the backtest was always computed on correct features.
On the 142 live fights that carry betting odds, always picking the Vegas favorite is right 66.2% of the time.
The model, on the same fights, is right 56.3%.
Where the model disagrees with the market - its only source of potential edge - it is right about 33% of the time.
The corrected model, evaluated in backtest, still lands well below the favorite baseline.

The train/serve skew is the one concrete reason to expect corrected live predictions to behave somewhat better than the buggy ones did, because the model is finally served the feature distribution it was trained on.
That is a reason for cautious optimism about consistency, not a claim that the model beats the market.
It does not.

## A second problem: weekly re-selection variance

The training pipeline trained three models - logistic regression, random forest, gradient boosting - and deployed whichever scored best on validation AUC that week.
The three are within roughly 0.003 AUC of each other, which is noise.
As a result the deployed model flip-flopped between the three from week to week.
Broken down by which model happened to be deployed, the live accuracy looked dramatic: 67.9% for gradient boosting, 60.5% for random forest, 48.9% for logistic regression.
Those splits are small samples (28, 86, and 47 fights) and the spread is sampling noise, not real model-quality differences.
On the validation set all three sit within about one percentage point on accuracy, AUC, log loss, and Brier score.
Weekly re-selection was therefore swapping the deployed artifact on noise, which added variance to the live track record for no benefit.

Evaluated out-of-sample on the 142 live fights that carry betting odds, the three models rank differently than on validation, which is exactly what "within noise" looks like in practice:

| Model | Accuracy | 95% CI | vs Vegas favorite |
|---|---|---|---|
| Vegas favorite | 66.2% | [58.1, 73.5] | - |
| Random Forest | 60.6% | [52.3, 68.2] | -5.6pp |
| Gradient Boosting | 59.2% | [50.9, 66.9] | -7.0pp |
| Logistic Regression | 52.1% | [43.9, 60.2] | -14.1pp |

All three lose to the favorite baseline, and their confidence intervals overlap each other and the baseline.
Logistic regression wins the validation set but ranks last on this particular test sample, while random forest is the reverse.
Neither ordering is statistically distinguishable, which is the point: the choice among these three is noise.
The pin is set to logistic regression because it has the lowest validation Brier score, meaning it is the best-calibrated of the three, which matters most for a product that displays probabilities.

The selection now pins logistic regression.
All three models are still trained and their metrics logged every retrain, so a genuine future divergence remains visible, and retraining alerts if another model beats the pinned one on Brier by more than the noise band.
The reporting and alerting metric was changed from AUC to Brier score, because the product displays win probabilities and a conviction level derived from them.
AUC measures only ranking and is blind to calibration.
Brier score rewards probabilities that are actually calibrated, which is what the interface shows.

## Calibration: are the displayed probabilities honest?

Binning the live predictions by the probability shown for the model's pick and comparing to the actual hit rate:

| Model said | Actually won | Fights |
|---|---|---|
| 54.5% | 59.5% | 116 |
| 63.6% | 54.8% | 42 |
| 74.4% | 50.0% | 2 |
| 83.8% | 100.0% | 1 |

The model is roughly honest near the coin flip, where most of its predictions sit.
In the 60-80% range it is overconfident: it claims 64-74% and wins 50-55%.
It almost never makes a high-confidence call, and the few it made are too sparse to judge.
This is now shown on the scorecard, so a viewer can see for themselves whether a displayed percentage means what it says.

## Data loss: UFC 329 has no live pre-fight prediction

UFC 329 (2026-07-11) has no live pre-fight prediction, and this is disclosed rather than papered over.

Two failures compounded.
The GitHub Actions database credential was not updated after a password rotation, so the archive workflow that freezes pre-fight snapshots had been failing for a week.
Then a bulk recompute of the upcoming predictions, run to apply the streak fix, overwrote UFC 329's original snapshot with an after-the-event vector before it could be frozen.
The original pre-fight prediction existed nowhere else and is permanently gone.

The event's results are ingested normally; only its prediction is missing.
No snapshot was fabricated to fill the hole, because a reconstructed prediction dated after the event would contradict the entire point of a pre-fight record.
The defect that allowed the overwrite was fixed: a bulk recompute now refuses to touch any event whose date has passed.

## What this project demonstrates

The portfolio-worthy result here is not a winning model.
It is a train/serve skew that was invisible until the values were checked against ground truth, a fix verified against an independent implementation to an exact match, and a model that, once its inputs were correct, still honestly does not beat the market.
A fight predictor built on physical differentials and rolling box-score statistics does not clear the closing line, which is the expected result against a reasonably efficient market.
Surfacing that on the front page, next to the baseline it fails to beat, is the honest version.
