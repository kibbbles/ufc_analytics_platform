// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { keepAboveKeyboard } from './keepAboveKeyboard'

/** A phone with the keyboard up: 844px layout viewport, 500px of it still visible. */
function fakePhone({ coarse = true } = {}) {
  const viewport = Object.assign(new EventTarget(), { offsetTop: 0, height: 500 })
  vi.stubGlobal('visualViewport', viewport)
  vi.stubGlobal('innerHeight', 844)
  vi.stubGlobal('matchMedia', (q: string) => ({ matches: coarse && q === '(pointer: coarse)' }))
  const scrollBy = vi.fn()
  vi.stubGlobal('scrollBy', scrollBy)
  return { viewport, scrollBy }
}

function fieldAt(top: number) {
  const field = document.createElement('input')
  document.body.appendChild(field)
  field.getBoundingClientRect = () => ({ top, bottom: top + 44 }) as DOMRect
  return field
}

function pageHeight(px: number) {
  Object.defineProperty(document.documentElement, 'scrollHeight', { value: px, configurable: true })
}

beforeEach(() => vi.useFakeTimers())
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
  document.body.style.paddingBottom = ''
})

describe('keepAboveKeyboard', () => {
  it('scrolls a field under the keyboard up, clear of the chat button, when the keyboard opens', () => {
    const { viewport, scrollBy } = fakePhone()
    pageHeight(5000)
    const field = fieldAt(700)
    keepAboveKeyboard(field)
    viewport.dispatchEvent(new Event('resize'))
    // Bottom edge 744 must land at 500 visible - 88 clearance = 412.
    expect(scrollBy).toHaveBeenCalledWith(0, 332)
    expect(document.body.style.paddingBottom).toBe('')
  })

  it('pads the page end when it is too short to scroll that far, and removes it on blur', () => {
    const { scrollBy } = fakePhone()
    pageHeight(844) // already at the very end: no room left to scroll
    const field = fieldAt(700)
    keepAboveKeyboard(field)
    vi.runAllTimers()
    expect(document.body.style.paddingBottom).toBe('332px')
    expect(scrollBy).toHaveBeenCalledWith(0, 332)
    field.dispatchEvent(new Event('blur'))
    expect(document.body.style.paddingBottom).toBe('')
  })

  it('stops watching the keyboard once the field loses focus', () => {
    const { viewport, scrollBy } = fakePhone()
    const field = fieldAt(700)
    keepAboveKeyboard(field)
    field.dispatchEvent(new Event('blur'))
    viewport.dispatchEvent(new Event('resize'))
    vi.runAllTimers()
    expect(scrollBy).not.toHaveBeenCalled()
  })

  it('does nothing with a mouse, so the desktop page never jumps on click', () => {
    const { viewport, scrollBy } = fakePhone({ coarse: false })
    const field = fieldAt(700)
    keepAboveKeyboard(field)
    viewport.dispatchEvent(new Event('resize'))
    vi.runAllTimers()
    expect(scrollBy).not.toHaveBeenCalled()
  })
})
