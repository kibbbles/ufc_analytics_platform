import { useState } from 'react'
import { useApi } from '@hooks/useApi'
import { useFilters } from '@hooks/useFilters'
import { eventsService } from '@services/eventsService'
import { LoadingSkeleton, Pagination } from '@components/common'
import { EventCard } from '@components/features'

const PAGE_SIZE = 10
const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: CURRENT_YEAR - 1993 }, (_, i) => CURRENT_YEAR - i)

export default function EventsPage() {
  const { filters, setYear } = useFilters()
  const [page, setPage] = useState(1)

  const { data, loading, error } = useApi(
    () =>
      eventsService.getList({ page, page_size: PAGE_SIZE, year: filters.year ?? undefined }),
    [page, filters.year],
  )

  function handleYearChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setYear(e.target.value ? Number(e.target.value) : null)
    setPage(1)
  }

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">UFC Events</h1>
          <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
            Events ordered by date — click any card to view the full fight card.
          </p>
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

      <div className="mt-6 space-y-3">
        {loading &&
          Array.from({ length: 6 }, (_, i) => (
            <div
              key={i}
              className="rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] p-5"
            >
              <LoadingSkeleton lines={2} />
            </div>
          ))}

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center text-sm text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {data && !loading && (
          <>
            {data.data.length === 0 ? (
              <div className="py-16 text-center text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
                No events found{filters.year ? ` for ${filters.year}` : ''}.
              </div>
            ) : (
              data.data.map((event) => <EventCard key={event.id} event={event} />)
            )}
            <Pagination
              page={page}
              totalPages={data.meta.total_pages}
              onPrev={() => setPage((p) => p - 1)}
              onNext={() => setPage((p) => p + 1)}
            />
          </>
        )}
      </div>
    </div>
  )
}
