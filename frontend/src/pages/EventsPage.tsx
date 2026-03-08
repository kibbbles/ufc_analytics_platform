// Task 7.6 — Recent Events view (wired up in 7.6)
export default function EventsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Recent Events</h1>
      <p className="mt-2 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        Latest UFC events with full fight card results.
      </p>
      <div className="mt-8 flex items-center justify-center h-48 rounded-lg border border-dashed border-[var(--color-border-light)] dark:border-[var(--color-border)]">
        <span className="text-[var(--color-text-muted)]">Events list — Task 7.6</span>
      </div>
    </div>
  )
}
