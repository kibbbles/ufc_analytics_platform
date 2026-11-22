import { describe, it, expect } from 'vitest'
import { calibrationVerdict } from './calibration'

describe('calibrationVerdict', () => {
  it('flags a prediction that ran well above the observed win rate', () => {
    // Live 60-70% bin: says 64%, wins 50.5% over 99 fights (SE ~4.8pp, gap ~13.6pp)
    expect(calibrationVerdict(0.641, 0.505, 99)).toBe('over')
  })

  it('flags a prediction that ran well below the observed win rate', () => {
    expect(calibrationVerdict(0.55, 0.7, 200)).toBe('under')
  })

  it('treats a gap inside two standard errors as noise', () => {
    // Vegas 50-60% bucket: implied 55.6%, actual 59.8% over 92 fights (SE ~5.2pp)
    expect(calibrationVerdict(0.556, 0.598, 92)).toBe('noise')
  })

  it('treats an empty bin as noise rather than dividing by zero', () => {
    expect(calibrationVerdict(0.6, 0, 0)).toBe('noise')
  })
})
