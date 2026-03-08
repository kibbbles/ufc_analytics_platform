import { Link } from 'react-router-dom'
import type { EventResponse } from '@t/api'
import { formatDate } from '@utils/format'

interface EventCardProps {
  event: EventResponse
}

export default function EventCard({ event }: EventCardProps) {
  return (
    <Link
      to={`/events/${event.id}`}
      className="block rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] p-5 hover:border-[var(--color-primary)] transition-colors group"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="font-semibold truncate group-hover:text-[var(--color-primary)] transition-colors">
            {event.name ?? 'Untitled Event'}
          </h2>
          {event.location && (
            <p className="mt-0.5 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] truncate">
              {event.location}
            </p>
          )}
        </div>
        {event.event_date && (
          <time
            dateTime={event.event_date}
            className="shrink-0 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]"
          >
            {formatDate(event.event_date)}
          </time>
        )}
      </div>
      <p className="mt-3 text-xs font-medium text-[var(--color-primary)]">View fight card →</p>
    </Link>
  )
}
