import { useParams, Link } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { pastPredictionsService } from '@services/pastPredictionsService'
import LoadingSkeleton from '@components/common/LoadingSkeleton'
import PastPredictionCard from '@components/features/PastPredictionCard'
import { formatDate } from '@utils/format'

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
        <div className="rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error)]/10 p-6 text-center text-sm text-[var(--color-error-light)] dark:text-[var(--color-error)]">
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
              <PastPredictionCard key={fight.fight_id} variant="event" item={fight} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
