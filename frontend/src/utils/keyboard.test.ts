import { describe, expect, it } from 'vitest'
import { scrollDeltaToReveal } from './keyboard'

const clearance = { above: 16, below: 88 }
// A 390x844 phone with the keyboard up: 500px of the page still visible.
const keyboardUp = { offsetTop: 0, height: 500 }

describe('scrollDeltaToReveal', () => {
  it('leaves a field that already fits alone', () => {
    expect(scrollDeltaToReveal({ top: 200, bottom: 244 }, keyboardUp, clearance)).toBe(0)
  })

  it('scrolls a field hidden under the keyboard up into view, clear of the chat button', () => {
    // Field at 700-744 sits under the keyboard; its bottom must land at 500 - 88 = 412.
    expect(scrollDeltaToReveal({ top: 700, bottom: 744 }, keyboardUp, clearance)).toBe(332)
  })

  it('counts the visual viewport offset when the page is already panned', () => {
    expect(
      scrollDeltaToReveal({ top: 700, bottom: 744 }, { offsetTop: 100, height: 500 }, clearance),
    ).toBe(232)
  })

  it('scrolls back down to a field above the visible area', () => {
    expect(scrollDeltaToReveal({ top: -50, bottom: -6 }, keyboardUp, clearance)).toBe(-66)
  })

  it('never pushes the top of a tall field off the top of the visible area', () => {
    expect(scrollDeltaToReveal({ top: 300, bottom: 800 }, keyboardUp, clearance)).toBe(284)
  })
})
