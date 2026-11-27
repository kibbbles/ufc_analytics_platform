import { useState } from 'react'
import { useApi } from '@hooks/useApi'
import { upcomingService } from '@services/upcomingService'
import { pastPredictionsService } from '@services/pastPredictionsService'
import UpcomingEventAccordion from '@components/features/UpcomingEventAccordion'
import type { MethodRecord } from '@components/features/UpcomingFightCard'
import LoadingSkeleton from '@components/common/LoadingSkeleton'

export default function UpcomingPage() {
  const { data, loading, error } = useApi(() => upcomingService.getEvents(), [])
  // The method pick's live record, shown beside every method breakdown. A
  // failed fetch only drops that line; the card still renders.
  const { data: scorecard } = useApi(() => pastPredictionsService.get(1), [])
  const s = scorecard?.summary
  const methodRecord: MethodRecord | null =
    s && s.method_total > 0
      ? { total: s.method_total, correct: s.method_correct, decisions: s.method_decision_count }
      : null

  // All collapsed by default — user opens what they want
  const [openId, setOpenId] = useState<string>('')

  const events = data?.data ?? []

  function handleToggle(id: string) {
    setOpenId((prev) => (prev === id ? '' : id))
  }

  return (
    <div className="mx-auto max-w-[1100px]">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Upcoming Events</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
          ML win probabilities and method predictions for every announced bout. Refreshed after the Sunday retrain and again on Friday and Saturday, then frozen once a fight starts.
        </p>
        <p className="mt-2 text-[13px] text-[var(--color-text-muted)]">
          Each bar splits a fight between its two fighters. The blue tick marks the Vegas implied chance for the left fighter, so the gap between the split and the tick is how far the model disagrees with the market.
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
        <div className="rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error)]/10 p-6 text-center text-sm text-[var(--color-error-light)] dark:text-[var(--color-error)]">
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
          {events.map((event, index) => (
            <UpcomingEventAccordion
              key={event.id}
              event={event}
              isOpen={openId === event.id}
              isNext={index === 0}
              onToggle={() => handleToggle(event.id)}
              methodRecord={methodRecord}
            />
          ))}
        </div>
      )}
    </div>
  )
}
