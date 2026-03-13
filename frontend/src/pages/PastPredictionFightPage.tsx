import { useParams, Link, useNavigate } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { pastPredictionsService } from '@services/pastPredictionsService'
import LoadingSkeleton from '@components/common/LoadingSkeleton'
import { formatDate } from '@utils/format'
import type { PastPredictionItem } from '@t/api'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pct(v: number | null | undefined, decimals = 1): string {
  if (v == null) return '—'
  return (v * 100).toFixed(decimals) + '%'
}

function winnerName(item: PastPredictionItem, id: string | null | undefined): string {
  if (!id) return '—'
  if (id === item.fighter_a_id) return item.fighter_a_name ?? '—'
  if (id === item.fighter_b_id) return item.fighter_b_name ?? '—'
  return '—'
}

// ---------------------------------------------------------------------------
// Win probability bar
// ---------------------------------------------------------------------------

function WinProbBar({ item }: { item: PastPredictionItem }) {
  const probA = item.win_prob_a ?? 0.5
  const probB = item.win_prob_b ?? 0.5
  const pctA  = (probA * 100).toFixed(1)
  const pctB  = (probB * 100).toFixed(1)

  const actualWinsA = item.actual_winner_id === item.fighter_a_id

  return (
    <div className="my-6">
      {/* Fighter name labels */}
      <div className="flex justify-between mb-1 text-sm font-semibold">
        <Link
          to={`/fighters/${item.fighter_a_id}`}
          className={`hover:text-[var(--color-primary)] transition-colors ${actualWinsA ? '' : 'text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]'}`}
        >
          {item.fighter_a_name ?? 'Fighter A'}
        </Link>
        <Link
          to={`/fighters/${item.fighter_b_id}`}
          className={`hover:text-[var(--color-primary)] transition-colors ${!actualWinsA ? '' : 'text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]'}`}
        >
          {item.fighter_b_name ?? 'Fighter B'}
        </Link>
      </div>

      {/* Probability bar */}
      <div className="relative h-8 rounded-full overflow-hidden flex">
        <div
          className="bg-[var(--color-primary)] flex items-center justify-center text-white text-xs font-mono font-bold"
          style={{ width: `${probA * 100}%` }}
        >
          {Number(pctA) >= 20 ? pctA + '%' : ''}
        </div>
        <div
          className="bg-[var(--color-text-muted-light)] dark:bg-[var(--color-text-muted)] flex items-center justify-center text-white text-xs font-mono font-bold flex-1"
        >
          {Number(pctB) >= 20 ? pctB + '%' : ''}
        </div>
      </div>

      {/* Predicted winner label */}
      <p className="mt-1.5 text-xs text-center text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
        Model predicted{' '}
        <span className="font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
          {winnerName(item, item.predicted_winner_id)}
        </span>
        {item.confidence != null && (
          <span className="font-mono tabular-nums"> ({pct(item.confidence)} confident)</span>
        )}
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Method breakdown
// ---------------------------------------------------------------------------

function MethodBreakdown({ item }: { item: PastPredictionItem }) {
  const methods = [
    { label: 'KO / TKO',   value: item.pred_method_ko_tko },
    { label: 'Submission', value: item.pred_method_sub },
    { label: 'Decision',   value: item.pred_method_dec },
  ]
  const maxVal = Math.max(...methods.map((m) => m.value ?? 0))

  return (
    <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] p-4 mb-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] mb-3">
        Method Prediction
      </h3>
      <div className="space-y-2">
        {methods.map(({ label, value }) => {
          const v = value ?? 0
          const isTop = v === maxVal
          return (
            <div key={label} className="flex items-center gap-2">
              <span className="w-24 shrink-0 text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                {label}
              </span>
              <div className="flex-1 h-2 rounded-full bg-[var(--color-border-light)] dark:bg-[var(--color-border)] overflow-hidden">
                <div
                  className={`h-full rounded-full ${isTop ? 'bg-[var(--color-primary)]' : 'bg-[var(--color-text-muted-light)] dark:bg-[var(--color-text-muted)]'}`}
                  style={{ width: `${v * 100}%` }}
                />
              </div>
              <span className="w-10 shrink-0 text-right font-mono text-xs tabular-nums">
                {pct(v)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Actual result card
// ---------------------------------------------------------------------------

function ActualResult({ item }: { item: PastPredictionItem }) {
  const isUpset   = item.is_upset
  const isCorrect = item.is_correct

  let label: string
  let bgClass: string
  let textClass: string
  if (isUpset) {
    label = 'Upset — model was confident but wrong'
    bgClass = 'bg-amber-500/10 border-amber-500/30'
    textClass = 'text-amber-600 dark:text-amber-400'
  } else if (isCorrect) {
    label = 'Correct prediction'
    bgClass = 'bg-green-500/10 border-green-500/30'
    textClass = 'text-green-600 dark:text-green-400'
  } else {
    label = 'Incorrect prediction'
    bgClass = 'bg-red-500/10 border-red-500/30'
    textClass = 'text-red-600 dark:text-red-400'
  }

  const actualWinner = winnerName(item, item.actual_winner_id)

  return (
    <div className={`rounded-lg border p-4 mb-4 ${bgClass}`}>
      <p className={`text-xs font-semibold uppercase tracking-wide mb-2 ${textClass}`}>{label}</p>
      <p className="text-sm">
        <span className="font-semibold">{actualWinner}</span>
        {item.actual_method && (
          <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            {' '}via {item.actual_method}
          </span>
        )}
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function PastPredictionFightPage() {
  const { fight_id } = useParams<{ fight_id: string }>()
  const navigate     = useNavigate()
  const { data: item, loading, error } = useApi(
    () => pastPredictionsService.getFight(fight_id!),
    [fight_id],
  )

  return (
    <div className="max-w-2xl mx-auto">
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] hover:text-[var(--color-primary)] transition-colors mb-6"
      >
        ← Back
      </button>

      {loading && <LoadingSkeleton lines={10} />}

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {item && (
        <>
          {/* Event context */}
          <div className="mb-1 text-center">
            <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              {item.event_name ?? ''}
              {item.event_date ? ` · ${formatDate(item.event_date)}` : ''}
            </p>
            {item.weight_class && (
              <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                {item.weight_class}
              </p>
            )}
          </div>

          {/* Win probability bar */}
          <WinProbBar item={item} />

          {/* Method breakdown */}
          <MethodBreakdown item={item} />

          {/* Actual result */}
          <ActualResult item={item} />
        </>
      )}
    </div>
  )
}
