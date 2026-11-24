import { Link } from 'react-router-dom'
import type { FightListItem } from '@t/api'
import { Badge } from '@components/common'
import { EMPTY } from '@utils/format'
import { listedFight } from '@utils/fightSides'

interface FightRowProps {
  fight: FightListItem
  /** When showing a fight in a fighter's profile, pass the fighter's ID to resolve W/L. */
  viewingFighterId?: string
}

function ResultBadge({ fight, fighterId }: { fight: FightListItem; fighterId?: string }) {
  // No viewing fighter means there is no perspective for W/L to be relative to —
  // an event card has no "did he win?" to answer. That is not missing data, so it
  // gets no placeholder; the winner is conveyed by Bout instead.
  if (!fighterId) return null
  if (fight.winner_id === fighterId) return <Badge variant="success">W</Badge>
  if (fight.winner_id !== null) return <Badge variant="danger">L</Badge>
  return <Badge variant="default">{EMPTY}</Badge>
}

/**
 * Renders "A vs. B" with the winner at full weight and the loser muted.
 *
 * Each name is the one the API joined to that fighter's id; the BOUT string is
 * never split by position. Falls back to flat, unemphasised text whenever the
 * winner cannot be resolved: a draw or no-contest, a winner id that is neither
 * fighter, or a response without the joined names.
 */
function Bout({ fight }: { fight: FightListItem }) {
  const { a, b, won } = listedFight(fight)

  if (a.name === EMPTY || b.name === EMPTY) return <>{fight.bout || EMPTY}</>
  if (won === null) return <>{`${a.name} vs. ${b.name}`}</>

  const [nameA, nameB] = [a.name, b.name]
  const aWon = won === 'a'
  // The loser's name is content, not decoration, so it stays on the secondary text
  // token rather than muted — muted lands at 3.5:1 on the card surface, under AA.
  const winnerClass = 'font-semibold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
  const loserClass = 'font-normal text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]'

  return (
    <>
      <span className={aWon ? winnerClass : loserClass}>{nameA}</span>
      <span className="font-normal text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
        {' '}
        vs.{' '}
      </span>
      <span className={aWon ? loserClass : winnerClass}>{nameB}</span>
    </>
  )
}

export default function FightHistoryRow({ fight, viewingFighterId }: FightRowProps) {
  return (
    <Link
      to={`/past-predictions/fights/${fight.id}`}
      className="flex items-center gap-3 py-3 border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-border)]/10 active:bg-[var(--color-border)]/20 transition-colors"
    >
      <div className="flex-1 min-w-0">
        {/* Wraps below sm so the winner is never the half that gets clipped;
            truncates from sm up, where the row has width to spare. */}
        <p className="text-sm font-medium sm:truncate">
          <Bout fight={fight} />
        </p>
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
