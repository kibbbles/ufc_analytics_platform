interface PaginationProps {
  page: number
  totalPages: number
  onPrev: () => void
  onNext: () => void
  /** When provided, renders a "Showing X–Y of Z" label */
  total?: number
  pageSize?: number
}

export default function Pagination({ page, totalPages, onPrev, onNext, total, pageSize }: PaginationProps) {
  if (totalPages <= 1 && !total) return null

  const showingLabel = total != null && pageSize != null
    ? (() => {
        const from = (page - 1) * pageSize + 1
        const to = Math.min(page * pageSize, total)
        return `Showing ${from.toLocaleString()}–${to.toLocaleString()} of ${total.toLocaleString()}`
      })()
    : `Page ${page} of ${totalPages}`

  if (totalPages <= 1) {
    return (
      <div className="mt-4 pt-3 text-center text-xs text-[var(--color-text-muted)]">
        {showingLabel}
      </div>
    )
  }

  return (
    <div className="flex items-center justify-between mt-6 pt-4 border-t border-[var(--color-border)]">
      <button
        onClick={onPrev}
        disabled={page <= 1}
        className="px-4 py-2 text-sm rounded-md border border-[var(--color-border)] disabled:opacity-40 hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] transition-colors"
      >
        ← Prev
      </button>
      <span className="text-xs text-[var(--color-text-muted)]">
        {showingLabel}
      </span>
      <button
        onClick={onNext}
        disabled={page >= totalPages}
        className="px-4 py-2 text-sm rounded-md border border-[var(--color-border)] disabled:opacity-40 hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] transition-colors"
      >
        Next →
      </button>
    </div>
  )
}
