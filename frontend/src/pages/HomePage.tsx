import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { pastPredictionsService } from '@services/pastPredictionsService'
import { LoadingSkeleton, Pagination } from '@components/common'
import ScorecardModal, { type ScorecardModalMode } from '@components/features/ScorecardModal'
import { formatDate } from '@utils/format'
import type { PastPredictionItem } from '@t/api'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPct(v: number): string {
  return (v * 100).toFixed(1) + '%'
}

function winnerName(item: PastPredictionItem, id: string | null | undefined): string {
  if (!id) return '—'
  if (id === item.fighter_a_id) return item.fighter_a_name ?? '—'
  if (id === item.fighter_b_id) return item.fighter_b_name ?? '—'
  return '—'
}

const PAGE_SIZE = 10

// ---------------------------------------------------------------------------
// Fight search result row
// ---------------------------------------------------------------------------

function FightSearchRow({ item }: { item: PastPredictionItem }) {
  const isUpset   = item.is_upset
  const isCorrect = item.is_correct

  let indicator: string
  let color: string
  if (isUpset)        { indicator = '~'; color = 'text-amber-500' }
  else if (isCorrect) { indicator = '✓'; color = 'text-green-500' }
  else                { indicator = '✗'; color = 'text-[var(--color-primary)]' }

  const predWinner   = winnerName(item, item.predicted_winner_id)
  const actualWinner = winnerName(item, item.actual_winner_id)

  return (
    <Link
      to={`/past-predictions/fights/${item.fight_id}`}
      className="block rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4 py-3 hover:border-[var(--color-primary)]/50 transition-colors lg:text-center"
    >
      {/* Matchup header */}
      <div className="flex items-start gap-2 mb-1.5 lg:justify-center">
        <span className={`font-mono font-bold text-sm mt-0.5 w-4 shrink-0 ${color}`}>{indicator}</span>
        <div className="min-w-0 flex-1 lg:flex-none">
          <p className="text-sm font-semibold leading-tight truncate">
            {item.fighter_a_name ?? '?'} vs {item.fighter_b_name ?? '?'}
          </p>
          <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] truncate">
            {item.event_name ?? '—'}
            {item.event_date ? ` · ${formatDate(item.event_date)}` : ''}
            {item.weight_class ? ` · ${item.weight_class}` : ''}
          </p>
        </div>
      </div>
      {/* Prediction vs actual */}
      <div className="ml-6 space-y-0.5 lg:ml-0">
        <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          <span className="w-16 inline-block">Predicted</span>
          <span className={isCorrect ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : ''}>
            {predWinner}
          </span>
          {item.predicted_method && <span> via {item.predicted_method}</span>}
        </p>
        <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          <span className="w-16 inline-block">Actual</span>
          <span className="text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
            {actualWinner}
          </span>
          {item.actual_method && <span> via {item.actual_method}</span>}
        </p>
        {item.confidence != null && (
          <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            <span className="w-16 inline-block">Conviction</span>
            <span className="font-mono font-semibold tabular-nums">{formatPct(item.confidence)}</span>
          </p>
        )}
      </div>
    </Link>
  )
}

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
        <p className="text-sm text-red-500">Failed to load scorecard: {summaryError}</p>
      ) : summary && summary.total_fights > 0 ? (
        <div className="mb-4">
          <div className="grid grid-cols-2 gap-3 mb-3">
            {/* Live track record — the model's real predictions, frozen pre-event */}
            {summary.pre_fight_total > 0 ? (
              <button
                onClick={() => setModal('pre_fight')}
                className="rounded-lg border border-[var(--color-primary)]/40 px-4 py-3 text-left w-full hover:border-[var(--color-primary)]/70 transition-colors"
              >
                <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] mb-1.5">
                  Live track record
                </p>
                <p className="font-mono text-xl font-bold tabular-nums text-[var(--color-primary)]">
                  {formatPct(summary.pre_fight_accuracy)}
                </p>
                <p className="mt-0.5 text-xs font-mono tabular-nums text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                  {summary.pre_fight_correct}/{summary.pre_fight_total} fights
                </p>
                <p className="mt-0.5 text-xs font-mono tabular-nums text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                  avg conviction {formatPct(summary.pre_fight_avg_confidence)}
                </p>
                <p className="mt-2 text-xs italic text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                  Frozen before each event · no look-ahead
                </p>
              </button>
            ) : (
              <div className="rounded-lg border border-dashed border-[var(--color-border-light)] dark:border-[var(--color-border)] px-4 py-3 flex items-center justify-center">
                <p className="text-xs text-center text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                  Live track record<br />accumulates over time
                </p>
              </div>
            )}

            {/* Backtested — current model reconstructed over past fights */}
            <button
              onClick={() => setModal('backtest')}
              className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] px-4 py-3 text-left w-full hover:border-[var(--color-primary)]/50 transition-colors"
            >
              <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] mb-1.5">
                Backtested
              </p>
              <p className="font-mono text-xl font-bold tabular-nums">
                {formatPct(summary.backtest_accuracy)}
              </p>
              <p className="mt-0.5 text-xs font-mono tabular-nums text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                {summary.backtest_correct}/{summary.backtest_total} fights
              </p>
              {summary.backtest_avg_confidence > 0 && (
                <p className="mt-0.5 text-xs font-mono tabular-nums text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                  avg conviction {formatPct(summary.backtest_avg_confidence)}
                </p>
              )}
              <p className="mt-2 text-xs italic text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                Corrected model · reconstructed
              </p>
            </button>
          </div>
          {/* Versus what baseline — the first question anyone asks; not buried */}
          {summary.baseline_sample > 0 && (
            <div className="mb-3 rounded-lg border border-[var(--color-primary)]/30 bg-[var(--color-primary)]/5 px-4 py-3">
              <p className="text-xs uppercase tracking-wide font-semibold text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] mb-2">
                Versus what baseline?
              </p>
              <div className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 text-xs mb-2">
                <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                  Always pick the Vegas favorite
                </span>
                <span className="text-right font-mono tabular-nums font-semibold">
                  {formatPct(summary.baseline_vegas_accuracy)}
                </span>
                <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                  Model, same {summary.baseline_sample} fights
                </span>
                <span className="text-right font-mono tabular-nums font-semibold">
                  {formatPct(summary.baseline_model_accuracy)}
                </span>
              </div>
              <p className="text-xs text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
                On the {summary.baseline_sample} live fights with betting odds, the model did not beat
                always picking the Vegas favorite. Its only potential edge is where it{' '}
                <span className="font-semibold">disagrees</span> with the market —{' '}
                {summary.baseline_disagree_count} fights — and there it was right just{' '}
                <span className="font-semibold text-[var(--color-primary)]">
                  {summary.baseline_disagree_accuracy != null ? formatPct(summary.baseline_disagree_accuracy) : '—'}
                </span>{' '}
                of the time. When this model departs from Vegas, it has mostly been wrong.
              </p>
            </div>
          )}
          {summary.pre_fight_total > 0 && (
            <p className="mb-3 rounded-lg border border-[var(--color-primary)]/30 bg-[var(--color-primary)]/5 px-4 py-3 text-xs font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
              The live record, made with the now-fixed feature bug, was overconfident above 60%. The corrected model is well-calibrated on held-out test data (ECE 3.65%), but has no live track record yet.{' '}
              <button
                onClick={() => setModal('pre_fight')}
                className="underline decoration-dotted underline-offset-2 hover:text-[var(--color-primary)]"
              >
                See calibration
              </button>.
            </p>
          )}
          <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            {summary.model_name ? `${summary.model_name} model` : 'A model'} using 30 features including physical differentials, career striking and grappling metrics, and recent fight history. It is pinned, chosen for best calibration from logistic regression, random forest, and gradient boosting rather than re-selected each retrain, which only added noise among three statistically tied models.{' '}
            <span className="font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">Live track record</span> is the model's real predictions, frozen the Saturday before each event and never rewritten: the honest number, with no look-ahead.{' '}
            <span className="font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">Backtested</span> is the current model reconstructed over past fights; it benefits from hindsight in the code (features rebuilt after the fact), so it is not a live record.{' '}
            Every one of these {summary.pre_fight_total} live predictions was made with a corrupted win/loss streak feature and with win_rate_diff silently imputed to the population mean; both were fixed in July 2026. The corrected model has no live track record yet and cannot be claimed to be better until it accumulates one.
          </p>
          <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            Conviction measures how far the model's prediction is from a coin flip, scaled to 0–100%. A 60/40 prediction = 20% conviction, a 75/25 pick = 50% conviction, an 85/15 pick = 70% conviction. It is not a statistical confidence interval — it reflects how decisive the model is on a given matchup based on the feature differentials going in.
          </p>
        </div>
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
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-400">
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
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-400">
            Failed to search: {fightsError}
          </div>
        ) : fightsData && fightsData.data.length > 0 ? (
          <>
            <div className="space-y-2">
              {fightsData.data.map((fight) => (
                <FightSearchRow key={fight.fight_id} item={fight} />
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
          Fight results and stats scraped every Sunday at 9 AM EST · Upcoming predictions refreshed every Saturday at 10 AM EST
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
