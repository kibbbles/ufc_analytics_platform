/**
 * American odds math and odds-entry helpers for the EV calculator.
 *
 * Extracted from OddsCalculator so the sign handling can be tested directly.
 * A dropped sign here does not crash or render visibly wrong - it silently
 * inverts the implied probability, which turns a losing bet into a confident
 * "value" recommendation. See odds.test.ts.
 */

/** Edge above which a bet is called value rather than a thin edge. */
export const EDGE_THRESHOLD = 0.05

/** Break-even win probability the odds imply, ignoring vig. -150 -> 0.6 */
export function americanToImplied(odds: number): number {
  if (odds > 0) return 100 / (odds + 100)
  return -odds / (-odds + 100)
}

/** Profit (not total return) on a winning stake. -150 at $100 -> $66.67 */
export function americanToPayout(odds: number, stake: number): number {
  if (odds > 0) return (stake * odds) / 100
  return (stake * 100) / -odds
}

/** Expected value: (win% x payout) - (loss% x stake). Zero at fair odds. */
export function ev(modelProb: number, odds: number, stake: number): number {
  return modelProb * americanToPayout(odds, stake) - (1 - modelProb) * stake
}

/**
 * Flips the sign of a signed odds string, preserving the magnitude.
 *
 * iOS renders no minus key on the numeric keypad, so the sign is a tap target
 * rather than something the user types.
 */
export function toggleSign(raw: string): string {
  const trimmed = raw.trim()
  if (trimmed.startsWith('-')) return trimmed.slice(1)
  if (trimmed.startsWith('+')) return `-${trimmed.slice(1)}`
  return `-${trimmed}`
}

export function isNegative(raw: string): boolean {
  return raw.trim().startsWith('-')
}

/** The digits alone. The sign is owned by the toggle, not the text field. */
export function magnitude(raw: string): string {
  return raw.trim().replace(/^[-+]/, '')
}

/**
 * Folds a keystroke into the signed state, absorbing any typed or pasted sign
 * into the toggle rather than the field. Typing "-150" on a desktop keyboard
 * still lands on -150. Non-digits are discarded at entry rather than left to
 * fail later in parseOdds.
 */
export function applyTypedOdds(raw: string, current: string): string {
  const digits = raw.replace(/[^0-9]/g, '')
  let negative = isNegative(current)
  if (raw.includes('-')) negative = true
  else if (raw.includes('+')) negative = false
  return negative ? `-${digits}` : digits
}

/**
 * Parses a signed odds string, rejecting values that are not valid American
 * odds. Returns null for anything unusable so callers render an empty state
 * rather than a number derived from garbage.
 */
export function parseOdds(raw: string): number | null {
  const n = Number(raw.replace(/\s/g, ''))
  if (!Number.isFinite(n) || n === 0) return null
  if (n > 0 && n < 100) return null
  if (n < 0 && n > -100) return null
  return n
}
