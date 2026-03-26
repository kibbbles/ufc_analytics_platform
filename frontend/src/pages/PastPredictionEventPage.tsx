import { useParams, Link } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { pastPredictionsService } from '@services/pastPredictionsService'
import LoadingSkeleton from '@components/common/LoadingSkeleton'
import { formatDate } from '@utils/format'
import type { PastPredictionItem } from '@t/api'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPct(value: number | null | undefined): string {
  if (value == null) return '—'
  return (value * 100).toFixed(1) + '%'
}

function winnerName(item: PastPredictionItem, id: string | null | undefined): string {
  if (!id) return '—'
  if (id === item.fighter_a_id) return item.fighter_a_name ?? '—'
  if (id === item.fighter_b_id) return item.fighter_b_name ?? '—'
  return '—'
}

// ---------------------------------------------------------------------------
// Fight row — centered layout, links to fight detail page
// Note: outer container uses div+onClick to avoid nested <a> tags
// ---------------------------------------------------------------------------

function FightRow({ item }: { item: PastPredictionItem }) {
  const isUpset      = item.is_upset
  const isCorrect    = item.is_correct
  const hasPred      = item.predicted_winner_id != null
  const winnerIsA    = item.actual_winner_id === item.fighter_a_id
  const predWinnerIsA = item.predicted_winner_id === item.fighter_a_id

  const resultBadge = !hasPred
    ? { label: '·', cls: 'bg-[var(--color-border)]/40 text-[var(--color-text-muted)]' }
    : isUpset
    ? { label: '~ Upset', cls: 'bg-amber-500/15 text-amber-600 dark:text-amber-400' }
    : isCorrect
    ? { label: '✓', cls: 'bg-green-500/15 text-green-600 dark:text-green-400' }
    : { label: '✗', cls: 'bg-red-500/15 text-red-600 dark:text-red-400' }

  const methodClr = (m: string | null | undefined) => {
    if (!m) return 'text-[var(--color-text-muted)]'
    const u = m.toUpperCase()
    if (u.includes('KO') || u.includes('TKO')) return 'text-[var(--color-primary)]'
    if (u.includes('SUB')) return 'text-amber-500 dark:text-amber-400'
    return 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]'
  }

  return (
    <Link
      to={`/past-predictions/fights/${item.fight_id}`}
      className="block py-3 border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] last:border-0 hover:bg-[var(--color-border)]/10 transition-colors space-y-1.5"
    >
      {/* Fighter names + result badge */}
      <div className="flex items-start justify-between gap-3">
        <p className="font-semibold leading-snug text-sm">
          <span className={winnerIsA ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}>
            {item.fighter_a_name ?? '?'}
          </span>
          <span className="mx-1.5 font-normal text-[var(--color-text-muted)]">vs</span>
          <span className={!winnerIsA && item.actual_winner_id ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : !item.actual_winner_id ? '' : 'text-[var(--color-text-muted)]'}>
            {item.fighter_b_name ?? '?'}
          </span>
        </p>
        <span className={`shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded ${resultBadge.cls}`}>
          {resultBadge.label}
        </span>
      </div>

      {/* Actual result */}
      {item.actual_winner_id && (
        <p className="text-xs">
          <span className="text-[var(--color-text-muted)]">Actual: </span>
          <span className="font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
            {winnerName(item, item.actual_winner_id)}
          </span>
          {item.actual_method && (
            <span className={`ml-1.5 font-medium ${methodClr(item.actual_method)}`}>
              · {item.actual_method}
            </span>
          )}
        </p>
      )}

      {/* Event + date + weight class */}
      <p className="text-xs text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        {item.event_name ?? '—'}
        {item.event_date ? ` · ${formatDate(item.event_date)}` : ''}
        {item.weight_class ? ` · ${item.weight_class}` : ''}
      </p>

      {/* Prediction row */}
      {hasPred && item.win_prob_a != null && item.win_prob_b != null && (
        <div className="flex items-center gap-2 pt-0.5">
          <span className="text-[10px] uppercase tracking-wide font-semibold text-[var(--color-text-muted)]">
            Model
          </span>
          <span className="text-xs font-mono tabular-nums text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
            {item.fighter_a_name?.split(' ').pop()} {formatPct(item.win_prob_a)}
            <span className="mx-1 text-[var(--color-text-muted)]">/</span>
            {item.fighter_b_name?.split(' ').pop()} {formatPct(item.win_prob_b)}
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
            isCorrect
              ? 'bg-green-500/15 text-green-600 dark:text-green-400'
              : 'bg-red-500/15 text-red-600 dark:text-red-400'
          }`}>
            {isCorrect ? '✓' : '✗'}{' '}
            {predWinnerIsA ? item.fighter_a_name?.split(' ').pop() : item.fighter_b_name?.split(' ').pop()}
          </span>
          {item.confidence != null && (
            <span className="text-[10px] text-[var(--color-text-muted)] font-mono tabular-nums">
              · {formatPct(item.confidence)} conviction
            </span>
          )}
        </div>
      )}
    </Link>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function PastPredictionEventPage() {
  const { event_id } = useParams<{ event_id: string }>()
  const { data, loading, error } = useApi(
    () => pastPredictionsService.getEvent(event_id!),
    [event_id],
  )

  return (
    <div className="max-w-2xl mx-auto">
      {/* Back link */}
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] hover:text-[var(--color-primary)] transition-colors mb-6"
      >
        ← Model Scorecard
      </Link>

      {loading && <LoadingSkeleton lines={8} />}

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {data && (
        <>
          {/* Event header */}
          <div className="mb-4 text-center">
            <h1 className="text-2xl font-bold leading-tight">{data.event_name ?? 'UFC Event'}</h1>
            <p className="mt-1 text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              {data.event_date ? formatDate(data.event_date) : '—'}
            </p>
          </div>

          {/* Accuracy summary */}
          <div className="mb-6 rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-surface-light)] dark:bg-[var(--color-surface)] px-4 py-3 text-center">
            <p className="text-sm font-mono tabular-nums">
              <span className="font-semibold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
                {(data.accuracy * 100).toFixed(1)}% accurate
              </span>
              <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                {' · '}{data.correct_count}/{data.fight_count} fights
              </span>
            </p>
          </div>

          {/* Fight list */}
          <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4">
            {data.fights.map((fight) => (
              <FightRow key={fight.fight_id} item={fight} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
