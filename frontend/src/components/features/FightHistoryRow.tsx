import { Link } from 'react-router-dom'
import type { FightListItem } from '@t/api'
import { Badge } from '@components/common'
import { EMPTY } from '@utils/format'

interface FightRowProps {
  fight: FightListItem
  /** When showing a fight in a fighter's profile, pass the fighter's ID to resolve W/L. */
  viewingFighterId?: string
}

function ResultBadge({ fight, fighterId }: { fight: FightListItem; fighterId?: string }) {
  if (!fighterId) return <Badge variant="default">{EMPTY}</Badge>
  if (fight.winner_id === fighterId) return <Badge variant="success">W</Badge>
  if (fight.winner_id !== null) return <Badge variant="danger">L</Badge>
  return <Badge variant="default">{EMPTY}</Badge>
}

export default function FightHistoryRow({ fight, viewingFighterId }: FightRowProps) {
  return (
    <Link
      to={`/past-predictions/fights/${fight.id}`}
      className="flex items-center gap-3 py-3 border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-border)]/10 transition-colors"
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{fight.bout ?? EMPTY}</p>
        <div className="mt-0.5 flex items-center gap-1.5">
          {fight.is_title_fight && !fight.is_interim_title && <Badge variant="warning">Title</Badge>}
          {fight.is_interim_title && <Badge variant="warning">Interim</Badge>}
          <span className="text-xs text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
            {fight.weight_class ?? EMPTY}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        <span className="text-xs">
          {fight.method ? `${fight.method}${fight.round != null ? ` R${fight.round}` : ''}` : EMPTY}
        </span>
        <ResultBadge fight={fight} fighterId={viewingFighterId} />
      </div>
    </Link>
  )
}
