import { useState, useEffect } from 'react'
import { useApi } from '@hooks/useApi'
import { useDebounce } from '@hooks/useDebounce'
import { fightsService } from '@services/fightsService'
import { LoadingSkeleton, Pagination } from '@components/common'
import FightSearchCard from './FightSearchCard'

const WEIGHT_CLASSES = [
  'Strawweight',
  'Flyweight',
  'Bantamweight',
  'Featherweight',
  'Lightweight',
  'Welterweight',
  'Middleweight',
  'Light Heavyweight',
  'Heavyweight',
  "Women's Strawweight",
  "Women's Flyweight",
  "Women's Bantamweight",
  "Women's Featherweight",
]

const METHODS = ['KO/TKO', 'Submission', 'Decision', 'No Contest', 'DQ']

const PAGE_SIZE = 25

export default function FightSearchTab() {
  const [fighterQuery, setFighterQuery] = useState('')
  const [weightClass, setWeightClass] = useState('')
  const [method, setMethod] = useState('')
  const [page, setPage] = useState(1)

  const debouncedFighter = useDebounce(fighterQuery, 300)

  // Reset page on any filter change
  useEffect(() => { setPage(1) }, [debouncedFighter, weightClass, method])

  const { data, loading, error } = useApi(
    () =>
      fightsService.search({
        fighter_name: debouncedFighter.trim() || undefined,
        weight_class: weightClass || undefined,
        method: method || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    [debouncedFighter, weightClass, method, page],
  )

  const selectClass =
    'rounded-md border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]'

  return (
    <div>
      {/* Filters */}
      <div className="mb-6 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[160px]">
          <input
            type="text"
            placeholder="Search by fighter name…"
            value={fighterQuery}
            onChange={(e) => setFighterQuery(e.target.value)}
            aria-label="Search by fighter name"
            className="w-full rounded-md border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          />
          {fighterQuery && (
            <button
              onClick={() => setFighterQuery('')}
              aria-label="Clear search"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-lg leading-none text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]"
            >
              ×
            </button>
          )}
        </div>

        <select
          value={weightClass}
          onChange={(e) => setWeightClass(e.target.value)}
          aria-label="Filter by weight class"
          className={selectClass}
        >
          <option value="">All weight classes</option>
          {WEIGHT_CLASSES.map((wc) => (
            <option key={wc} value={wc}>{wc}</option>
          ))}
        </select>

        <select
          value={method}
          onChange={(e) => setMethod(e.target.value)}
          aria-label="Filter by method"
          className={selectClass}
        >
          <option value="">All methods</option>
          {METHODS.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      {/* Results count */}
      {data && !loading && data.meta.total > 0 && (
        <p className="mb-3 text-xs text-[var(--color-text-muted)]">
          {data.meta.total.toLocaleString()} fight{data.meta.total !== 1 ? 's' : ''}
          {debouncedFighter || weightClass || method ? ' matching filters' : ' in database'}
        </p>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] p-4">
              <LoadingSkeleton lines={3} />
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error)]/10 p-6 text-center text-sm text-[var(--color-error-light)] dark:text-[var(--color-error)]">
          {error}
        </div>
      )}

      {/* Results */}
      {data && !loading && (
        <>
          {data.data.length === 0 ? (
            <div className="py-16 text-center text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
              No fights found. Try a different search.
            </div>
          ) : (
            <div className="space-y-3">
              {data.data.map((fight) => (
                <FightSearchCard key={fight.fight_id} fight={fight} />
              ))}
            </div>
          )}

          <Pagination
            page={page}
            totalPages={data.meta.total_pages}
            total={data.meta.total}
            pageSize={PAGE_SIZE}
            onPrev={() => setPage((p) => p - 1)}
            onNext={() => setPage((p) => p + 1)}
          />
        </>
      )}
    </div>
  )
}
