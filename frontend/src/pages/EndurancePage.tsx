// Task 10 — Fighter Endurance & Pacing Dashboard
export default function EndurancePage() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Fighter Endurance Dashboard</h1>
      <p className="mt-2 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        Round-by-round performance profiles and cardio predictions.
      </p>
      <div className="mt-8 flex items-center justify-center h-64 rounded-lg border border-dashed border-[var(--color-border-light)] dark:border-[var(--color-border)]">
        <span className="text-[var(--color-text-muted)]">Endurance charts — Task 10</span>
      </div>
    </div>
  )
}
