interface PaginationProps {
  page: number
  totalPages: number
  onPrev: () => void
  onNext: () => void
}

export default function Pagination({ page, totalPages, onPrev, onNext }: PaginationProps) {
  if (totalPages <= 1) return null

  return (
    <div className="flex items-center justify-between mt-6 pt-4 border-t border-[var(--color-border)]">
      <button
        onClick={onPrev}
        disabled={page <= 1}
        className="px-4 py-2 text-sm rounded-md border border-[var(--color-border)] disabled:opacity-40 hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] transition-colors"
      >
        ← Previous
      </button>
      <span className="text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        Page {page} of {totalPages}
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
