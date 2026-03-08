import { useParams } from 'react-router-dom'

// Task 7.6 — Fighter detail (wired up in 7.6)
export default function FighterDetailPage() {
  const { id } = useParams<{ id: string }>()
  return (
    <div>
      <h1 className="text-2xl font-bold">Fighter Profile</h1>
      <p className="mt-2 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        Fighter ID: <code className="font-mono text-[var(--color-accent)]">{id}</code>
      </p>
      <div className="mt-8 flex items-center justify-center h-48 rounded-lg border border-dashed border-[var(--color-border-light)] dark:border-[var(--color-border)]">
        <span className="text-[var(--color-text-muted)]">Fighter profile — Task 7.6</span>
      </div>
    </div>
  )
}
