import { scrollDeltaToReveal } from '@utils/keyboard'

/**
 * Px kept clear below a focused field: the floating chat button is 56px tall
 * and sits 16px from the bottom, plus 16px of breathing room.
 */
const CLEAR_BELOW = 88
const CLEAR_ABOVE = 16
/** iOS opens the keyboard with an animation; check again once it has settled. */
const SETTLE_MS = 350

/**
 * Keeps a focused field above the on-screen keyboard until it loses focus.
 * Call it from the field's onFocus.
 *
 * On iOS the keyboard covers the page without resizing the layout viewport, so
 * a field near the bottom of the page can end up under it, and when the page is
 * already scrolled to its end there is no room left to scroll the field up. This
 * watches visualViewport (which does shrink), scrolls the field into the visible
 * part, and when the page is too short to scroll that far, pads the bottom of the
 * page while the field has focus. Touch screens only: on desktop there is no
 * keyboard to clear and the page should not jump on click.
 */
export function keepAboveKeyboard(field: HTMLElement): void {
  if (!window.matchMedia?.('(pointer: coarse)').matches) return

  const body = document.body
  const originalPadding = body.style.paddingBottom
  const vv = window.visualViewport

  const reveal = () => {
    const view = vv
      ? { offsetTop: vv.offsetTop, height: vv.height }
      : { offsetTop: 0, height: window.innerHeight }
    const delta = scrollDeltaToReveal(field.getBoundingClientRect(), view, {
      above: CLEAR_ABOVE,
      below: CLEAR_BELOW,
    })
    if (delta <= 0) {
      if (delta < 0) window.scrollBy(0, delta)
      return
    }
    const room = document.documentElement.scrollHeight - window.innerHeight - window.scrollY
    if (delta > room) {
      const current = parseFloat(getComputedStyle(body).paddingBottom) || 0
      body.style.paddingBottom = `${current + delta - room}px`
    }
    window.scrollBy(0, delta)
  }

  vv?.addEventListener('resize', reveal)
  const settle = window.setTimeout(reveal, SETTLE_MS)

  field.addEventListener(
    'blur',
    () => {
      vv?.removeEventListener('resize', reveal)
      window.clearTimeout(settle)
      body.style.paddingBottom = originalPadding
    },
    { once: true },
  )
}
