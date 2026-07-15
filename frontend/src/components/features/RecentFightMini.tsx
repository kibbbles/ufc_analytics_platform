import { Link } from 'react-router-dom'
import type { FightListItem } from '@t/api'
import { EMPTY } from '@utils/format'

interface Props {
  fights: FightListItem[]
  viewingFighterId: string
}

/** Compact W/L opponent list for one fighter, shared by the upcoming and past fight pages. */
export default function RecentFightMini({ fights, viewingFighterId }: Props) {
  return (
    <div className="space-y-2">
      {fights.map((f) => {
        const parts = (f.bout ?? '').split(' vs. ')
        const isA = f.fighter_a_id === viewingFighterId
        const opponentRaw = (isA ? parts[1] : parts[0] ?? '').trim()
        const opponentLastName = opponentRaw.split(' ').at(-1) ?? EMPTY
        const opponentId = isA ? f.fighter_b_id : f.fighter_a_id
        const isWin = f.winner_id === viewingFighterId
        const isLoss = f.winner_id !== null && f.winner_id !== viewingFighterId
        return (
          <div key={f.id} className="flex items-center gap-2 text-sm">
            <span
              className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-bold tabular-nums ${
                isWin
                  ? 'bg-[var(--color-success)]/15 text-[var(--color-success-light)] dark:text-[var(--color-success)]'
                  : isLoss
                  ? 'bg-[var(--color-error)]/15 text-[var(--color-error-light)] dark:text-[var(--color-error)]'
                  : 'bg-[var(--color-border)] text-[var(--color-text-muted)]'
              }`}
            >
              {isWin ? 'W' : isLoss ? 'L' : EMPTY}
            </span>
            {opponentId ? (
              <Link
                to={`/fighters/${opponentId}`}
                className="font-medium hover:text-[var(--color-primary)] transition-colors"
              >
                {opponentLastName}
              </Link>
            ) : (
              <span className="font-medium text-[var(--color-text-muted)]">{opponentLastName}</span>
            )}
          </div>
        )
      })}
    </div>
  )
}
