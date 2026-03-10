import { useState } from 'react'
import { useApi } from '@hooks/useApi'
import { upcomingService } from '@services/upcomingService'
import UpcomingEventAccordion from '@components/features/UpcomingEventAccordion'
import LoadingSkeleton from '@components/common/LoadingSkeleton'

export default function UpcomingPage() {
  const { data, loading, error } = useApi(() => upcomingService.getEvents(), [])

  // All collapsed by default — user opens what they want
  const [openId, setOpenId] = useState<string>('')

  const events = data?.data ?? []

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
        <div className="mx-auto max-w-2xl space-y-3">
          {events.map((event, index) => (
            <UpcomingEventAccordion
              key={event.id}
              event={event}
              isOpen={openId === event.id}
              isNext={index === 0}
              onToggle={() => handleToggle(event.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
