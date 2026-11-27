import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { useClampPage } from '@hooks/useClampPage'
import { pastPredictionsService } from '@services/pastPredictionsService'
import { LoadingSkeleton, Pagination } from '@components/common'
import ScorecardModal, { type ScorecardModalMode } from '@components/features/ScorecardModal'
import PastPredictionCard from '@components/features/PastPredictionCard'
import ScorecardSummary from '@components/features/ScorecardSummary'
import { formatDate } from '@utils/format'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPct(v: number): string {
  return (v * 100).toFixed(1) + '%'
}

const PAGE_SIZE = 10

// ---------------------------------------------------------------------------
// Model Scorecard section
// ---------------------------------------------------------------------------

type ScorecardTab = 'events' | 'fights'

function ModelScorecard() {
  const [modal, setModal]           = useState<ScorecardModalMode | null>(null)
  const [tab, setTab]               = useState<ScorecardTab>('events')
  const [page, setPage]             = useState(1)
  const [search, setSearch]         = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [year, setYear]             = useState<number | undefined>(undefined)
  const debounceTimer               = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Summary (fetched once; includes available_years)
  const { data: summaryData, loading: summaryLoading, error: summaryError } = useApi(
    () => pastPredictionsService.get(1),
    [],
  )

  // Events tab
  const { data: eventsData, loading: eventsLoading, error: eventsError } = useApi(
    () =>
      tab === 'events'
        ? pastPredictionsService.getEvents({
            page,
            page_size: PAGE_SIZE,
            search: debouncedSearch || undefined,
            year,
          })
        : Promise.resolve(null),
    [tab, page, debouncedSearch, year],
  )

  // A page past the end of the events list (fewer pages after a reload) goes to the last page.
  useClampPage(page, tab === 'events' ? (eventsData?.total_pages ?? 0) : 0, setPage)

  // Fights tab — show most recent by default, filter by search/year when provided
  const { data: fightsData, loading: fightsLoading, error: fightsError } = useApi(
    () =>
      tab === 'fights'
        ? pastPredictionsService.searchFights({
            search: debouncedSearch || undefined,
            year,
            page,
            page_size: PAGE_SIZE,
          })
        : Promise.resolve(null),
    [tab, page, debouncedSearch, year],
  )

  const summary    = summaryData?.summary
  const availYears = summary?.available_years ?? []

  let dateLabel = 'Test set'
  if (summary?.date_from) {
    const fromDate = new Date(summary.date_from + 'T00:00:00')
    const fromStr  = fromDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
    dateLabel = `Test set · ${fromStr} – present`
  }

  function handleTabChange(t: ScorecardTab) {
    setTab(t)
    setSearch('')
    setDebouncedSearch('')
    setPage(1)
    setYear(undefined)
  }

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value
    setSearch(val)
    setPage(1)
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => setDebouncedSearch(val), 300)
  }

  function clearSearch() {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    setSearch('')
    setDebouncedSearch('')
    setPage(1)
  }

  function handleYearChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setYear(e.target.value ? Number(e.target.value) : undefined)
    setPage(1)
  }

  useEffect(() => {
    return () => { if (debounceTimer.current) clearTimeout(debounceTimer.current) }
  }, [])

  return (
    <section>
      {/* Header */}
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-xl font-bold">Model Scorecard</h2>
        <span className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          {dateLabel}
        </span>
      </div>

      {/* Summary stats */}
      {summaryLoading ? (
        <LoadingSkeleton lines={2} />
      ) : summaryError ? (
        <p className="text-sm text-[var(--color-error-light)] dark:text-[var(--color-error)]">Failed to load scorecard: {summaryError}</p>
      ) : summary && summary.total_fights > 0 ? (
        <ScorecardSummary summary={summary} onOpen={setModal} />
      ) : null}

      {/* Events | Fights tab toggle */}
      <div
        className="mb-3 flex rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-border)]/20 p-1 gap-1"
        role="tablist"
      >
        {(['events', 'fights'] as ScorecardTab[]).map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => handleTabChange(t)}
            className={`flex-1 rounded-md py-2 text-sm font-medium capitalize transition-colors ${
              tab === t
                ? 'bg-white dark:bg-[var(--color-surface)] text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)] shadow-sm'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]'
            }`}
          >
            {t === 'events' ? 'Events' : 'Fight Search'}
          </button>
        ))}
      </div>

      {/* Search + filters */}
      <div className="mb-3 flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-[160px]">
          <input
            type="text"
            placeholder={tab === 'events' ? 'Search events…' : 'Search fighter name…'}
            value={search}
            onChange={handleSearchChange}
            aria-label={tab === 'events' ? 'Filter scorecard events' : 'Search by fighter name'}
            className="w-full rounded-md border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          />
          {search && (
            <button
              onClick={clearSearch}
              aria-label="Clear search"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-lg leading-none text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]"
            >
              ×
            </button>
          )}
        </div>
        {availYears.length > 0 && (
          <select
            value={year ?? ''}
            onChange={handleYearChange}
            aria-label="Filter by year"
            className="rounded-md border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          >
            <option value="">All years</option>
            {availYears.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        )}
      </div>

      {/* ── Events tab ─────────────────────────────────────────────────────── */}
      {tab === 'events' && (
        eventsLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] p-4">
                <LoadingSkeleton lines={2} />
              </div>
            ))}
          </div>
        ) : eventsError ? (
          <div className="rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error)]/10 p-4 text-sm text-[var(--color-error-light)] dark:text-[var(--color-error)]">
            Failed to load events: {eventsError}
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
                    <span className="font-mono text-sm tabular-nums font-semibold">
                      {formatPct(event.accuracy)}
                    </span>
                    <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                      {event.correct_count}/{event.fight_count}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
            <Pagination
              page={page}
              totalPages={eventsData.total_pages}
              onPrev={() => setPage((p) => p - 1)}
              onNext={() => setPage((p) => p + 1)}
              onPageChange={setPage}
            />
          </>
        ) : (
          <p className="py-8 text-center text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            {debouncedSearch || year ? 'No events match your filter.' : 'No past predictions yet.'}
          </p>
        )
      )}

      {/* ── Fights tab ─────────────────────────────────────────────────────── */}
      {tab === 'fights' && (
        fightsLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }, (_, i) => (
              <div key={i} className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] p-4">
                <LoadingSkeleton lines={2} />
              </div>
            ))}
          </div>
        ) : fightsError ? (
          <div className="rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error)]/10 p-4 text-sm text-[var(--color-error-light)] dark:text-[var(--color-error)]">
            Failed to search: {fightsError}
          </div>
        ) : fightsData && fightsData.data.length > 0 ? (
          <>
            <div className="space-y-2">
              {fightsData.data.map((fight) => (
                <PastPredictionCard key={fight.fight_id} variant="search" item={fight} />
              ))}
            </div>
            <Pagination
              page={page}
              totalPages={fightsData.total_pages}
              onPrev={() => setPage((p) => p - 1)}
              onNext={() => setPage((p) => p + 1)}
            />
          </>
        ) : (
          <p className="py-8 text-center text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            {debouncedSearch || year ? `No fights found matching your filter.` : 'No past predictions yet.'}
          </p>
        )
      )}

      {/* Scorecard detail modal */}
      {modal && <ScorecardModal mode={modal} onClose={() => setModal(null)} />}
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
        <p className="mt-1 text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          Fight results and stats scraped every Sunday · Upcoming predictions refreshed after the Sunday retrain and again on Friday and Saturday, then frozen once a fight starts
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { title: 'Upcoming Card', desc: "Pre-computed predictions for this Saturday's event", to: '/upcoming' },
          { title: 'Fight Database', desc: 'Browse all UFC events, fight cards, and individual fight matchups', to: '/events' },
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
