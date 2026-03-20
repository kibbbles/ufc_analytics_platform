import { useParams, Link, useNavigate } from 'react-router-dom'
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
  const navigate  = useNavigate()
  const isUpset   = item.is_upset
  const isCorrect = item.is_correct

  const hasPrediction = item.predicted_winner_id != null

  let indicator: string
  let indicatorColor: string
  if (!hasPrediction)  { indicator = '·'; indicatorColor = 'text-[var(--color-text-muted)]' }
  else if (isUpset)    { indicator = '~'; indicatorColor = 'text-amber-500' }
  else if (isCorrect)  { indicator = '✓'; indicatorColor = 'text-green-500' }
  else                 { indicator = '✗'; indicatorColor = 'text-[var(--color-primary)]' }

  const predWinner   = winnerName(item, item.predicted_winner_id)
  const actualWinner = winnerName(item, item.actual_winner_id)

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => navigate(`/past-predictions/fights/${item.fight_id}`)}
      onKeyDown={(e) => e.key === 'Enter' && navigate(`/past-predictions/fights/${item.fight_id}`)}
      className="py-4 border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] last:border-0 hover:bg-[var(--color-border-light)]/30 dark:hover:bg-[var(--color-border)]/20 cursor-pointer transition-colors"
    >
      {/* Indicator + matchup — centered */}
      <div className="flex flex-col items-center text-center gap-1 mb-2">
        <span
          className={`font-mono font-bold text-lg ${indicatorColor}`}
          aria-label={isUpset ? 'upset' : isCorrect ? 'correct' : 'incorrect'}
        >
          {indicator}
        </span>
        <p className="text-sm font-semibold leading-tight">
          <Link
            to={`/fighters/${item.fighter_a_id}`}
            onClick={(e) => e.stopPropagation()}
            className="hover:text-[var(--color-primary)] transition-colors"
          >
            {item.fighter_a_name ?? '?'}
          </Link>
          <span className="font-normal text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            {' vs '}
          </span>
          <Link
            to={`/fighters/${item.fighter_b_id}`}
            onClick={(e) => e.stopPropagation()}
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

      {/* Predicted vs actual — centered */}
      <div className="flex flex-col items-center gap-0.5">
        <p className="text-xs text-center">
          {hasPrediction ? (
            <>
              <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                Predicted{' '}
              </span>
              <span className={isCorrect ? 'font-medium text-[var(--color-primary)]' : ''}>
                {predWinner}
              </span>
              {item.predicted_method && (
                <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                  {' '}via {item.predicted_method}
                </span>
              )}
            </>
          ) : (
            <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] italic">
              No prediction
            </span>
          )}
        </p>
        <p className="text-xs text-center">
          <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            Actual{' '}
          </span>
          <span className="font-medium">{actualWinner}</span>
          {item.actual_method && (
            <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              {' '}via {item.actual_method}
            </span>
          )}
        </p>
        {item.confidence != null && (
          <p className="text-xs text-center text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] mt-0.5">
            conviction{' '}
            <span className="font-mono tabular-nums font-semibold">
              {formatPct(item.confidence)}
            </span>
          </p>
        )}
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
