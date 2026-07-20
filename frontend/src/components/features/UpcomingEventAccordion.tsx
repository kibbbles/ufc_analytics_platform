import { useState, useEffect, useRef } from 'react'
import { upcomingService } from '@services/upcomingService'
import type { UpcomingEventListItem, UpcomingEventWithFights } from '@t/api'
import UpcomingFightCard from './UpcomingFightCard'
import LoadingSpinner from '@components/common/LoadingSpinner'

interface Props {
  event: UpcomingEventListItem
  isOpen: boolean
  isNext: boolean
  onToggle: () => void
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

function isHighlighted(name: string | null): boolean {
  if (!name) return false
  return /^UFC \d+/.test(name) || name.toLowerCase().includes('freedom')
}

export default function UpcomingEventAccordion({ event, isOpen, isNext, onToggle }: Props) {
  const [fightCard, setFightCard] = useState<UpcomingEventWithFights | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const requestedRef = useRef(false)

  // Lazy-fetch: only load fight card on first open. The ref guard dedupes
  // rather than a state flag, so nothing is set synchronously in the effect
  // body. The cancelled flag drops a resolved response if the accordion
  // unmounts mid-flight instead of setting state on a dead component.
  useEffect(() => {
    if (!isOpen || requestedRef.current) return
    requestedRef.current = true
    let cancelled = false
    upcomingService
      .getEventWithFights(event.id)
      .then((data) => {
        if (!cancelled) setFightCard(data)
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [isOpen, event.id, attempt])

  // Clearing the guard alone would not refire the effect, since isOpen and
  // event.id are unchanged - bumping attempt is what re-triggers the fetch.
  function retry() {
    requestedRef.current = false
    setError(null)
    setAttempt((a) => a + 1)
  }

  // Derived, not stored: in flight is exactly "opened, with neither result yet".
  const loading = isOpen && fightCard === null && error === null

  const highlighted = isHighlighted(event.event_name)

  return (
    <div
      className={`overflow-hidden rounded-lg border transition-colors ${
        highlighted
          ? 'border-[var(--color-primary)]/40 bg-white dark:bg-[var(--color-surface)]'
          : 'border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)]'
      }`}
    >
      {/* Header — always visible */}
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left"
        aria-expanded={isOpen}
      >
        <div className="min-w-0 flex-1 text-center">
          {/* Badges — always on own line above event name */}
          {(isNext || highlighted) && (
            <div className="mb-1 flex justify-center gap-2">
              {isNext && (
                <span className="rounded-sm bg-[var(--color-primary)] px-2 py-0.5 text-xs font-bold uppercase tracking-wide text-white">
                  Next
                </span>
              )}
              {highlighted && (
                <span className="hidden sm:inline rounded-sm bg-[var(--color-primary)] px-1.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-white">
                  Numbered
                </span>
              )}
            </div>
          )}
          <div>
            <span
              className={`font-semibold leading-tight ${
                highlighted
                  ? 'text-[var(--color-primary)]'
                  : 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
              }`}
            >
              {event.event_name ?? 'Unnamed Event'}
            </span>
          </div>
          <div className="mt-0.5 text-xs text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
            <div className="flex min-w-0 justify-center gap-x-3">
              <span className="whitespace-nowrap">{formatDate(event.event_date)}</span>
              {event.location && <span className="truncate">{event.location}</span>}
            </div>
            <div>
              {event.fight_count} {event.fight_count === 1 ? 'bout' : 'bouts'}
            </div>
          </div>
        </div>

        {/* Chevron */}
        <svg
          className={`h-4 w-4 shrink-0 text-[var(--color-text-muted)] transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expandable fight card */}
      {isOpen && (
        <div className="px-4 pb-4">
          {loading && (
            <div className="flex justify-center py-6">
              <LoadingSpinner />
            </div>
          )}
          {error && (
            <div className="py-4 text-center">
              <p className="text-sm text-[var(--color-error-light)] dark:text-[var(--color-error)]">{error}</p>
              <button
                onClick={retry}
                className="mt-2 rounded border border-[var(--color-border)] px-3 py-2 text-xs font-semibold text-[var(--color-text-secondary-light)] transition-colors hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] dark:text-[var(--color-text-secondary)]"
              >
                Try again
              </button>
            </div>
          )}
          {fightCard && !loading && (
            fightCard.fights.length > 0 ? (
              fightCard.fights.map((fight) => (
                <UpcomingFightCard key={fight.id} fight={fight} />
              ))
            ) : (
              <p className="py-4 text-center text-sm text-[var(--color-text-muted)]">
                No bouts announced yet.
              </p>
            )
          )}
        </div>
      )}
    </div>
  )
}
