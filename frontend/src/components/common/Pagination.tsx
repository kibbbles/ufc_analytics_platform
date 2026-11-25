import { useId, useRef, useState } from 'react'
import { resolvePageInput } from '@utils/pagination'

interface PaginationProps {
  page: number
  totalPages: number
  onPrev: () => void
  onNext: () => void
  /** When provided, renders a "Showing X–Y of Z" label */
  total?: number
  pageSize?: number
  /**
   * When provided, the page number becomes a field the user can type into
   * (Red Hat Design System pagination: Enter jumps to the typed page).
   */
  onPageChange?: (page: number) => void
}

// 44px tall (min-h-11): the touch target Red Hat's default size and WCAG AAA call for.
const BUTTON =
  'min-h-11 px-4 text-sm rounded-md border border-[var(--color-border)] transition-colors ' +
  'disabled:opacity-40 enabled:hover:border-[var(--color-primary)] enabled:hover:text-[var(--color-primary)] ' +
  'enabled:active:border-[var(--color-primary)] enabled:active:text-[var(--color-primary)] enabled:active:bg-[var(--color-primary)]/10'

function showingLabel(page: number, total: number, pageSize: number) {
  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)
  return `Showing ${from.toLocaleString()}–${to.toLocaleString()} of ${total.toLocaleString()}`
}

/**
 * The page field. Typing does nothing until the user leaves the field, by
 * pressing Enter or Go, tapping the keyboard's Done/✓, or tapping elsewhere;
 * then it jumps. Leaving is the one commit path: the iOS number pad has no
 * Enter key, only Done, which just closes the keyboard. Escape puts the
 * current page back. Out-of-range numbers are clamped, anything that is not a
 * number is discarded.
 */
function PageField({
  page,
  totalPages,
  onPageChange,
}: {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}) {
  // null while the user is not editing: the field shows the current page.
  const [draft, setDraft] = useState<string | null>(null)
  const ofId = useId()
  // Set by Escape so the blur it triggers puts the current page back instead of jumping.
  const discard = useRef(false)

  function commit() {
    const target = discard.current ? null : resolvePageInput(draft ?? '', totalPages)
    discard.current = false
    setDraft(null)
    if (target !== null && target !== page) onPageChange(target)
  }

  return (
    <label className="flex items-center justify-center gap-2 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
      <span>Page</span>
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        enterKeyHint="go"
        autoComplete="off"
        aria-label="Page number"
        aria-describedby={ofId}
        value={draft ?? String(page)}
        onChange={e => setDraft(e.target.value)}
        onFocus={e => e.target.select()}
        onBlur={commit}
        onKeyDown={e => {
          if (e.key === 'Enter') {
            e.preventDefault()
            e.currentTarget.blur()
          } else if (e.key === 'Escape') {
            discard.current = true
            e.currentTarget.blur()
          }
        }}
        className="min-h-11 w-16 rounded-md border border-[var(--color-border)] bg-transparent px-2 text-center font-mono tabular-nums text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)] focus:border-[var(--color-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)]"
      />
      <span id={ofId}>
        of <span className="font-mono tabular-nums">{totalPages.toLocaleString()}</span>
      </span>
    </label>
  )
}

export default function Pagination({
  page,
  totalPages,
  onPrev,
  onNext,
  total,
  pageSize,
  onPageChange,
}: PaginationProps) {
  if (totalPages <= 1 && !total) return null

  const range = total != null && pageSize != null ? showingLabel(page, total, pageSize) : null

  if (totalPages <= 1) {
    return (
      <div className="mt-4 pt-3 text-center text-xs text-[var(--color-text-muted)]">
        {range ?? `Page ${page} of ${totalPages}`}
      </div>
    )
  }

  // The page-field layout drops the words "Prev"/"Next" in a container narrower
  // than 340px (phones under about 372px wide), keeping the arrows and a 44px
  // square target, so all three controls stay on one row.
  const compact = Boolean(onPageChange)
  const word = compact ? 'hidden @min-[340px]:inline' : undefined

  const prev = (
    <button
      type="button"
      onClick={onPrev}
      disabled={page <= 1}
      aria-label="Previous page"
      className={`${BUTTON} min-w-11`}
    >
      <span aria-hidden="true">←</span>
      <span className={word}> Prev</span>
    </button>
  )
  const next = (
    <button
      type="button"
      onClick={onNext}
      disabled={page >= totalPages}
      aria-label="Next page"
      className={`${BUTTON} min-w-11`}
    >
      <span className={word}>Next </span>
      <span aria-hidden="true">→</span>
    </button>
  )

  if (!onPageChange) {
    return (
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-[var(--color-border)]">
        {prev}
        <span className="text-xs text-[var(--color-text-muted)]">
          {range ?? `Page ${page} of ${totalPages}`}
        </span>
        {next}
      </div>
    )
  }

  // Page field in the middle at every size: Prev, field, Next on one row, which
  // is also the focus order. (Red Hat puts the field after numbered page links
  // on desktop and below the arrows on phones; this list has no numbered links,
  // so the field takes the middle instead.)
  return (
    <nav
      aria-label="Page navigation"
      className="@container mt-6 pt-4 border-t border-[var(--color-border)]"
    >
      <div className="flex items-center justify-between gap-2">
        {prev}
        <PageField page={page} totalPages={totalPages} onPageChange={onPageChange} />
        {next}
      </div>
      {range && <p className="mt-3 text-center text-xs text-[var(--color-text-muted)]">{range}</p>}
    </nav>
  )
}
