// Phase 2 — Task 17-19: Upcoming event predictions
export default function UpcomingPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Upcoming Event Predictions</h1>
      <p className="mt-2 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        Pre-computed ML predictions for this Saturday's fight card, refreshed every Friday.
      </p>
      <div className="mt-8 flex items-center justify-center h-48 rounded-lg border border-dashed border-[var(--color-border-light)] dark:border-[var(--color-border)]">
        <span className="text-[var(--color-text-muted)]">Upcoming card predictions — Phase 2 (Tasks 17-19)</span>
      </div>
    </div>
  )
}
