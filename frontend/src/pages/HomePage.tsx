import { Link } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { pastPredictionsService } from '@services/pastPredictionsService'
import LoadingSkeleton from '@components/common/LoadingSkeleton'
import type { PastPredictionItem } from '@t/api'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPct(value: number): string {
  return (value * 100).toFixed(1) + '%'
}

function getWinnerName(item: PastPredictionItem): string {
  if (!item.predicted_winner_id) return '—'
  if (item.predicted_winner_id === item.fighter_a_id) return item.fighter_a_name ?? '—'
  if (item.predicted_winner_id === item.fighter_b_id) return item.fighter_b_name ?? '—'
  return '—'
}

function getActualWinnerName(item: PastPredictionItem): string {
  if (!item.actual_winner_id) return '—'
  if (item.actual_winner_id === item.fighter_a_id) return item.fighter_a_name ?? '—'
  if (item.actual_winner_id === item.fighter_b_id) return item.fighter_b_name ?? '—'
  return '—'
}

// ---------------------------------------------------------------------------
// Subcomponent: single prediction row
// ---------------------------------------------------------------------------

function PredictionRow({ item }: { item: PastPredictionItem }) {
  const isCorrect = item.is_correct
  const isUpset   = item.is_upset

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
    indicatorColor = 'text-red-500'
  }

  const predWinnerName   = getWinnerName(item)
  const actualWinnerName = getActualWinnerName(item)
  const confPct          = item.confidence != null ? formatPct(item.confidence) : '—'
  const predMethod       = item.predicted_method ?? '—'
  const actualMethod     = item.actual_method ?? '—'

  const predWinnerCorrect = item.is_correct === true

  return (
    <div className="flex items-start justify-between gap-3 py-3 border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] last:border-0">
      {/* Left: indicator + names */}
      <div className="flex items-start gap-2 min-w-0">
        <span
          className={`font-mono font-bold text-base mt-0.5 w-4 shrink-0 ${indicatorColor}`}
          aria-label={isCorrect ? 'correct' : isUpset ? 'upset' : 'incorrect'}
        >
          {indicator}
        </span>
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">
            {item.fighter_a_name ?? '?'} vs {item.fighter_b_name ?? '?'}
          </p>
          {item.weight_class && (
            <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              {item.weight_class}
            </p>
          )}
        </div>
      </div>

      {/* Right: prediction + actual */}
      <div className="text-right shrink-0">
        <p className="text-xs">
          <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            Predicted{' '}
          </span>
          <span
            className={
              predWinnerCorrect
                ? 'font-medium text-[var(--color-primary)]'
                : 'text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]'
            }
          >
            {predWinnerName}
          </span>
          <span className="font-mono tabular-nums text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            {' '}{confPct}
          </span>
          <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            {' '}via {predMethod}
          </span>
        </p>
        <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          Actual: {actualWinnerName} via {actualMethod}
        </p>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Model Scorecard section
// ---------------------------------------------------------------------------

function ModelScorecard() {
  const { data, loading } = useApi(() => pastPredictionsService.get(10), [])

  const summary = data?.summary
  const recent  = data?.recent ?? []

  // Derive date range label
  let dateLabel = 'Test set'
  if (summary?.date_from) {
    const from = summary.date_from.slice(0, 7) // "YYYY-MM"
    const to   = summary.date_to ? summary.date_to.slice(0, 4) : 'present'
    // Format like "Jan 2022 – present"
    const fromDate = new Date(summary.date_from + 'T00:00:00')
    const fromStr  = fromDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
    dateLabel = `Test set · ${fromStr} – present`
  }

  return (
    <section>
      {/* Section header */}
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="text-xl font-bold">Model Scorecard</h2>
        <span className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          {dateLabel}
        </span>
      </div>

      {loading ? (
        <LoadingSkeleton lines={6} />
      ) : (
        <>
          {/* Summary stats */}
          {summary && summary.total_fights > 0 ? (
            <div className="mb-5 flex flex-wrap items-end gap-x-6 gap-y-1">
              <div className="flex items-end gap-2">
                <span className="font-mono text-4xl font-bold leading-none">
                  {formatPct(summary.accuracy)}
                </span>
                <span className="text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] mb-0.5">
                  accurate
                </span>
              </div>
              <div className="text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                <span className="font-mono tabular-nums text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
                  {summary.correct}/{summary.total_fights}
                </span>
                {' '}fights
              </div>
              {summary.high_conf_fights > 0 && (
                <div className="text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                  <span className="font-mono tabular-nums text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
                    {formatPct(summary.high_conf_accuracy)}
                  </span>
                  {' '}when ≥65% confident
                </div>
              )}
            </div>
          ) : (
            <p className="mb-5 text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              No predictions yet — run the backfill script to populate.
            </p>
          )}

          {/* Recent predictions list */}
          {recent.length > 0 && (
            <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-surface-light)] dark:bg-[var(--color-surface)] px-4 divide-y-0">
              {recent.map((item) => (
                <PredictionRow key={item.fight_id} item={item} />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function HomePage() {
  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-3xl font-bold">UFC Analytics</h1>
        <p className="mt-2 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
          ML-powered fight predictions and historical analysis
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { title: 'Upcoming Card', desc: "Pre-computed predictions for this Saturday's event", to: '/upcoming' },
          { title: 'Completed Events', desc: 'Browse historical UFC events and full fight cards', to: '/events' },
          { title: 'Fight Predictor', desc: 'Win probability + method breakdown for any matchup', to: '/predictions' },
          { title: 'Fighter Lookup', desc: 'Search any fighter — record, stats, fight history', to: '/fighters' },
        ].map((card) => (
          <Link
            key={card.to}
            to={card.to}
            className="block p-5 rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-surface-light)] dark:bg-[var(--color-surface)] hover:border-[var(--color-primary)] transition-colors"
          >
            <h2 className="font-semibold">{card.title}</h2>
            <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
              {card.desc}
            </p>
          </Link>
        ))}
      </div>

      <ModelScorecard />
    </div>
  )
}
