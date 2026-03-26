import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { useDebounce } from '@hooks/useDebounce'
import { useFilters } from '@hooks/useFilters'
import { eventsService } from '@services/eventsService'
import { LoadingSkeleton, Pagination } from '@components/common'
import { EventCard, FightSearchTab } from '@components/features'

type Tab = 'events' | 'fights'

const PAGE_SIZE = 10
const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: CURRENT_YEAR - 1993 }, (_, i) => CURRENT_YEAR - i)

export default function EventsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get('tab')
  const activeTab: Tab = rawTab === 'fights' ? 'fights' : 'events'

  function setTab(tab: Tab) {
    setSearchParams({ tab }, { replace: true })
  }

  // ── Events tab state ───────────────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState('')
  const debouncedSearch = useDebounce(searchQuery, 300)
  const { filters, setYear } = useFilters()
  const [page, setPage] = useState(1)

  const { data: completedData, loading: completedLoading, error: completedError } = useApi(
    () =>
      eventsService.getList({
        page,
        page_size: PAGE_SIZE,
        year: filters.year ?? undefined,
        name: debouncedSearch.trim() || undefined,
      }),
    [page, filters.year, debouncedSearch],
  )

  // Reset page when debounced search fires
  useEffect(() => { setPage(1) }, [debouncedSearch])

  function handleYearChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setYear(e.target.value ? Number(e.target.value) : null)
    setPage(1)
  }

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    setSearchQuery(e.target.value)
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Fight Database</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
          All UFC events and fights in the database.
        </p>
      </div>

      {/* Tab toggle */}
      <div
        className="mb-4 flex rounded-lg border border-[var(--color-border)] bg-[var(--color-border)]/20 p-1 gap-1"
        role="tablist"
      >
        {(['events', 'fights'] as Tab[]).map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => setTab(tab)}
            className={`flex-1 rounded-md py-2.5 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-white dark:bg-[var(--color-surface)] text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)] shadow-sm'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]'
            }`}
          >
            {tab === 'events' ? 'Events' : 'Fight Search'}
          </button>
        ))}
      </div>

      {/* ── Events tab ────────────────────────────────────────────────────────── */}
      {activeTab === 'events' && (
        <div>
          {/* Search + year filter row */}
          <div className="mb-6 flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[160px]">
              <input
                type="text"
                placeholder="Search events…"
                value={searchQuery}
                onChange={handleSearchChange}
                aria-label="Filter events by name"
                className="w-full rounded-md border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              />
              {searchQuery && (
                <button
                  onClick={() => { setSearchQuery(''); setPage(1) }}
                  aria-label="Clear search"
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-lg leading-none text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]"
                >
                  ×
                </button>
              )}
            </div>

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
          </div>

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
                {completedData.data.length === 0 ? (
                  <div className="py-16 text-center text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
                    {searchQuery
                      ? 'No events match your search.'
                      : `No events found${filters.year ? ` for ${filters.year}` : ''}.`}
                  </div>
                ) : (
                  completedData.data.map((event) => <EventCard key={event.id} event={event} />)
                )}
                <Pagination
                  page={page}
                  totalPages={completedData.meta.total_pages}
                  total={completedData.meta.total}
                  pageSize={PAGE_SIZE}
                  onPrev={() => setPage((p) => p - 1)}
                  onNext={() => setPage((p) => p + 1)}
                />
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Fight Search tab ──────────────────────────────────────────────────── */}
      {activeTab === 'fights' && <FightSearchTab />}
    </div>
  )
}
