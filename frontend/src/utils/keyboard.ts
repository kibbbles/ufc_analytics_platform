/**
 * Math behind keeping a focused field above the on-screen keyboard.
 *
 * Kept free of the DOM so the rules can be tested without a browser.
 */

export interface Box {
  top: number
  bottom: number
}

export interface VisibleArea {
  /** Where the visible area starts, in layout-viewport pixels (visualViewport.offsetTop). */
  offsetTop: number
  /** How tall the visible area is (visualViewport.height, which shrinks when the keyboard opens). */
  height: number
}

/**
 * How far to scroll the page so the field sits inside the visible area, with
 * `above` px clear at the top and `below` px clear at the bottom. Positive
 * scrolls down, negative up, 0 when it already fits. When the field can't fit
 * with both margins, the top margin wins so the field is never pushed off the top.
 */
export function scrollDeltaToReveal(
  field: Box,
  view: VisibleArea,
  clearance: { above: number; below: number },
): number {
  const visibleTop = view.offsetTop + clearance.above
  const visibleBottom = view.offsetTop + view.height - clearance.below
  if (field.bottom > visibleBottom)
    return Math.min(field.bottom - visibleBottom, field.top - visibleTop)
  if (field.top < visibleTop) return field.top - visibleTop
  return 0
}
