import { useState } from 'react'
import { useApi } from '@hooks/useApi'
import { upcomingService } from '@services/upcomingService'
import UpcomingEventAccordion from '@components/features/UpcomingEventAccordion'
import LoadingSkeleton from '@components/common/LoadingSkeleton'

export default function UpcomingPage() {
  const { data, loading, error } = useApi(() => upcomingService.getEvents(), [])

  // Track which event is open; null = use first event as default
  const [openId, setOpenId] = useState<string | null>(null)

  const events = data?.data ?? []
  const firstId = events[0]?.id ?? null
  // Auto-open first event until user explicitly toggles
  const resolvedOpenId = openId === null && firstId ? firstId : openId

  function handleToggle(id: string) {
    setOpenId((prev) => (prev === id ? '' : id))
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Upcoming Events</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
          ML win probabilities and method predictions for every announced bout.
        </p>
      </div>

      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }, (_, i) => (
            <div
              key={i}
              className="rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] p-4"
            >
              <LoadingSkeleton lines={2} />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {!loading && !error && events.length === 0 && (
        <p className="py-16 text-center text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
          No upcoming events found.
        </p>
      )}

      {!loading && !error && events.length > 0 && (
        <div className="space-y-3">
          {events.map((event) => (
            <UpcomingEventAccordion
              key={event.id}
              event={event}
              isOpen={resolvedOpenId === event.id}
              onToggle={() => handleToggle(event.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
