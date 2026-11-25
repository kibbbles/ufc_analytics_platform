/**
 * Pure helpers behind the page field in <Pagination> and the ?page= URL state.
 *
 * Kept out of the component so the rules can be tested without a DOM.
 */

/** Reads a ?page= value. Anything that is not a whole number of 1 or more means page 1. */
export function parsePageParam(raw: string | null | undefined): number {
  if (!raw || !/^\d+$/.test(raw.trim())) return 1
  const n = Number(raw.trim())
  return Number.isSafeInteger(n) && n >= 1 ? n : 1
}

/**
 * What a typed page number resolves to, or null when it should be discarded.
 *
 * Digits only; anything else (letters, a minus sign, a decimal, an empty box)
 * returns null and the field goes back to the current page. A number outside
 * the range is clamped: 0 goes to page 1, 500 of 227 goes to page 227.
 */
export function resolvePageInput(text: string, totalPages: number): number | null {
  const trimmed = text.trim()
  if (!/^\d+$/.test(trimmed) || totalPages < 1) return null
  const n = Number(trimmed)
  if (!Number.isFinite(n)) return null
  return Math.min(Math.max(n, 1), totalPages)
}

/**
 * A copy of the search params with some keys set or removed. null or '' removes
 * a key, and page 1 is written as no ?page= at all, so the first page keeps a
 * clean URL.
 */
export function withParams(
  prev: URLSearchParams,
  changes: Record<string, string | number | null>,
): URLSearchParams {
  const next = new URLSearchParams(prev)
  for (const [key, value] of Object.entries(changes)) {
    const removed = value === null || value === '' || (key === 'page' && Number(value) === 1)
    if (removed) next.delete(key)
    else next.set(key, String(value))
  }
  return next
}
