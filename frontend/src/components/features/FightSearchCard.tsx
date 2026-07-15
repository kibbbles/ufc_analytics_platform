import { Link } from 'react-router-dom'
import { formatDate, EMPTY } from '@utils/format'
import type { FightSearchItem } from '@t/api'

function methodColor(method: string | null): string {
  if (!method) return 'text-[var(--color-text-muted)]'
  const m = method.toUpperCase()
  if (m.includes('KO') || m.includes('TKO')) return 'text-[var(--color-primary)]'
  if (m.includes('SUB')) return 'text-[var(--color-warning-light)] dark:text-[var(--color-warning)]'
  return 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]'
}

export default function FightSearchCard({ fight }: { fight: FightSearchItem }) {
  const hasPred = fight.win_prob_a !== null && fight.win_prob_b !== null
  const winnerIsA = fight.winner_id === fight.fighter_a_id
  const predWinnerIsA = fight.predicted_winner_id === fight.fighter_a_id

  return (
    <Link
      to={`/past-predictions/fights/${fight.fight_id}`}
      className="block rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4 py-3 space-y-1.5 hover:border-[var(--color-primary)]/60 transition-colors lg:text-center"
    >
      {/* Fighter names + winner */}
      <div className="flex items-start justify-between gap-3 lg:justify-center">
        <div className="min-w-0">
          <p className="font-semibold leading-snug">
            <span className={winnerIsA ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}>
              {fight.fighter_a_name ?? '—'}
            </span>
            <span className="mx-1.5 text-[var(--color-text-muted)] font-normal">vs</span>
            <span className={!winnerIsA && fight.winner_id ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : !fight.winner_id ? '' : 'text-[var(--color-text-muted)]'}>
              {fight.fighter_b_name ?? '—'}
            </span>
          </p>
        </div>
        {fight.is_title_fight && !fight.is_interim_title && (
          <span className="shrink-0 text-xs font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-[var(--color-warning)]/20 text-[var(--color-warning-light)] dark:text-[var(--color-warning)]">
            Title
          </span>
        )}
        {fight.is_interim_title && (
          <span className="shrink-0 text-xs font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-[var(--color-warning)]/20 text-[var(--color-warning-light)] dark:text-[var(--color-warning)]">
            Interim
          </span>
        )}
      </div>

      {/* Winner + method */}
      <p className="text-xs">
        <span className="text-[var(--color-text-muted)]">Winner: </span>
        <span className="font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
          {fight.winner_name ?? EMPTY}
        </span>
        {fight.method && (
          <span className={`ml-1.5 font-medium ${methodColor(fight.method)}`}>
            · {fight.method}
            {fight.round != null ? ` (R${fight.round})` : ''}
          </span>
        )}
      </p>

      {/* Event + date */}
      <p className="text-xs text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        {fight.event_name ?? '—'}
        {fight.event_date ? ` · ${formatDate(fight.event_date)}` : ''}
        {fight.weight_class ? ` · ${fight.weight_class}` : ''}
      </p>

      {/* Model row */}
      <div className="flex items-center gap-2 pt-0.5 lg:justify-center">
        <span className="text-xs uppercase tracking-wide font-semibold text-[var(--color-text-muted)]">
          Model
        </span>
        {hasPred ? (
          <>
            <span className="text-xs font-mono tabular-nums text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
              {fight.fighter_a_name?.split(' ').pop()} {(fight.win_prob_a! * 100).toFixed(0)}%
              <span className="mx-1 text-[var(--color-text-muted)]">/</span>
              {fight.fighter_b_name?.split(' ').pop()} {(fight.win_prob_b! * 100).toFixed(0)}%
            </span>
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
              fight.predicted_winner_id === fight.winner_id
                ? 'bg-[var(--color-success)]/15 text-[var(--color-success-light)] dark:text-[var(--color-success)]'
                : 'bg-[var(--color-error)]/15 text-[var(--color-error-light)] dark:text-[var(--color-error)]'
            }`}>
              {fight.predicted_winner_id === fight.winner_id ? '✓' : '✗'}{' '}
              {predWinnerIsA ? fight.fighter_a_name?.split(' ').pop() : fight.fighter_b_name?.split(' ').pop()}
            </span>
          </>
        ) : (
          <span className="text-xs text-[var(--color-text-muted)]">{EMPTY} no prediction</span>
        )}
      </div>
    </Link>
  )
}
