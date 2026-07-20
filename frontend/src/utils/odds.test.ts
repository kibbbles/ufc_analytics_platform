import { describe, it, expect } from 'vitest'
import {
  EDGE_THRESHOLD,
  americanToImplied,
  americanToPayout,
  applyTypedOdds,
  ev,
  isNegative,
  magnitude,
  parseOdds,
  toggleSign,
} from './odds'

/**
 * Simulates a user typing into the odds field one character at a time, which is
 * how the component actually drives applyTypedOdds - one call per keystroke,
 * each folding the full field value into the signed state.
 */
function type(text: string, start = ''): string {
  let state = start
  for (let i = 1; i <= text.length; i++) {
    state = applyTypedOdds(text.slice(0, i), state)
  }
  return state
}

/** What the two controls display for a given signed state. */
function display(state: string) {
  return { sign: isNegative(state) ? '-' : '+', field: magnitude(state) }
}

describe('American odds math', () => {
  it('converts odds to the break-even win probability', () => {
    expect(americanToImplied(150)).toBeCloseTo(0.4, 10)
    expect(americanToImplied(-150)).toBeCloseTo(0.6, 10)
    expect(americanToImplied(100)).toBeCloseTo(0.5, 10)
    expect(americanToImplied(-100)).toBeCloseTo(0.5, 10)
    expect(americanToImplied(-200)).toBeCloseTo(2 / 3, 10)
  })

  it('returns profit rather than total return', () => {
    expect(americanToPayout(150, 100)).toBeCloseTo(150, 10)
    expect(americanToPayout(-150, 100)).toBeCloseTo(66.666, 2)
    expect(americanToPayout(-150, 50)).toBeCloseTo(33.333, 2)
  })

  it('is zero EV at exactly fair odds', () => {
    expect(ev(0.6, -150, 100)).toBeCloseTo(0, 10)
    expect(ev(0.4, 150, 100)).toBeCloseTo(0, 10)
  })

  it('scales EV linearly with stake', () => {
    expect(ev(0.7, -150, 200)).toBeCloseTo(ev(0.7, -150, 100) * 2, 10)
  })
})

describe('odds entry', () => {
  it('shows the sign once when prefilled from the DB', () => {
    // The shipped double-negative bug: the field rendered "-150" while the
    // toggle also showed a minus.
    expect(display(String(-150))).toEqual({ sign: '-', field: '150' })
  })

  it('lets an iPhone user set the sign by tapping, then type digits', () => {
    // No minus key exists on the iOS numeric keypad, so this is the only path.
    const state = type('150', toggleSign(''))
    expect(display(state)).toEqual({ sign: '-', field: '150' })
    expect(parseOdds(state)).toBe(-150)
  })

  it('absorbs a typed sign into the toggle, not the field', () => {
    const negative = type('-150')
    expect(display(negative)).toEqual({ sign: '-', field: '150' })
    expect(parseOdds(negative)).toBe(-150)

    const positive = type('+130')
    expect(display(positive)).toEqual({ sign: '+', field: '130' })
    expect(parseOdds(positive)).toBe(130)
  })

  it('flips the sign without disturbing the digits', () => {
    expect(display(toggleSign('-150'))).toEqual({ sign: '+', field: '150' })
    expect(display(toggleSign('150'))).toEqual({ sign: '-', field: '150' })
    expect(toggleSign(toggleSign('-150'))).toBe('-150')
  })

  it('keeps the chosen sign while the digits are edited', () => {
    expect(applyTypedOdds('15', '-150')).toBe('-15')
    expect(applyTypedOdds('', '-150')).toBe('-')
    expect(isNegative(applyTypedOdds('', '-150'))).toBe(true)
  })

  it('discards characters that are neither digits nor a sign', () => {
    expect(display(applyTypedOdds('1a5b0', ''))).toEqual({ sign: '+', field: '150' })
    expect(display(applyTypedOdds('-150 ', ''))).toEqual({ sign: '-', field: '150' })
  })
})

describe('parseOdds guard rails', () => {
  it('rejects magnitudes below 100, which are not valid American odds', () => {
    expect(parseOdds('50')).toBeNull()
    expect(parseOdds('-50')).toBeNull()
    expect(parseOdds('99')).toBeNull()
  })

  it('accepts the boundary', () => {
    expect(parseOdds('100')).toBe(100)
    expect(parseOdds('-100')).toBe(-100)
  })

  it('returns null for unusable input rather than a derived number', () => {
    expect(parseOdds('')).toBeNull()
    expect(parseOdds('-')).toBeNull()
    expect(parseOdds('0')).toBeNull()
    expect(parseOdds('abc')).toBeNull()
  })
})

/**
 * The reason this file exists. A dropped sign does not crash and does not look
 * wrong on screen - it inverts the implied probability, which flips the verdict
 * from "pass" to a confident "value" badge on a bet that loses money.
 */
describe('a dropped sign must never reach the EV calculation', () => {
  const verdict = (odds: number, modelProb: number) =>
    modelProb - americanToImplied(odds) > EDGE_THRESHOLD ? 'value' : 'no value'

  it('keeps a break-even favourite break-even', () => {
    const odds = parseOdds(type('150', toggleSign('')))!
    expect(odds).toBe(-150)
    expect(ev(0.6, odds, 100)).toBeCloseTo(0, 10)
    expect(verdict(odds, 0.6)).toBe('no value')
  })

  it('would have called that same bet value if the sign were lost', () => {
    // Documents the blast radius: identical digits, sign dropped, +$50 EV and a
    // green "value" badge on a bet that is actually break-even.
    expect(ev(0.6, 150, 100)).toBeCloseTo(50, 10)
    expect(verdict(150, 0.6)).toBe('value')
  })

  it('keeps a losing bet losing', () => {
    const odds = parseOdds(type('200', toggleSign('')))!
    expect(odds).toBe(-200)
    expect(ev(0.6, odds, 100)).toBeCloseTo(-10, 10)
    expect(verdict(odds, 0.6)).toBe('no value')
  })

  it('survives the full round trip from DB prefill through a sign flip', () => {
    const prefilled = String(-150)
    expect(parseOdds(prefilled)).toBe(-150)
    const flipped = toggleSign(prefilled)
    expect(parseOdds(flipped)).toBe(150)
    expect(parseOdds(toggleSign(flipped))).toBe(-150)
  })
})
