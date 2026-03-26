import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { useDebounce } from '@hooks/useDebounce'
import { fightsService } from '@services/fightsService'
import { LoadingSkeleton, Pagination } from '@components/common'
import { formatDate } from '@utils/format'
import type { FightSearchItem } from '@t/api'

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

function methodColor(method: string | null): string {
  if (!method) return 'text-[var(--color-text-muted)]'
  const m = method.toUpperCase()
  if (m.includes('KO') || m.includes('TKO')) return 'text-[var(--color-primary)]'
  if (m.includes('SUB')) return 'text-amber-500 dark:text-amber-400'
  return 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]'
}

function FightCard({ fight }: { fight: FightSearchItem }) {
  const hasPred = fight.win_prob_a !== null && fight.win_prob_b !== null
  const winnerIsA = fight.winner_id === fight.fighter_a_id
  const predWinnerIsA = fight.predicted_winner_id === fight.fighter_a_id

  return (
    <Link
      to={`/past-predictions/fights/${fight.fight_id}`}
      className="block rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4 py-3 space-y-1.5 hover:border-[var(--color-primary)]/60 transition-colors"
    >
      {/* Fighter names + winner */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold leading-snug">
            <span className={winnerIsA ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}>
              {fight.fighter_a_name ?? '—'}
            </span>
            <span className="mx-1.5 text-[var(--color-text-muted)] font-normal">vs</span>
            <span className={!winnerIsA && fight.winner_id ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : !fight.winner_id ? '' : 'text-[var(--color-text-muted)]'}>
              {fight.fighter_b_name ?? '—'}
            </span>
          </p>
        </div>
        {fight.is_title_fight && (
          <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-amber-400/20 text-amber-600 dark:text-amber-400">
            Title
          </span>
        )}
      </div>

      {/* Winner badge */}
      {fight.winner_name && (
        <p className="text-xs">
          <span className="text-[var(--color-text-muted)]">Winner: </span>
          <span className="font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
            {fight.winner_name}
          </span>
          {fight.method && (
            <span className={`ml-1.5 font-medium ${methodColor(fight.method)}`}>
              · {fight.method}
              {fight.round != null ? ` (R${fight.round})` : ''}
            </span>
          )}
        </p>
      )}

      {/* Event + date */}
      <p className="text-xs text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        {fight.event_name ?? '—'}
        {fight.event_date ? ` · ${formatDate(fight.event_date)}` : ''}
        {fight.weight_class ? ` · ${fight.weight_class}` : ''}
      </p>

      {/* Prediction badge */}
      {hasPred && (
        <div className="flex items-center gap-2 pt-0.5">
          <span className="text-[10px] uppercase tracking-wide font-semibold text-[var(--color-text-muted)]">
            Model
          </span>
          <span className="text-xs font-mono tabular-nums text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
            {fight.fighter_a_name?.split(' ').pop()} {(fight.win_prob_a! * 100).toFixed(0)}%
            <span className="mx-1 text-[var(--color-text-muted)]">/</span>
            {fight.fighter_b_name?.split(' ').pop()} {(fight.win_prob_b! * 100).toFixed(0)}%
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
            fight.predicted_winner_id === fight.winner_id
              ? 'bg-green-500/15 text-green-600 dark:text-green-400'
              : 'bg-red-500/15 text-red-600 dark:text-red-400'
          }`}>
            {fight.predicted_winner_id === fight.winner_id ? '✓' : '✗'}{' '}
            {predWinnerIsA ? fight.fighter_a_name?.split(' ').pop() : fight.fighter_b_name?.split(' ').pop()}
          </span>
        </div>
      )}
    </Link>
  )
}

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
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center text-sm text-red-600 dark:text-red-400">
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
                <FightCard key={fight.fight_id} fight={fight} />
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
