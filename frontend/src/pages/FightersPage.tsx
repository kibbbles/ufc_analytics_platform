import { useEffect } from 'react'
import { useApi } from '@hooks/useApi'
import { useDebounce } from '@hooks/useDebounce'
import { useListParams } from '@hooks/useListParams'
import { fightersService } from '@services/fightersService'
import { LoadingSkeleton, Pagination } from '@components/common'
import { FighterCard, FighterSearchBar } from '@components/features'

const PAGE_SIZE = 20

export default function FightersPage() {
  // Page and search live in the URL (?page=, ?q=) so Back from a fighter
  // returns to the same page of the same search.
  const { page, query, setPage, setQuery } = useListParams()
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

  // A ?page= past the end (an old link, or a search with fewer pages) goes to the last page.
  const totalPages = data?.meta.total_pages ?? 0
  useEffect(() => {
    if (totalPages > 0 && page > totalPages) setPage(totalPages, { replace: true })
  }, [page, totalPages, setPage])

  const totalLabel = data?.meta.total.toLocaleString() ?? '4,449'

  return (
    <div>
      <h1 className="text-2xl font-bold">Fighter Lookup</h1>
      <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        Search {totalLabel} UFC fighters by name.
      </p>

      <div className="mt-6">
        <FighterSearchBar value={query} onChange={setQuery} />
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
          <div className="rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error)]/10 p-6 text-center text-sm text-[var(--color-error-light)] dark:text-[var(--color-error)]">
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
              onPrev={() => setPage(page - 1)}
              onNext={() => setPage(page + 1)}
              onPageChange={setPage}
            />
          </>
        )}
      </div>
    </div>
  )
}
