/**
 * How an observed win rate compares with the probability that was predicted for it.
 * - 'over':  wins came in clearly below the prediction (the prediction was too high)
 * - 'under': wins came in clearly above the prediction (the prediction was too low)
 * - 'noise': the gap is within two binomial standard errors, so the sample cannot tell it apart from chance
 */
export type CalibrationVerdict = 'over' | 'under' | 'noise'

export function calibrationVerdict(
  predicted: number,
  actual: number,
  fights: number,
): CalibrationVerdict {
  if (fights <= 0) return 'noise'
  const se = Math.sqrt((predicted * (1 - predicted)) / fights)
  const gap = actual - predicted
  if (Math.abs(gap) <= 2 * se) return 'noise'
  return gap < 0 ? 'over' : 'under'
}
