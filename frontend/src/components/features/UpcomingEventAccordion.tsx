import { useState, useEffect } from 'react'
import { upcomingService } from '@services/upcomingService'
import type { UpcomingEventListItem, UpcomingEventWithFights } from '@t/api'
import UpcomingFightRow from './UpcomingFightRow'
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
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Lazy-fetch: only load fight card on first open
  useEffect(() => {
    if (!isOpen || fightCard !== null) return
    setLoading(true)
    upcomingService
      .getEventWithFights(event.id)
      .then((data) => {
        setFightCard(data)
        setLoading(false)
      })
      .catch((err: Error) => {
        setError(err.message)
        setLoading(false)
      })
  }, [isOpen, event.id, fightCard])

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
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {/* NEXT badge */}
            {isNext && (
              <span className="rounded-sm bg-[var(--color-primary)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                Next
              </span>
            )}
            {highlighted && (
              <span className="rounded-sm bg-[var(--color-primary)] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                Numbered
              </span>
            )}
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
            <div className="flex gap-x-3">
              <span>{formatDate(event.event_date)}</span>
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
            <p className="py-4 text-center text-sm text-red-500">{error}</p>
          )}
          {fightCard && !loading && (
            fightCard.fights.length > 0 ? (
              fightCard.fights.map((fight) => (
                <UpcomingFightRow key={fight.id} fight={fight} />
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
