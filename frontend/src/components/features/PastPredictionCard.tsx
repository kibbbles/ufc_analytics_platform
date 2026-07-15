import { Link } from 'react-router-dom'
import { Badge } from '@components/common'
import { formatDate, formatPct } from '@utils/format'
import type { PastPredictionItem } from '@t/api'

// ── Shared helpers ────────────────────────────────────────────────────────────

function winnerName(item: PastPredictionItem, id: string | null | undefined): string {
  if (!id) return '—'
  if (id === item.fighter_a_id) return item.fighter_a_name ?? '—'
  if (id === item.fighter_b_id) return item.fighter_b_name ?? '—'
  return '—'
}

function methodColor(m: string | null | undefined): string {
  if (!m) return 'text-[var(--color-text-muted)]'
  const u = m.toUpperCase()
  if (u.includes('KO') || u.includes('TKO')) return 'text-[var(--color-primary)]'
  if (u.includes('SUB')) return 'text-[var(--color-warning-light)] dark:text-[var(--color-warning)]'
  return 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]'
}

interface Props {
  item: PastPredictionItem
  /**
   * `search` — a standalone bordered card, used in the fight-search results list.
   * `event`  — a borderless row inside a shared event container.
   */
  variant: 'search' | 'event'
}

export default function PastPredictionCard({ item, variant }: Props) {
  return variant === 'search' ? <SearchLayout item={item} /> : <EventLayout item={item} />
}

// ── search variant (HomePage fight search) ────────────────────────────────────

function SearchLayout({ item }: { item: PastPredictionItem }) {
  const isUpset = item.is_upset
  const isCorrect = item.is_correct

  let indicator: string
  let color: string
  if (isUpset)        { indicator = '~'; color = 'text-[var(--color-warning-light)] dark:text-[var(--color-warning)]' }
  else if (isCorrect) { indicator = '✓'; color = 'text-[var(--color-success-light)] dark:text-[var(--color-success)]' }
  else                { indicator = '✗'; color = 'text-[var(--color-primary)]' }

  const predWinner = winnerName(item, item.predicted_winner_id)
  const actualWinner = winnerName(item, item.actual_winner_id)

  return (
    <Link
      to={`/past-predictions/fights/${item.fight_id}`}
      className="block rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4 py-3 hover:border-[var(--color-primary)]/50 transition-colors lg:text-center"
    >
      {/* Matchup header */}
      <div className="flex items-start gap-2 mb-1.5 lg:justify-center">
        <span className={`font-mono font-bold text-sm mt-0.5 w-4 shrink-0 ${color}`}>{indicator}</span>
        <div className="min-w-0 flex-1 lg:flex-none">
          <p className="text-sm font-semibold leading-tight truncate">
            {item.fighter_a_name ?? '?'} vs {item.fighter_b_name ?? '?'}
          </p>
          <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] truncate">
            {item.event_name ?? '—'}
            {item.event_date ? ` · ${formatDate(item.event_date)}` : ''}
            {item.weight_class ? ` · ${item.weight_class}` : ''}
          </p>
        </div>
      </div>
      {/* Prediction vs actual */}
      <div className="ml-6 space-y-0.5 lg:ml-0">
        <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          <span className="w-16 inline-block">Predicted</span>
          <span className={isCorrect ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : ''}>
            {predWinner}
          </span>
          {item.predicted_method && <span> via {item.predicted_method}</span>}
        </p>
        <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          <span className="w-16 inline-block">Actual</span>
          <span className="text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
            {actualWinner}
          </span>
          {item.actual_method && <span> via {item.actual_method}</span>}
        </p>
        {item.confidence != null && (
          <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            <span className="w-16 inline-block">Conviction</span>
            <span className="font-mono font-semibold tabular-nums">{formatPct(item.confidence)}</span>
          </p>
        )}
      </div>
    </Link>
  )
}

// ── event variant (Past Prediction event page) ────────────────────────────────

function EventLayout({ item }: { item: PastPredictionItem }) {
  const isUpset = item.is_upset
  const isCorrect = item.is_correct
  const hasPred = item.predicted_winner_id != null
  const winnerIsA = item.actual_winner_id === item.fighter_a_id
  const predWinnerIsA = item.predicted_winner_id === item.fighter_a_id

  const resultBadge = !hasPred
    ? { label: '·', cls: 'bg-[var(--color-border)]/40 text-[var(--color-text-muted)]' }
    : isUpset
    ? { label: '~ Upset', cls: 'bg-[var(--color-warning)]/15 text-[var(--color-warning-light)] dark:text-[var(--color-warning)]' }
    : isCorrect
    ? { label: '✓', cls: 'bg-[var(--color-success)]/15 text-[var(--color-success-light)] dark:text-[var(--color-success)]' }
    : { label: '✗', cls: 'bg-[var(--color-error)]/15 text-[var(--color-error-light)] dark:text-[var(--color-error)]' }

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
        <span className={`shrink-0 text-xs font-semibold px-1.5 py-0.5 rounded ${resultBadge.cls}`}>
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
            <span className={`ml-1.5 font-medium ${methodColor(item.actual_method)}`}>
              · {item.actual_method}
            </span>
          )}
        </p>
      )}

      {/* Event + date + weight class + title badge */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {item.is_title_fight && !item.is_interim_title && <Badge variant="warning">Title</Badge>}
        {item.is_interim_title && <Badge variant="warning">Interim</Badge>}
        <p className="text-xs text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
          {item.event_name ?? '—'}
          {item.event_date ? ` · ${formatDate(item.event_date)}` : ''}
          {item.weight_class ? ` · ${item.weight_class}` : ''}
        </p>
      </div>

      {/* Prediction row */}
      {hasPred && item.win_prob_a != null && item.win_prob_b != null && (
        <div className="flex items-center gap-2 pt-0.5">
          <span className="text-xs uppercase tracking-wide font-semibold text-[var(--color-text-muted)]">
            Model
          </span>
          <span className="text-xs font-mono tabular-nums text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
            {item.fighter_a_name?.split(' ').pop()} {formatPct(item.win_prob_a)}
            <span className="mx-1 text-[var(--color-text-muted)]">/</span>
            {item.fighter_b_name?.split(' ').pop()} {formatPct(item.win_prob_b)}
          </span>
          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
            isCorrect
              ? 'bg-[var(--color-success)]/15 text-[var(--color-success-light)] dark:text-[var(--color-success)]'
              : 'bg-[var(--color-error)]/15 text-[var(--color-error-light)] dark:text-[var(--color-error)]'
          }`}>
            {isCorrect ? '✓' : '✗'}{' '}
            {predWinnerIsA ? item.fighter_a_name?.split(' ').pop() : item.fighter_b_name?.split(' ').pop()}
          </span>
          {item.confidence != null && (
            <span className="text-xs text-[var(--color-text-muted)] font-mono tabular-nums">
              · {formatPct(item.confidence)} conviction
            </span>
          )}
        </div>
      )}
    </Link>
  )
}
