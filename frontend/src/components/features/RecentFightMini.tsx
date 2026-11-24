import { Link } from 'react-router-dom'
import type { FightListItem } from '@t/api'
import { EMPTY } from '@utils/format'
import { opponentOf } from '@utils/fightSides'

interface Props {
  fights: FightListItem[]
  viewingFighterId: string
}

/** Compact W/L opponent list for one fighter, shared by the upcoming and past fight pages. */
export default function RecentFightMini({ fights, viewingFighterId }: Props) {
  return (
    <div className="space-y-2">
      {fights.map((f) => {
        // The opponent is found by id and named by the name joined to that id,
        // never by splitting the bout string by position.
        const opponent = opponentOf(f, viewingFighterId)
        const opponentLastName =
          opponent && opponent.name !== EMPTY ? (opponent.name.split(' ').at(-1) ?? EMPTY) : EMPTY
        const opponentId = opponent?.id ?? null
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
