import { Link } from 'react-router-dom'
import type { EventResponse } from '@t/api'
import { formatDate, EMPTY } from '@utils/format'

interface EventCardProps {
  event: EventResponse
}

export default function EventCard({ event }: EventCardProps) {
  return (
    <Link
      to={`/events/${event.id}`}
      className="flex items-center justify-between gap-4 rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4 py-3 hover:border-[var(--color-primary)]/60 transition-colors group"
    >
      {/* Left: name + date */}
      <div className="min-w-0">
        <p className="font-semibold leading-snug truncate group-hover:text-[var(--color-primary)] transition-colors">
          {event.name ?? EMPTY}
        </p>
        <time
          dateTime={event.event_date ?? undefined}
          className="text-xs text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]"
        >
          {event.event_date ? formatDate(event.event_date) : EMPTY}
        </time>
      </div>

      {/* Right: location */}
      <p className="shrink-0 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] text-right max-w-[40%] truncate">
        {event.location ?? EMPTY}
      </p>
    </Link>
  )
}
