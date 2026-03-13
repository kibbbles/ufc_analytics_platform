import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { pastPredictionsService } from '@services/pastPredictionsService'
import { LoadingSkeleton, Pagination } from '@components/common'
import { formatDate } from '@utils/format'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPct(value: number): string {
  return (value * 100).toFixed(1) + '%'
}

const PAGE_SIZE = 10
const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: CURRENT_YEAR - 2021 }, (_, i) => CURRENT_YEAR - i)

// ---------------------------------------------------------------------------
// Model Scorecard section
// ---------------------------------------------------------------------------

function ModelScorecard() {
  const [page, setPage]         = useState(1)
  const [search, setSearch]     = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [year, setYear]         = useState<number | undefined>(undefined)

  // Summary stats (fetched once)
  const { data: summaryData, loading: summaryLoading } = useApi(
    () => pastPredictionsService.get(1),
    [],
  )

  // Event list (paginated, filtered)
  const { data: eventsData, loading: eventsLoading } = useApi(
    () =>
      pastPredictionsService.getEvents({
        page,
        page_size: PAGE_SIZE,
        search: debouncedSearch || undefined,
        year,
      }),
    [page, debouncedSearch, year],
  )

  const summary = summaryData?.summary

  // Derive date range label
  let dateLabel = 'Test set'
  if (summary?.date_from) {
    const fromDate = new Date(summary.date_from + 'T00:00:00')
    const fromStr  = fromDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
    dateLabel = `Test set · ${fromStr} – present`
  }

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value
    setSearch(val)
    setPage(1)
    // Simple debounce via timeout
    clearTimeout((handleSearchChange as unknown as { _t?: ReturnType<typeof setTimeout> })._t)
    const t = setTimeout(() => setDebouncedSearch(val), 300)
    ;(handleSearchChange as unknown as { _t?: ReturnType<typeof setTimeout> })._t = t
  }

  function handleYearChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setYear(e.target.value ? Number(e.target.value) : undefined)
    setPage(1)
  }

  return (
    <section>
      {/* Section header */}
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-xl font-bold">Model Scorecard</h2>
        <span className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          {dateLabel}
        </span>
      </div>

      {/* Summary stats — compact single-line */}
      {summaryLoading ? (
        <LoadingSkeleton lines={2} />
      ) : summary && summary.total_fights > 0 ? (
        <div className="mb-1">
          <p className="text-sm font-mono tabular-nums">
            <span className="font-semibold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
              {formatPct(summary.accuracy)} accurate
            </span>
            <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              {' · '}{summary.correct}/{summary.total_fights} fights
            </span>
            {summary.high_conf_fights > 0 && (
              <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                {' '}({formatPct(summary.high_conf_accuracy)} when ≥65% confident)
              </span>
            )}
          </p>
          <p className="mt-1.5 text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            Random Forest ensemble using 30 features including physical differentials, career striking and grappling metrics, and recent fight history.
          </p>
        </div>
      ) : (
        <p className="mb-5 text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          No predictions yet.
        </p>
      )}

      {/* Search + year filter */}
      <div className="mt-4 mb-3 flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-[160px]">
          <input
            type="text"
            placeholder="Search events…"
            value={search}
            onChange={handleSearchChange}
            aria-label="Filter scorecard events"
            className="w-full rounded-md border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          />
          {search && (
            <button
              onClick={() => { setSearch(''); setDebouncedSearch(''); setPage(1) }}
              aria-label="Clear search"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-lg leading-none text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]"
            >
              ×
            </button>
          )}
        </div>
        <select
          value={year ?? ''}
          onChange={handleYearChange}
          aria-label="Filter by year"
          className="rounded-md border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
        >
          <option value="">All years</option>
          {YEARS.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* Event list */}
      {eventsLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] p-4">
              <LoadingSkeleton lines={2} />
            </div>
          ))}
        </div>
      ) : eventsData && eventsData.data.length > 0 ? (
        <>
          <div className="space-y-2">
            {eventsData.data.map((event) => (
              <Link
                key={event.event_id}
                to={`/past-predictions/events/${event.event_id}`}
                className="flex items-center justify-between gap-3 rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4 py-3 hover:border-[var(--color-primary)]/50 transition-colors"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium leading-tight truncate">
                    {event.event_name ?? 'Unknown Event'}
                  </p>
                  <p className="mt-0.5 text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                    {event.event_date ? formatDate(event.event_date) : '—'}
                    {' · '}{event.fight_count} {event.fight_count === 1 ? 'bout' : 'bouts'}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <span className="font-mono text-sm tabular-nums font-semibold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
                    {formatPct(event.accuracy)}
                  </span>
                  <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                    {event.correct_count}/{event.fight_count}
                  </p>
                </div>
              </Link>
            ))}
          </div>

          {!debouncedSearch && !year && (
            <Pagination
              page={page}
              totalPages={eventsData.total_pages}
              onPrev={() => setPage((p) => p - 1)}
              onNext={() => setPage((p) => p + 1)}
            />
          )}
        </>
      ) : (
        <p className="py-8 text-center text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          {debouncedSearch || year ? 'No events match your search.' : 'No past predictions yet.'}
        </p>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function HomePage() {
  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-3xl font-bold">UFC Analytics</h1>
        <p className="mt-2 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
          ML-powered fight predictions and historical analysis
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { title: 'Upcoming Card', desc: "Pre-computed predictions for this Saturday's event", to: '/upcoming' },
          { title: 'Completed Events', desc: 'Browse historical UFC events and full fight cards', to: '/events' },
          { title: 'Fight Predictor', desc: 'Win probability + method breakdown for any matchup', to: '/predictions' },
          { title: 'Fighter Lookup', desc: 'Search any fighter — record, stats, fight history', to: '/fighters' },
        ].map((card) => (
          <Link
            key={card.to}
            to={card.to}
            className="block p-5 rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-surface-light)] dark:bg-[var(--color-surface)] hover:border-[var(--color-primary)] transition-colors"
          >
            <h2 className="font-semibold">{card.title}</h2>
            <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
              {card.desc}
            </p>
          </Link>
        ))}
      </div>

      <ModelScorecard />
    </div>
  )
}
