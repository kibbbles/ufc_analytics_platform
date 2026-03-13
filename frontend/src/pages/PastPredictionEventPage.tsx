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
// Fight prediction row
// ---------------------------------------------------------------------------

function FightRow({ item }: { item: PastPredictionItem }) {
  const isUpset   = item.is_upset
  const isCorrect = item.is_correct

  let indicator: string
  let indicatorColor: string
  if (isUpset) {
    indicator      = '~'
    indicatorColor = 'text-amber-500'
  } else if (isCorrect) {
    indicator      = '✓'
    indicatorColor = 'text-green-500'
  } else {
    indicator      = '✗'
    indicatorColor = 'text-[var(--color-primary)]'
  }

  const predWinner   = winnerName(item, item.predicted_winner_id)
  const actualWinner = winnerName(item, item.actual_winner_id)

  return (
    <div className="py-4 border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] last:border-0">
      {/* Matchup header */}
      <div className="flex items-start gap-2 mb-2">
        <span
          className={`font-mono font-bold text-base mt-0.5 w-5 shrink-0 ${indicatorColor}`}
          aria-label={isUpset ? 'upset' : isCorrect ? 'correct' : 'incorrect'}
        >
          {indicator}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold leading-tight">
            <Link
              to={`/fighters/${item.fighter_a_id}`}
              className="hover:text-[var(--color-primary)] transition-colors"
            >
              {item.fighter_a_name ?? '?'}
            </Link>
            <span className="font-normal text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              {' vs '}
            </span>
            <Link
              to={`/fighters/${item.fighter_b_id}`}
              className="hover:text-[var(--color-primary)] transition-colors"
            >
              {item.fighter_b_name ?? '?'}
            </Link>
          </p>
          {item.weight_class && (
            <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              {item.weight_class}
            </p>
          )}
        </div>
      </div>

      {/* Predicted vs Actual — two-row compact layout */}
      <div className="ml-7 space-y-1">
        <p className="text-xs">
          <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] w-16 inline-block">
            Predicted
          </span>
          <span className={isCorrect ? 'font-medium text-[var(--color-primary)]' : ''}>
            {predWinner}
          </span>
          {item.confidence != null && (
            <span className="font-mono tabular-nums text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              {' '}{formatPct(item.confidence)}
            </span>
          )}
          {item.predicted_method && (
            <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              {' '}via {item.predicted_method}
            </span>
          )}
        </p>
        <p className="text-xs">
          <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] w-16 inline-block">
            Actual
          </span>
          <span className="font-medium">
            {actualWinner}
          </span>
          {item.actual_method && (
            <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              {' '}via {item.actual_method}
            </span>
          )}
        </p>
      </div>
    </div>
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
    <div>
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
          <div className="mb-6">
            <h1 className="text-2xl font-bold leading-tight">{data.event_name ?? 'UFC Event'}</h1>
            <p className="mt-1 text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              {data.event_date ? formatDate(data.event_date) : '—'}
            </p>
          </div>

          {/* Accuracy summary bar */}
          <div className="mb-6 rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-surface-light)] dark:bg-[var(--color-surface)] px-4 py-3">
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
