import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { useFilters } from '@hooks/useFilters'
import { eventsService } from '@services/eventsService'
import { upcomingService } from '@services/upcomingService'
import { LoadingSkeleton, Pagination } from '@components/common'
import { EventCard } from '@components/features'
import type { UpcomingEventListItem } from '@t/api'
import { formatDate } from '@utils/format'

type Tab = 'completed' | 'upcoming'

const PAGE_SIZE = 10
const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: CURRENT_YEAR - 1993 }, (_, i) => CURRENT_YEAR - i)

export default function EventsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('completed')
  const [searchQuery, setSearchQuery] = useState('')

  // Completed events (paginated, server-side year filter)
  const { filters, setYear } = useFilters()
  const [page, setPage] = useState(1)
  const { data: completedData, loading: completedLoading, error: completedError } = useApi(
    () =>
      eventsService.getList({ page, page_size: PAGE_SIZE, year: filters.year ?? undefined }),
    [page, filters.year],
  )

  // Upcoming events — fetched once on first switch to Upcoming tab, cached
  const [upcomingEvents, setUpcomingEvents] = useState<UpcomingEventListItem[] | null>(null)
  const [upcomingLoading, setUpcomingLoading] = useState(false)
  const [upcomingError, setUpcomingError] = useState<string | null>(null)

  useEffect(() => {
    if (activeTab !== 'upcoming' || upcomingEvents !== null) return
    setUpcomingLoading(true)
    upcomingService
      .getEvents()
      .then((res) => {
        setUpcomingEvents(res.data)
        setUpcomingLoading(false)
      })
      .catch((err: Error) => {
        setUpcomingError(err.message)
        setUpcomingLoading(false)
      })
  }, [activeTab, upcomingEvents])

  function handleTabSwitch(tab: Tab) {
    setActiveTab(tab)
    setSearchQuery('')
  }

  function handleYearChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setYear(e.target.value ? Number(e.target.value) : null)
    setPage(1)
  }

  // Client-side filtering
  const q = searchQuery.toLowerCase().trim()
  const filteredCompleted = completedData
    ? completedData.data.filter((e) => (e.name ?? '').toLowerCase().includes(q))
    : []
  const filteredUpcoming = (upcomingEvents ?? []).filter((e) =>
    (e.event_name ?? '').toLowerCase().includes(q),
  )

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">UFC Events</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
          Browse completed and upcoming UFC events.
        </p>
      </div>

      {/* Tab toggle */}
      <div
        className="mb-4 flex rounded-lg border border-[var(--color-border)] bg-[var(--color-border)]/20 p-1 gap-1"
        role="tablist"
      >
        {(['completed', 'upcoming'] as Tab[]).map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => handleTabSwitch(tab)}
            className={`flex-1 rounded-md py-2.5 text-sm font-medium capitalize transition-colors ${
              activeTab === tab
                ? 'bg-white dark:bg-[var(--color-surface)] text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)] shadow-sm'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Search + year filter row */}
      <div className="mb-6 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[160px]">
          <input
            type="text"
            placeholder="Search events…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Filter events by name"
            className="w-full rounded-md border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              aria-label="Clear search"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-lg leading-none text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]"
            >
              ×
            </button>
          )}
        </div>

        {activeTab === 'completed' && (
          <select
            value={filters.year ?? ''}
            onChange={handleYearChange}
            aria-label="Filter by year"
            className="rounded-md border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          >
            <option value="">All years</option>
            {YEARS.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* ── Completed tab ─────────────────────────────────────────────────────── */}
      {activeTab === 'completed' && (
        <div className="space-y-3">
          {completedLoading &&
            Array.from({ length: 6 }, (_, i) => (
              <div
                key={i}
                className="rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] p-5"
              >
                <LoadingSkeleton lines={2} />
              </div>
            ))}

          {completedError && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center text-sm text-red-600 dark:text-red-400">
              {completedError}
            </div>
          )}

          {completedData && !completedLoading && (
            <>
              {filteredCompleted.length === 0 ? (
                <div className="py-16 text-center text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
                  {searchQuery
                    ? 'No events match your search.'
                    : `No events found${filters.year ? ` for ${filters.year}` : ''}.`}
                </div>
              ) : (
                filteredCompleted.map((event) => <EventCard key={event.id} event={event} />)
              )}
              {/* Only show pagination when not actively searching */}
              {!searchQuery && (
                <Pagination
                  page={page}
                  totalPages={completedData.meta.total_pages}
                  onPrev={() => setPage((p) => p - 1)}
                  onNext={() => setPage((p) => p + 1)}
                />
              )}
            </>
          )}
        </div>
      )}

      {/* ── Upcoming tab ──────────────────────────────────────────────────────── */}
      {activeTab === 'upcoming' && (
        <div className="space-y-3">
          {upcomingLoading &&
            Array.from({ length: 4 }, (_, i) => (
              <div
                key={i}
                className="rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] p-5"
              >
                <LoadingSkeleton lines={2} />
              </div>
            ))}

          {upcomingError && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center text-sm text-red-600 dark:text-red-400">
              Failed to load upcoming events.
            </div>
          )}

          {!upcomingLoading && !upcomingError && upcomingEvents !== null && (
            <>
              {filteredUpcoming.length === 0 ? (
                <div className="py-16 text-center text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
                  {searchQuery ? 'No events match your search.' : 'No upcoming events found.'}
                </div>
              ) : (
                filteredUpcoming.map((event) => (
                  <Link
                    key={event.id}
                    to="/upcoming"
                    className="block rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] p-4 hover:border-[var(--color-primary)]/40 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-semibold leading-tight truncate">
                          {event.event_name ?? 'Unnamed Event'}
                        </p>
                        <p className="mt-0.5 text-xs text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
                          {event.event_date ? formatDate(event.event_date) : '—'}
                          {event.location ? ` · ${event.location}` : ''}
                        </p>
                      </div>
                      <span className="shrink-0 text-xs text-[var(--color-text-muted)]">
                        {event.fight_count} {event.fight_count === 1 ? 'bout' : 'bouts'}
                      </span>
                    </div>
                  </Link>
                ))
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
