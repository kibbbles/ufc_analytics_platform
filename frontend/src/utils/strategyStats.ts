import type { BettingFightRow } from '@t/api'

// The one hard line. Below this many bets a result is never a finding: it is
// shown for transparency but stripped of its verdict and its colour. Mirrors
// the analysis-rigor rule (a difference under n=50 cannot be told from noise).
export const N_CONCLUSIVE = 50

// Sportsbook margin. Beating the favorite baseline is not the real bar; beating
// it by more than the house edge is. Used to caveat thin positive edges.
export const VIG = 0.045

// ── Temporal train/test boundary for the held-out confirmation set ───────────
//
// WHY 2026-06-01 specifically:
//   The fights carrying Vegas odds span 2026-03-21 .. 2026-07-18 — the window
//   since pre-fight odds archiving began. 2026-06-01 is the clean month
//   boundary that splits that window ~2:1: 103 fights before it (exploration,
//   comfortably above the 50-fight bar) and 52 on/after it (confirmation, which
//   grows as new events land). Older fights explore; newer fights confirm, so a
//   strategy is judged out-of-sample on fights that happened AFTER it could
//   have been picked.
//
// DO NOT move this cutoff to make a strategy look better. Sliding a train/test
// boundary to improve a backtest is the single most common way backtests lie.
// If it ever genuinely must change (e.g. the odds window is re-scoped), that is
// a deliberate decision with a written reason recorded here - never a tuning
// knob turned to chase a nicer number.
export const CONFIRMATION_CUTOFF = '2026-06-01'

export type PlSource = 'model' | 'fav' | 'dog' | 'younger'

// Per-fight P&L (flat $1 stake) for a bet source. Null when the source does not
// apply to a fight (e.g. no known ages for the younger strategy).
export function plOf(f: BettingFightRow, src: PlSource): number | null {
  switch (src) {
    case 'fav': return f.pl_fav
    case 'dog': return f.pl_dog
    case 'younger': return f.pl_younger
    default: return f.pl_model
  }
}

const mean = (xs: number[]): number => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0)

// Deterministic PRNG (mulberry32) so the bootstrap CI is stable across renders
// for the same fights instead of jittering on every re-render.
function mulberry32(seed: number): () => number {
  return function () {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export interface CI { lo: number; hi: number }

// Percentile bootstrap CI of the mean P&L (= ROI at a flat $1 stake), in the
// same fractional units as ROI. Null under 2 samples.
export function bootstrapRoiCI(pls: number[], iters = 2000): CI | null {
  const n = pls.length
  if (n < 2) return null
  const rand = mulberry32((0x9e3779b1 ^ n ^ Math.round(mean(pls) * 1e6)) >>> 0)
  const means = new Array<number>(iters)
  for (let b = 0; b < iters; b++) {
    let s = 0
    for (let i = 0; i < n; i++) s += pls[(rand() * n) | 0]
    means[b] = s / n
  }
  means.sort((a, b) => a - b)
  const q = (p: number) => means[Math.min(iters - 1, Math.max(0, Math.floor(p * iters)))]
  return { lo: q(0.025), hi: q(0.975) }
}

export type VerdictKind =
  | 'beats'        // strategy CI clears the baseline on the upside
  | 'loses'        // strategy CI clears the baseline on the downside
  | 'tie'          // CI overlaps the baseline: indistinguishable, never "beats"
  | 'inconclusive' // n < 50: no verdict, ever
  | 'is-baseline'  // strategy IS the favorite baseline; nothing to compare

export interface StrategyEval {
  kind: VerdictKind
  n: number
  strategyRoi: number   // fraction
  baselineRoi: number   // fraction, always-favorite on the SAME fights
  ci: CI | null         // strategy ROI CI, fraction
  deltaPts: number      // (strategy - baseline) * 100, points of ROI
  clearsVig: boolean    // could this plausibly beat the house edge?
}

// Evaluate a strategy against the always-favorite baseline computed on the SAME
// fights (paired, identical n). Verdict is gated on the strategy's CI clearing
// the baseline point estimate - a within-noise win reads "tie", never "beats".
export function evaluateStrategy(fights: BettingFightRow[], src: PlSource): StrategyEval {
  const usable = fights.filter(f => plOf(f, src) != null)
  const pls = usable.map(f => plOf(f, src) as number)
  const n = pls.length
  const strategyRoi = mean(pls)
  const baselineRoi = mean(usable.map(f => f.pl_fav))
  const ci = bootstrapRoiCI(pls)
  const deltaPts = (strategyRoi - baselineRoi) * 100
  const clearsVig = ci != null && ci.hi > VIG

  let kind: VerdictKind
  if (src === 'fav') kind = 'is-baseline'
  else if (n < N_CONCLUSIVE || !ci) kind = 'inconclusive'
  else if (baselineRoi < ci.lo) kind = 'beats'
  else if (baselineRoi > ci.hi) kind = 'loses'
  else kind = 'tie'

  return { kind, n, strategyRoi, baselineRoi, ci, deltaPts, clearsVig }
}

// Split fights at the fixed temporal cutoff. Older -> exploration, newer ->
// confirmation. Fights without a date fall into exploration (they cannot be the
// out-of-sample future).
export function splitAtCutoff(fights: BettingFightRow[]): {
  exploration: BettingFightRow[]
  confirmation: BettingFightRow[]
} {
  const exploration: BettingFightRow[] = []
  const confirmation: BettingFightRow[] = []
  for (const f of fights) {
    if (f.event_date && f.event_date >= CONFIRMATION_CUTOFF) confirmation.push(f)
    else exploration.push(f)
  }
  return { exploration, confirmation }
}
