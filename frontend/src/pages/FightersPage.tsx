import { useState } from 'react'
import { useApi } from '@hooks/useApi'
import { useDebounce } from '@hooks/useDebounce'
import { fightersService } from '@services/fightersService'
import { LoadingSkeleton, Pagination } from '@components/common'
import { FighterCard, FighterSearchBar } from '@components/features'

const PAGE_SIZE = 20

export default function FightersPage() {
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const debouncedQuery = useDebounce(query, 300)

  const { data, loading, error } = useApi(
    () =>
      fightersService.getList({
        search: debouncedQuery || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    [debouncedQuery, page],
  )

  function handleSearch(value: string) {
    setQuery(value)
    setPage(1)
  }

  const totalLabel = data?.meta.total.toLocaleString() ?? '4,449'

  return (
    <div>
      <h1 className="text-2xl font-bold">Fighter Lookup</h1>
      <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        Search {totalLabel} UFC fighters by name.
      </p>

      <div className="mt-6">
        <FighterSearchBar value={query} onChange={handleSearch} />
      </div>

      <div className="mt-4 space-y-2">
        {loading &&
          Array.from({ length: 8 }, (_, i) => (
            <div
              key={i}
              className="rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4 py-3"
            >
              <LoadingSkeleton lines={1} />
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
              <div className="py-12 text-center text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
                {debouncedQuery
                  ? `No fighters found for "${debouncedQuery}".`
                  : 'No fighters found.'}
              </div>
            ) : (
              data.data.map((fighter) => <FighterCard key={fighter.id} fighter={fighter} />)
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
