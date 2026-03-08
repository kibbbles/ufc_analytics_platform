import { Link } from 'react-router-dom'
import type { FighterListItem } from '@t/api'

interface FighterCardProps {
  fighter: FighterListItem
}

export default function FighterCard({ fighter }: FighterCardProps) {
  const name =
    [fighter.first_name, fighter.last_name].filter(Boolean).join(' ') || 'Unknown Fighter'
  const record = `${fighter.wins ?? 0}-${fighter.losses ?? 0}`

  return (
    <Link
      to={`/fighters/${fighter.id}`}
      className="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4 py-3 hover:border-[var(--color-primary)] transition-colors group"
    >
      <div className="min-w-0">
        <p className="font-medium truncate group-hover:text-[var(--color-primary)] transition-colors">
          {name}
        </p>
        {fighter.weight_class && (
          <p className="text-xs text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] mt-0.5">
            {fighter.weight_class}
          </p>
        )}
      </div>
      <span className="shrink-0 ml-4 text-sm font-mono tabular-nums text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        {record}
      </span>
    </Link>
  )
}
