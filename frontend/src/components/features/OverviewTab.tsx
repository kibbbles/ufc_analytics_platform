import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts'
import { analyticsService } from '@services/analyticsService'
import type { BettingFightRow } from '@t/api'
import { DualRangeSlider } from './DualRangeSlider'
import Pagination from '@components/common/Pagination'
import InfoTooltip from '@components/common/InfoTooltip'

// ── Types ────────────────────────────────────────────────────────────────────

type PlSource = 'model' | 'fav' | 'dog'
type Range    = '1M' | '3M' | '6M' | 'YTD' | 'ALL'

interface Preset {
  conv: [number, number]
  edge: [number, number]
  plSource: PlSource
  desc: string
}

const PRESETS: Record<string, Preset> = {
  model_pick:      { conv: [0, 45], edge: [0, 30], plSource: 'model', desc: 'Bet on the model\'s pick every fight. No edge or conviction filter.' },
  model_edge_5_15: { conv: [0, 45], edge: [5, 15], plSource: 'model', desc: 'Bet only when the model is 5–15pp more confident than Vegas. Signal zone.' },
  high_conv_20:    { conv: [20, 45], edge: [0, 30], plSource: 'model', desc: 'Bet only when model win probability ≥70% (conviction ≥20pp).' },
  edge_conv:       { conv: [20, 45], edge: [5, 15], plSource: 'model', desc: 'Strictest filter: 5–15pp edge AND conviction ≥20pp. Smallest sample.' },
  custom:          { conv: [0, 45], edge: [0, 30], plSource: 'model', desc: 'Custom — adjust sliders below.' },
  vegas_fav:       { conv: [0, 45], edge: [0, 30], plSource: 'fav', desc: 'Bet the Vegas favorite every fight. Negative expected — sportsbook vig.' },
  vegas_dog:       { conv: [0, 45], edge: [0, 30], plSource: 'dog', desc: 'Bet the Vegas underdog every fight. Negative expected — sportsbook vig.' },
}

const RANGES: Range[] = ['1M', '3M', '6M', 'YTD', 'ALL']
const PAGE_SIZE = 10

const WEIGHT_CLASSES_ORDERED = [
  "Women's Strawweight", "Women's Flyweight", "Women's Bantamweight", "Women's Featherweight",
  'Flyweight', 'Bantamweight', 'Featherweight', 'Lightweight',
  'Welterweight', 'Middleweight', 'Light Heavyweight', 'Heavyweight',
]

// ── Helpers ──────────────────────────────────────────────────────────────────

const CURRENT_YEAR = new Date().getFullYear()

function fmtEventDate(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00')
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  const sameYear = d.getFullYear() === CURRENT_YEAR
  return `${months[d.getMonth()]} ${d.getDate()}${sameYear ? '' : ` '${String(d.getFullYear()).slice(2)}`}`
}

function getStartDate(range: Range): Date | null {
  const now = new Date()
  if (range === 'ALL') return null
  if (range === 'YTD') return new Date(now.getFullYear(), 0, 1)
  const days = range === '1M' ? 30 : range === '3M' ? 90 : 180
  const d = new Date(now)
  d.setDate(d.getDate() - days)
  return d
}

// ── Fight card ───────────────────────────────────────────────────────────────

