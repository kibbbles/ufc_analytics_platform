import { useState, useEffect, useLayoutEffect, useMemo, useCallback, useRef } from 'react'
import {
  ComposedChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts'
import { analyticsService } from '@services/analyticsService'
import type { BettingFightRow } from '@t/api'
import { DualRangeSlider } from './DualRangeSlider'
import Pagination from '@components/common/Pagination'
import BettingFightCard from './BettingFightCard'
import StrategyResult from './StrategyResult'
import { formatEventDate } from '@utils/format'
import { plOf, N_CONCLUSIVE, type PlSource } from '@utils/strategyStats'
import { useComparisonCounter } from '@hooks/useComparisonCounter'
import { useDebounce } from '@hooks/useDebounce'

// ── Types ────────────────────────────────────────────────────────────────────

type Range = '1M' | '3M' | '6M' | 'YTD' | 'ALL'

interface Preset {
  conv: [number, number]
  edge: [number, number]
  plSource: PlSource
  desc: string
  ageDiffMin?: number   // younger-fighter strategies: minimum age gap in years
}

const PRESETS: Record<string, Preset> = {
  model_pick:      { conv: [0, 45], edge: [0, 30], plSource: 'model', desc: 'Bet on the model\'s pick every fight. No edge or conviction filter.' },
  model_edge_5_15: { conv: [0, 45], edge: [5, 15], plSource: 'model', desc: 'Bet only when the model is 5–15pp more confident than Vegas. Signal zone.' },
  high_conv_20:    { conv: [20, 45], edge: [0, 30], plSource: 'model', desc: 'Bet only when model win probability ≥70% (conviction ≥20pp).' },
  edge_conv:       { conv: [20, 45], edge: [5, 15], plSource: 'model', desc: 'Strictest filter: 5–15pp edge AND conviction ≥20pp. Smallest sample.' },
  custom:          { conv: [0, 45], edge: [0, 30], plSource: 'model', desc: 'Custom — adjust sliders below.' },
  vegas_fav:       { conv: [0, 45], edge: [0, 30], plSource: 'fav', desc: 'Bet the Vegas favorite every fight. Negative expected — sportsbook vig.' },
  vegas_dog:       { conv: [0, 45], edge: [0, 30], plSource: 'dog', desc: 'Bet the Vegas underdog every fight. Negative expected — sportsbook vig.' },
  younger_all:     { conv: [0, 45], edge: [0, 30], plSource: 'younger', desc: 'Bet the younger fighter every fight, at any age gap.' },
  younger_3:       { conv: [0, 45], edge: [0, 30], plSource: 'younger', ageDiffMin: 3, desc: 'Bet the younger fighter only when the age gap is more than 3 years.' },
  younger_5:       { conv: [0, 45], edge: [0, 30], plSource: 'younger', ageDiffMin: 5, desc: 'Bet the younger fighter only when the age gap is more than 5 years.' },
}

const RANGES: Range[] = ['1M', '3M', '6M', 'YTD', 'ALL']
const PAGE_SIZE = 10

const WEIGHT_CLASSES_ORDERED = [
  "Women's Strawweight", "Women's Flyweight", "Women's Bantamweight", "Women's Featherweight",
  'Flyweight', 'Bantamweight', 'Featherweight', 'Lightweight',
  'Welterweight', 'Middleweight', 'Light Heavyweight', 'Heavyweight',
]

// ── Helpers ──────────────────────────────────────────────────────────────────

function getStartDate(range: Range): Date | null {
  const now = new Date()
  if (range === 'ALL') return null
  if (range === 'YTD') return new Date(now.getFullYear(), 0, 1)
  const days = range === '1M' ? 30 : range === '3M' ? 90 : 180
  const d = new Date(now)
  d.setDate(d.getDate() - days)
  return d
}

// ── Main component ───────────────────────────────────────────────────────────

export function OverviewTab() {
  const [fights, setFights]         = useState<BettingFightRow[]>([])
  const [loadingFights, setLoading] = useState(true)
  const [strategy, setStrategy]     = useState<string>('model_edge_5_15')
  const [convRange, setConvRange]   = useState<[number, number]>([0, 45])
  const [edgeRange, setEdgeRange]   = useState<[number, number]>([5, 15])
  const [timeRange, setTimeRange]   = useState<Range>('ALL')
  const [weightClass, setWeightClass] = useState<string>('')
  const [titleFilter, setTitleFilter] = useState<string>('all')
  const [page, setPage]             = useState(1)

  const preset  = PRESETS[strategy] ?? PRESETS.custom
  const plSource = preset.plSource
  const ageDiffMin = preset.ageDiffMin ?? 0
  const slidersDisabled = plSource !== 'model'

  // Fetch all fights once on mount
  useEffect(() => {
    analyticsService.getBettingFights().then((res) => {
      setFights(res.fights)
    }).finally(() => setLoading(false))
  }, [])

  // When a named preset is selected, snap sliders
  const handleStrategyChange = useCallback((s: string) => {
    setStrategy(s)
    const p = PRESETS[s]
    if (p) {
      setConvRange(p.conv as [number, number])
      setEdgeRange(p.edge as [number, number])
    }
    setPage(1)
  }, [])

  // When user drags slider, switch to custom
  const handleConvChange = useCallback((lo: number, hi: number) => {
    if (strategy !== 'custom') setStrategy('custom')
    setConvRange([lo, hi])
    setPage(1)
  }, [strategy])
  const handleEdgeChange = useCallback((lo: number, hi: number) => {
    if (strategy !== 'custom') setStrategy('custom')
    setEdgeRange([lo, hi])
    setPage(1)
  }, [strategy])

  // Date-range cutoff
  const startDate = useMemo(() => getStartDate(timeRange), [timeRange])

  // Client-side filter. `fellBack` is derived (not stored) so it never sets
  // state during render: if the date range produces nothing we retry without it.
  const { filtered, fellBack } = useMemo(() => {
    const matches = (f: BettingFightRow, applyDate: boolean): boolean => {
      if (applyDate && startDate && f.event_date) {
        if (new Date(f.event_date + 'T00:00:00') < startDate) return false
      }
      if (weightClass && f.weight_class !== weightClass) return false
      if (titleFilter === 'title' && !f.is_title) return false
      if (titleFilter === 'non_title' && f.is_title) return false
      // Younger-fighter strategies: need a defined age gap above the threshold
      if (plSource === 'younger') {
        if (f.pl_younger == null || f.age_diff == null) return false
        return f.age_diff > ageDiffMin
      }
      // Vegas strategies: no model filters
      if (plSource !== 'model') return true
      // Model strategies: apply conviction and edge filters
      if (f.conviction_pp < convRange[0] || f.conviction_pp > convRange[1]) return false
      if (f.edge_pp < edgeRange[0] || f.edge_pp > edgeRange[1]) return false
      return true
    }

    const withDate = fights.filter(f => matches(f, true))
    if (withDate.length === 0 && timeRange !== 'ALL') {
      return { filtered: fights.filter(f => matches(f, false)), fellBack: true }
    }
    return { filtered: withDate, fellBack: false }
  }, [fights, startDate, timeRange, weightClass, titleFilter, plSource, ageDiffMin, convRange, edgeRange])

  // Reset page on filter change
  const [prevFiltered, setPrevFiltered] = useState(filtered)
  if (filtered !== prevFiltered) {
    setPrevFiltered(filtered)
    setPage(1)
  }

  // Cumulative P&L chart data (grouped by event)
  const chartData = useMemo(() => {
    const sorted = [...filtered].sort((a, b) =>
      (a.event_date ?? '').localeCompare(b.event_date ?? ''))

    const eventMap = new Map<string, { date: string | null; name: string | null; pnl: number }>()
    for (const f of sorted) {
      const eid = f.event_id ?? f.fight_id
      if (!eventMap.has(eid)) {
        eventMap.set(eid, { date: f.event_date, name: f.event_name, pnl: 0 })
      }
      const e = eventMap.get(eid)!
      e.pnl += plOf(f, plSource) ?? 0
    }

    const sortedEvents = Array.from(eventMap.values())
      .sort((a, b) => (a.date ?? '').localeCompare(b.date ?? ''))
    const cumulative = sortedEvents.reduce<number[]>(
      (acc, e, i) => [...acc, (acc[i - 1] ?? 0) + e.pnl],
      [],
    )
    return sortedEvents.map((e, i) => ({
      date_label: formatEventDate(e.date),
      event_name: e.name,
      cumPnl: Math.round(cumulative[i] * 100 * 100) / 100,
    }))
  }, [filtered, plSource])

  // Bet count for the active source (younger fights without a known age gap are
  // already excluded by the filter, so filtered.length is the usable count).
  const bets = filtered.length

  // n-guard: below the 50-fight bar the chart is muted (not hidden) along with
  // the rest of the result treatment in StrategyResult.
  const isEmpty = bets === 0
  const muted   = bets < N_CONCLUSIVE
  const finalPnl  = chartData.at(-1)?.cumPnl ?? 0
  const lineColor = isEmpty ? 'var(--color-border)'
                  : muted   ? 'var(--color-text-muted)'
                  : finalPnl >= 0 ? 'var(--color-success)' : 'var(--color-error)'

  // Multiple-comparisons counter. Debounced so dragging a slider through many
  // values records one settled combination, not fifty.
  const { count, record, reset } = useComparisonCounter()
  const comboKey = useMemo(
    () => JSON.stringify({ strategy, weightClass, titleFilter, timeRange, convRange, edgeRange }),
    [strategy, weightClass, titleFilter, timeRange, convRange, edgeRange],
  )
  const settledCombo = useDebounce(comboKey, 600)
  useEffect(() => { if (!loadingFights) record(settledCombo) }, [settledCombo, loadingFights, record])

  // Keep the results region from collapsing mid-drag. When a slider crosses
  // into the empty state the chart/cards unmount; without a reserved height
  // the page shrinks, the browser clamps the scroll position, and the slider
  // shifts out from under the cursor. Remember the last populated height and
  // hold it while the region is empty.
  const wrapRef          = useRef<HTMLDivElement>(null)
  const resultsRef       = useRef<HTMLDivElement>(null)
  const lastResultsHeight = useRef<number>(0)
  useLayoutEffect(() => {
    if (!isEmpty && resultsRef.current) {
      lastResultsHeight.current = resultsRef.current.offsetHeight
    }
    if (wrapRef.current) {
      wrapRef.current.style.minHeight = isEmpty ? `${lastResultsHeight.current}px` : ''
    }
  })

  // Paginated fight cards (newest first)
  const sortedForCards = useMemo(() =>
    [...filtered].sort((a, b) => (b.event_date ?? '').localeCompare(a.event_date ?? '')),
  [filtered])
  const totalPages = Math.ceil(sortedForCards.length / PAGE_SIZE)
  const visible    = sortedForCards.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  // Chart footnote
  const footnotes: Record<string, string> = {
    model_pick:      `Cumulative P&L · flat $100/bet · ${bets} bets · all model picks`,
    model_edge_5_15: `Cumulative P&L · flat $100/bet · ${bets} bets · flat segments = no qualifying fights that event`,
    high_conv_20:    `Cumulative P&L · flat $100/bet · ${bets} bets · model win prob ≥70%`,
    edge_conv:       `Cumulative P&L · flat $100/bet · ${bets} bets · strictest filter`,
    custom:          `Cumulative P&L · flat $100/bet · ${bets} bets · custom filter`,
    vegas_fav:       `Cumulative P&L · flat $100/bet · ${bets} bets · Vegas favorite`,
    vegas_dog:       `Cumulative P&L · flat $100/bet · ${bets} bets · Vegas underdog`,
    younger_all:     `Cumulative P&L · flat $100/bet · ${bets} bets · younger fighter every fight`,
    younger_3:       `Cumulative P&L · flat $100/bet · ${bets} bets · younger fighter · age gap over 3y`,
    younger_5:       `Cumulative P&L · flat $100/bet · ${bets} bets · younger fighter · age gap over 5y`,
  }

  if (loadingFights) {
    return (
      <div className="space-y-3">
        {[1,2,3].map(i => <div key={i} className="h-16 animate-pulse rounded-lg bg-[var(--color-border)]" />)}
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Strategy dropdown */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>
          Strategy / Bet mode
        </label>
        <select
          value={strategy}
          onChange={(e) => handleStrategyChange(e.target.value)}
          className="w-full rounded border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
        >
          <optgroup label="Model strategies">
            <option value="model_pick">Model pick — no filter</option>
            <option value="model_edge_5_15">Model edge 5–15pp</option>
            <option value="high_conv_20">High conviction 20pp+</option>
            <option value="edge_conv">Edge 5–15pp + conviction 20pp+</option>
            <option value="custom">Custom (adjust sliders)</option>
          </optgroup>
          <optgroup label="Vegas baselines">
            <option value="vegas_fav">Always Vegas favorite</option>
            <option value="vegas_dog">Always Vegas underdog</option>
          </optgroup>
          <optgroup label="Age baselines">
            <option value="younger_all">Always the younger fighter</option>
            <option value="younger_3">Younger fighter, age gap 3y+</option>
            <option value="younger_5">Younger fighter, age gap 5y+</option>
          </optgroup>
        </select>
        <p className="text-xs text-[var(--color-text-muted)]">{PRESETS[strategy]?.desc}</p>
      </div>

      {/* Multiple-comparisons counter — persistent, resets only on explicit action */}
      <div className="flex items-start gap-2 rounded-lg border border-[var(--color-warning)]/40 bg-[var(--color-warning)]/10 px-3 py-2.5">
        <span aria-hidden="true" className="mt-0.5 shrink-0 text-[var(--color-warning-light)] dark:text-[var(--color-warning)]">⟳</span>
        <p className="min-w-0 flex-1 text-xs">
          <span className="font-semibold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
            You&apos;ve compared {count} {count === 1 ? 'strategy' : 'strategies'} this session.
          </span>{' '}
          <span className="text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
            The more combinations you try, the more likely one looks good by chance, not skill.
          </span>
        </p>
        <button
          type="button"
          onClick={reset}
          className="shrink-0 rounded px-1.5 py-0.5 text-[0.7rem] font-medium text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-border)]/40 hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]"
        >
          Reset
        </button>
      </div>

      {/* Sliders */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label className="block text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>
            Model conviction
          </label>
          <DualRangeSlider
            min={0} max={45} step={1}
            valueLo={convRange[0]} valueHi={convRange[1]}
            onChange={handleConvChange}
            disabled={slidersDisabled}
            unit="pp"
          />
          <p className="text-xs text-[var(--color-text-muted)]">
            Win prob minus 50%. 72% win prob = 22pp. Drag to set window.
          </p>
        </div>
        <div className="space-y-1">
          <label className="block text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>
            Model edge over Vegas
          </label>
          <DualRangeSlider
            min={0} max={30} step={1}
            valueLo={edgeRange[0]} valueHi={edgeRange[1]}
            onChange={handleEdgeChange}
            disabled={slidersDisabled}
            unit="pp"
          />
          <p className="text-xs text-[var(--color-text-muted)]">
            Model win % minus Vegas implied %. 5–15pp = historically profitable zone. Drag fill bar to shift window.
          </p>
        </div>
      </div>

      {/* Additional filters */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="space-y-1">
          <label className="block text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>
            Weight class
          </label>
          <select
            value={weightClass}
            onChange={(e) => { setWeightClass(e.target.value); setPage(1) }}
            className="w-full rounded border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
          >
            <option value="">All divisions</option>
            {WEIGHT_CLASSES_ORDERED.map(wc => <option key={wc} value={wc}>{wc}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <label className="block text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>
            Title fight
          </label>
          <select
            value={titleFilter}
            onChange={(e) => { setTitleFilter(e.target.value); setPage(1) }}
            className="w-full rounded border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
          >
            <option value="all">All fights</option>
            <option value="title">Title fights only</option>
            <option value="non_title">Non-title only</option>
          </select>
        </div>
      </div>

      {/* Time range */}
      <div className="flex flex-wrap items-center gap-1">
        {RANGES.map(r => (
          <button
            key={r}
            onClick={() => { setTimeRange(r); setPage(1) }}
            className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
              timeRange === r
                ? 'bg-[var(--color-text-primary-light)] text-[var(--color-bg-light)] dark:bg-[var(--color-text-primary)] dark:text-[var(--color-bg)]'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]'
            }`}
          >
            {r}
          </button>
        ))}
      </div>

      {fellBack && (
        <p className="text-xs text-[var(--color-text-muted)]">
          Showing all data — not enough history for {timeRange}.
        </p>
      )}

      {/* Results (chart + stats + cards). Reserve the last populated height
          while empty so a slider drag that crosses into "no matches" does not
          shrink the page and scroll-clamp the slider away from the cursor. */}
      <div ref={wrapRef}>
      {isEmpty ? (
        <div className="rounded-lg border border-[var(--color-border)] p-6 text-center text-sm text-[var(--color-text-muted)]">
          {titleFilter === 'title'
            ? 'No title fights match this selection. Title bouts are rare in the betting data.'
            : 'No fights match this filter.'}
        </div>
      ) : (
        <div ref={resultsRef} className="space-y-5">
          {/* Strategy result: baseline comparison, n-guard, CI-gated verdict,
              and the held-out confirmation panel */}
          <StrategyResult fights={filtered} src={plSource} />

          {/* Cumulative P&L — muted (grey line, no colour) below the n-guard */}
          <div>
            <ResponsiveContainer width="100%" height={200}>
              <ComposedChart data={chartData} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="ov-fill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={lineColor} stopOpacity={0.15} />
                    <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                <XAxis dataKey="date_label" tick={{ fill: 'var(--color-chart-axis)', fontSize: 11 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                <YAxis tickFormatter={(v) => `$${v}`} tick={{ fill: 'var(--color-chart-axis)', fontSize: 11 }} axisLine={false} tickLine={false} width={52} />
                <Tooltip
                  formatter={(v) => [`$${Number(v).toFixed(2)}`, 'Cumulative P&L']}
                  labelFormatter={(label) => String(label)}
                  contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 6, fontSize: 12 }}
                />
                <ReferenceLine y={0} stroke="var(--color-border)" strokeWidth={1.5} />
                {/* One Area carries both the gradient fill and the colored line,
                    so the tooltip shows a single Cumulative P&L row (a separate
                    Line on the same dataKey used to duplicate it). */}
                <Area type="monotone" dataKey="cumPnl" name="Cumulative P&L" stroke={lineColor} strokeWidth={2} fill="url(#ov-fill)" dot={false} activeDot={{ r: 4, fill: lineColor }} isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
            <p className="mt-1 text-xs text-[var(--color-text-muted)]">{footnotes[strategy] ?? footnotes.custom}</p>
          </div>

          {/* Standing pre-registration note — sits with every result */}
          <div className="flex items-start gap-2 rounded-lg border border-[var(--color-border)] border-l-[3px] border-l-[var(--color-primary)] bg-white px-3 py-2.5 dark:bg-[var(--color-surface)]">
            <span aria-hidden="true" className="mt-0.5 shrink-0 text-[var(--color-primary)]">◆</span>
            <p className="text-xs text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
              <span className="font-semibold">Before you trust a strategy, ask: did you expect it to work before you ran it?</span>{' '}
              <span className="text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">A winner pulled out of a filter hunt is usually luck.</span>
            </p>
          </div>

          {/* Fight cards */}
          <div className="space-y-2">
            {visible.map(f => <BettingFightCard key={f.fight_id} f={f} mode={plSource} />)}
          </div>
          <Pagination
            page={page}
            totalPages={totalPages}
            onPrev={() => setPage(p => p - 1)}
            onNext={() => setPage(p => p + 1)}
            total={sortedForCards.length}
            pageSize={PAGE_SIZE}
          />
        </div>
      )}
      </div>
    </div>
  )
}
