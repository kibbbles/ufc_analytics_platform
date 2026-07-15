import { Link } from 'react-router-dom'
import type { FighterListItem } from '@t/api'
import { EMPTY } from '@utils/format'

interface FighterCardProps {
  fighter: FighterListItem
}

export default function FighterCard({ fighter }: FighterCardProps) {
  const name = [fighter.first_name, fighter.last_name].filter(Boolean).join(' ') || EMPTY
  // Never fabricate a 0-0; a missing win or loss count discloses the gap.
  const record =
    fighter.wins != null && fighter.losses != null ? `${fighter.wins}-${fighter.losses}` : EMPTY

  return (
    <Link
      to={`/fighters/${fighter.id}`}
      className="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4 py-3 hover:border-[var(--color-primary)] transition-colors group"
    >
      <div className="min-w-0">
        <p className="font-medium truncate group-hover:text-[var(--color-primary)] transition-colors">
          {name}
        </p>
        <p className="text-xs text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] mt-0.5">
          {fighter.weight_class ?? EMPTY}
        </p>
      </div>
      <span className="shrink-0 ml-4 text-sm font-mono tabular-nums text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        {record}
      </span>
    </Link>
  )
}