function BettingFightCard({ f, mode }: { f: BettingFightRow; mode: PlSource }) {
  const inHotZone  = f.edge_pp >= 5 && f.edge_pp <= 15
  const showPills  = mode !== 'fav' && mode !== 'dog'

  return (
    <div className="relative rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4 py-3 text-sm">
      {/* Corner badge */}
      <div
        className={`absolute top-0 right-0 rounded-bl-lg rounded-tr-lg px-2 py-0.5 text-xs font-semibold ${
          f.is_correct
            ? 'bg-[var(--color-success)]/15 text-[var(--color-success-light)] dark:text-[var(--color-success)]'
            : 'bg-[var(--color-error)]/15 text-[var(--color-error-light)] dark:text-[var(--color-error)]'
        }`}
      >
        {f.is_correct ? '✓' : '✗'}
      </div>

      {/* Matchup */}
      <p className="font-semibold pr-12">
        <span>{f.pick ?? '?'}</span>
        <span className="text-[var(--color-text-muted)] font-normal"> vs </span>
        <span className="text-[var(--color-text-muted)] font-normal">{f.opponent ?? '?'}</span>
      </p>

      {/* Actual result */}
      {f.actual_winner_name && (
        <p className="mt-0.5 text-[var(--color-warning-light)] dark:text-[var(--color-warning)]">
          {f.actual_winner_name}{f.result_method ? ` · ${f.result_method}` : ''}
        </p>
      )}

      {/* Meta */}
      <p className="mt-0.5 text-xs uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>
        {[f.event_name, fmtEventDate(f.event_date), f.weight_class, f.is_title ? 'Title fight' : null]
          .filter(Boolean).join(' · ')}
      </p>

      {/* Model row */}
      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs">
        <span className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>MODEL</span>
        <span className="font-mono">
          {f.fighter_a_name} {Math.round(f.win_prob_a * 100)}% / {f.fighter_b_name} {Math.round(f.win_prob_b * 100)}%
        </span>

        {showPills && (
          <>
            <span
              className={`rounded px-1.5 py-0.5 text-xs font-semibold ${
                f.is_correct
                  ? 'bg-[var(--color-success)]/15 text-[var(--color-success-light)] dark:text-[var(--color-success)]'
                  : 'bg-[var(--color-error)]/15 text-[var(--color-error-light)] dark:text-[var(--color-error)]'
              }`}
            >
              {f.is_correct ? '✓ pick' : '✗ pick'} · {(f.pick_prob * 100).toFixed(0)}%
            </span>
            <span className="font-mono text-[var(--color-accent)]">
              {f.conviction_pp.toFixed(0)}pp conv
            </span>
            <span
              className={`rounded px-1.5 py-0.5 text-xs font-mono ${
                inHotZone
                  ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent)]'
                  : 'border border-[var(--color-border)] text-[var(--color-text-muted)]'
              }`}
            >
              {f.edge_pp >= 0 ? '+' : ''}{f.edge_pp.toFixed(1)}pp vs Vegas
            </span>
            <InfoTooltip label="What does pp vs Vegas mean?">
              <strong className="font-semibold text-[var(--color-text-light)] dark:text-[var(--color-text)]">
                pp = percentage points.
              </strong>{' '}
              The gap between the model&apos;s win probability and the probability implied by the
              Vegas line. A positive edge means the model is more confident in this pick than the
              betting market.
            </InfoTooltip>
          </>
        )}
        {!showPills && (
          <span className="text-[var(--color-text-muted)] text-xs">
            {mode === 'fav' ? 'Vegas favorite' : 'Vegas underdog'} strategy active
          </span>
        )}
      </div>
    </div>
  )
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
  const [fellBack, setFellBack]     = useState(false)

  const preset  = PRESETS[strategy] ?? PRESETS.custom
  const plSource = preset.plSource
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

  // Client-side filter
  const filtered = useMemo(() => {
    let result = fights.filter(f => {
      // Date range
      if (startDate && f.event_date) {
        if (new Date(f.event_date + 'T00:00:00') < startDate) return false
      }
      // Weight class
      if (weightClass && f.weight_class !== weightClass) return false
      // Title fight
      if (titleFilter === 'title' && !f.is_title) return false
      if (titleFilter === 'non_title' && f.is_title) return false
      // Vegas strategies: no model filters
      if (plSource !== 'model') return true
      // Model strategies: apply conviction and edge filters
      if (f.conviction_pp < convRange[0] || f.conviction_pp > convRange[1]) return false
      if (f.edge_pp < edgeRange[0] || f.edge_pp > edgeRange[1]) return false
      return true
    })

    // Fall back to ALL if range produces nothing
    if (result.length === 0 && timeRange !== 'ALL') {
      setFellBack(true)
      result = fights.filter(f => {
        if (weightClass && f.weight_class !== weightClass) return false
        if (titleFilter === 'title' && !f.is_title) return false
        if (titleFilter === 'non_title' && f.is_title) return false
        if (plSource !== 'model') return true
        if (f.conviction_pp < convRange[0] || f.conviction_pp > convRange[1]) return false
        if (f.edge_pp < edgeRange[0] || f.edge_pp > edgeRange[1]) return false
        return true
      })
    } else {
      setFellBack(false)
    }
    return result
  }, [fights, startDate, timeRange, weightClass, titleFilter, plSource, convRange, edgeRange])

  // Reset page on filter change
  useEffect(() => setPage(1), [filtered])

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
      e.pnl += plSource === 'fav' ? f.pl_fav : plSource === 'dog' ? f.pl_dog : f.pl_model
    }

    let cum = 0
    return Array.from(eventMap.values())
      .sort((a, b) => (a.date ?? '').localeCompare(b.date ?? ''))
      .map(e => {
        cum += e.pnl
        return { date_label: fmtEventDate(e.date), event_name: e.name, cumPnl: Math.round(cum * 100 * 100) / 100 }
      })
  }, [filtered, plSource])

  // Stat totals
  const stats = useMemo(() => {
    const bets = filtered.length
    const wins = filtered.filter(f =>
      plSource === 'fav' ? f.pl_fav > 0 :
      plSource === 'dog' ? f.pl_dog > 0 :
      f.is_correct
    ).length
    const pnl = filtered.reduce((s, f) =>
      s + (plSource === 'fav' ? f.pl_fav : plSource === 'dog' ? f.pl_dog : f.pl_model), 0)
    const roi = bets > 0 ? pnl / bets : 0
    return { bets, wins, pnl, roi }
  }, [filtered, plSource])

  const finalPnl   = chartData.at(-1)?.cumPnl ?? 0
  const lineColor  = finalPnl >= 0 ? 'var(--color-success)' : 'var(--color-error)'
  const pnl100     = (stats.pnl * 100)
  const roi100     = stats.roi * 100
  const noData     = stats.bets < 10
  const lowSample  = stats.bets >= 10 && stats.bets < 30

  // Paginated fight cards (newest first)
  const sortedForCards = useMemo(() =>
    [...filtered].sort((a, b) => (b.event_date ?? '').localeCompare(a.event_date ?? '')),
  [filtered])
  const totalPages = Math.ceil(sortedForCards.length / PAGE_SIZE)
  const visible    = sortedForCards.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  // Footnote
  const footnotes: Record<string, string> = {
    model_pick:      `Flat $100/bet · ${stats.bets} bets · all model picks`,
    model_edge_5_15: `Flat segments = no qualifying fights that event. $100/bet · ${stats.bets} bets.`,
    high_conv_20:    `Flat $100/bet · ${stats.bets} bets · model win prob ≥70%`,
    edge_conv:       `Flat $100/bet · ${stats.bets} bets · strictest filter`,
    custom:          `Flat $100/bet · ${stats.bets} bets · custom filter`,
    vegas_fav:       `Flat $100/bet · ${stats.bets} bets · Vegas favorite · negative expected due to sportsbook vig`,
    vegas_dog:       `Flat $100/bet · ${stats.bets} bets · Vegas underdog · negative expected due to sportsbook vig`,
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
        </select>
        <p className="text-xs text-[var(--color-text-muted)]">{PRESETS[strategy]?.desc}</p>
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

      {/* No data guard */}
      {noData ? (
        <div className="rounded-lg border border-[var(--color-border)] p-6 text-center text-sm text-[var(--color-text-muted)]">
          Not enough fights match — try widening the filters.
        </div>
      ) : (
        <>
          {lowSample && (
            <p className="rounded-lg border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/10 px-3 py-2 text-xs text-[var(--color-warning-light)] dark:text-[var(--color-warning)]">
              Small sample (n={stats.bets}) — interpret with caution.
            </p>
          )}

          {/* Chart */}
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
                <Area type="monotone" dataKey="cumPnl" stroke="none" fill="url(#ov-fill)" isAnimationActive={false} />
                <Line type="monotone" dataKey="cumPnl" stroke={lineColor} strokeWidth={2} dot={false} activeDot={{ r: 4, fill: lineColor }} isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
            <p className="mt-1 text-xs text-[var(--color-text-muted)]">{footnotes[strategy] ?? footnotes.custom}</p>
          </div>

          {/* Stat cards */}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[
              { label: 'Bets', value: String(stats.bets), colored: false },
              { label: 'Win rate', value: stats.bets > 0 ? `${((stats.wins / stats.bets) * 100).toFixed(0)}%` : '—', colored: false },
              { label: 'Total P&L', value: `${pnl100 >= 0 ? '+' : ''}$${pnl100.toFixed(0)}`, colored: true, pos: pnl100 >= 0 },
              { label: 'ROI', value: `${roi100 >= 0 ? '+' : ''}${roi100.toFixed(1)}%`, colored: true, pos: roi100 >= 0 },
            ].map((s) => (
              <div key={s.label} className="rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2.5">
                <p className="text-xs uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>{s.label}</p>
                <p className={`mt-0.5 font-mono text-xl font-medium tabular-nums leading-tight ${
                  s.colored
                    ? s.pos
                      ? 'text-[var(--color-success-light)] dark:text-[var(--color-success)]'
                      : 'text-[var(--color-error-light)] dark:text-[var(--color-error)]'
                    : ''
                }`}>
                  {s.value}
                </p>
              </div>
            ))}
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
        </>
      )}
    </div>
  )
}
