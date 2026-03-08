import { useParams, Link } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { eventsService } from '@services/eventsService'
import { LoadingSkeleton, Card } from '@components/common'
import { FightRow } from '@components/features'
import { formatDate } from '@utils/format'

export default function EventDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data, loading, error } = useApi(
    () => eventsService.getById(id!),
    [id],
  )

  return (
    <div>
      <Link
        to="/events"
        className="inline-flex items-center gap-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors mb-6"
      >
        ← All events
      </Link>

      {loading && (
        <div className="space-y-4">
          <LoadingSkeleton lines={2} />
          <div className="mt-6 rounded-lg border border-[var(--color-border)] p-5">
            <LoadingSkeleton lines={8} />
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {data && !loading && (
        <>
          <div className="mb-6">
            <h1 className="text-2xl font-bold">{data.name ?? 'Untitled Event'}</h1>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
              {data.event_date && (
                <time dateTime={data.event_date}>{formatDate(data.event_date)}</time>
              )}
              {data.location && (
                <>
                  <span aria-hidden="true">·</span>
                  <span>{data.location}</span>
                </>
              )}
            </div>
          </div>

          <Card header={<h2 className="font-semibold text-sm uppercase tracking-wide">Fight Card</h2>}>
            {data.fights.length === 0 ? (
              <p className="py-6 text-center text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
                No fight results available for this event.
              </p>
            ) : (
              <div className="-my-1">
                {data.fights.map((fight) => (
                  <FightRow key={fight.id} fight={fight} />
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  )
}
