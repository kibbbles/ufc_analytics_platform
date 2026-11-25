import { describe, it, expect } from 'vitest'
import { parsePageParam, resolvePageInput, withParams } from './pagination'

describe('resolvePageInput - what the page field does with typed text', () => {
  it('goes to a page in range', () => {
    expect(resolvePageInput('50', 227)).toBe(50)
    expect(resolvePageInput(' 7 ', 227)).toBe(7)
  })

  it('clamps numbers outside the range', () => {
    expect(resolvePageInput('500', 227)).toBe(227)
    expect(resolvePageInput('0', 227)).toBe(1)
    expect(resolvePageInput('99999999999999999999', 227)).toBe(227)
  })

  it('discards anything that is not a whole number', () => {
    for (const text of ['', '   ', 'abc', '-3', '2.5', '1e3', '12a']) {
      expect(resolvePageInput(text, 227)).toBeNull()
    }
  })

  it('discards input when there are no pages', () => {
    expect(resolvePageInput('1', 0)).toBeNull()
  })
})

describe('parsePageParam - reading ?page= from the URL', () => {
  it('reads a page number', () => {
    expect(parsePageParam('50')).toBe(50)
  })

  it('falls back to page 1 for missing or bad values', () => {
    for (const raw of [null, undefined, '', '0', '-2', 'abc', '3.5', '99999999999999999999']) {
      expect(parsePageParam(raw)).toBe(1)
    }
  })
})

describe('withParams - updating the URL', () => {
  it('sets the page and keeps other params', () => {
    const next = withParams(new URLSearchParams('tab=events&q=ufc'), { page: 4 })
    expect(next.toString()).toBe('tab=events&q=ufc&page=4')
  })

  it('writes page 1 as no ?page= at all', () => {
    expect(withParams(new URLSearchParams('page=9&q=silva'), { page: 1 }).toString()).toBe(
      'q=silva',
    )
  })

  it('removes a cleared search and resets the page together', () => {
    expect(
      withParams(new URLSearchParams('q=silva&page=3'), { q: '', page: null }).toString(),
    ).toBe('')
  })

  it('does not change the params it was given', () => {
    const prev = new URLSearchParams('page=2')
    withParams(prev, { page: 5 })
    expect(prev.toString()).toBe('page=2')
  })
})
