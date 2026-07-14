import { useState, useEffect, useCallback } from 'react'
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import { analyticsService } from '@services/analyticsService'
import type { RoiEventEntry } from '@t/api'

const STRATEGIES = [
  { key: 'model_edge_5_15', label: 'Model edge 5–15%' },
  { key: 'vegas_fav',       label: 'Always bet Vegas fav' },
  { key: 'vegas_dog',       label: 'Always bet Vegas underdog' },
  { key: 'model_pick',      label: 'Always bet model pick' },
] as const

const RANGES = ['1M', '3M', '6M', 'YTD', 'ALL'] as const
type Range = (typeof RANGES)[number]

const FOOTNOTES: Record<string, string> = {
  model_edge_5_15: 'Flat segments = no qualifying fights that event.',
  vegas_fav: 'Negative due to sportsbook vig — the house takes a cut on every line.',
  vegas_dog: 'Negative due to sportsbook vig — the house takes a cut on every line.',
  model_pick: '$100/bet · Vegas-tracked fights only.',
}

function formatDate(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
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

function buildChartData(events: RoiEventEntry[], range: Range) {
  const start = getStartDate(range)
  const filtered = start
    ? events.filter((e) => e.event_date && new Date(e.event_date) >= start)
    : events

  let cumPnl = 0
  return {
    rows: filtered.map((e) => {
      cumPnl += e.pnl
      return {
        ...e,
        date_label: formatDate(e.event_date),
        cumPnl: Math.round(cumPnl * 100 * 100) / 100, // $100 unit, 2dp
      }
    }),
    fellBack: start !== null && filtered.length === 0,
  }
}

export function ROIOverTimeChart() {
  const [strategy, setStrategy] = useState<string>('model_edge_5_15')
  const [range, setRange] = useState<Range>('ALL')
  const [events, setEvents] = useState<RoiEventEntry[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (s: string) => {
    setLoading(true)
    try {
      const res = await analyticsService.getRoiOverTime(s)
      setEvents(res.events)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(strategy) }, [strategy, load])

  const { rows, fellBack } = buildChartData(events, range)
  const finalPnl = rows.at(-1)?.cumPnl ?? 0
  const positive = finalPnl >= 0
  const lineColor = positive ? '#2a78d6' : '#e34948'

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={strategy}
          onChange={(e) => { setStrategy(e.target.value); setRange('ALL') }}
          className="rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
        >
          {STRATEGIES.map((s) => (
            <option key={s.key} value={s.key}>{s.label}</option>
          ))}
        </select>
        <div className="flex gap-1">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                range === r
                  ? 'bg-[var(--color-text-primary-light)] text-[var(--color-bg-light)] dark:bg-[var(--color-text-primary)] dark:text-[var(--color-bg)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {fellBack && (
        <p className="text-xs text-[var(--color-text-muted)]">
          Showing all data — not enough history for {range}.
        </p>
      )}

      {loading ? (
        <div className="h-[200px] animate-pulse rounded bg-[var(--color-border)]" />
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={rows} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="roi-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={lineColor} stopOpacity={0.15} />
                <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
            <XAxis
              dataKey="date_label"
              tick={{ fill: '#898781', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={(v) => `$${v}`}
              tick={{ fill: '#898781', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={52}
            />
            <Tooltip
              formatter={(v) => [`$${Number(v).toFixed(2)}`, 'Cumulative P&L']}
              labelFormatter={(label) => label}
              contentStyle={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 6,
                fontSize: 12,
              }}
            />
            <ReferenceLine y={0} stroke="var(--color-border)" strokeWidth={1.5} />
            <Area
              type="monotone"
              dataKey="cumPnl"
              stroke="none"
              fill="url(#roi-fill)"
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="cumPnl"
              stroke={lineColor}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: lineColor }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
      <p className="text-xs text-[var(--color-text-muted)]">
        {FOOTNOTES[strategy]} Flat $100/bet · {rows.length} events shown.
      </p>
    </div>
  )
}
