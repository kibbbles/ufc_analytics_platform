// Task 7.6 — Fighter/Database Lookup (scaffold, wired up in 7.6)
export default function FightersPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Fighter Lookup</h1>
      <p className="mt-2 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        Search any UFC fighter by name to view their profile and fight history.
      </p>
      <div className="mt-8 flex items-center justify-center h-48 rounded-lg border border-dashed border-[var(--color-border-light)] dark:border-[var(--color-border)]">
        <span className="text-[var(--color-text-muted)]">Fighter search — Task 7.6</span>
      </div>
    </div>
  )
}
