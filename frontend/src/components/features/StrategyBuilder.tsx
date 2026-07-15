import { useState, useEffect, useRef, useCallback } from 'react'
import { analyticsService } from '@services/analyticsService'
import type { BettingRoiResponse } from '@t/api'

const WEIGHT_CLASSES = [
  'Heavyweight', 'Light Heavyweight', 'Middleweight', 'Welterweight',
  'Lightweight', 'Featherweight', 'Bantamweight', 'Flyweight',
  "Women's Featherweight", "Women's Bantamweight", "Women's Flyweight", "Women's Strawweight",
]

interface Params {
  side: string
  conviction: string
  edge: string
  weight_class: string
  upset_filter: string
  title_filter: string
}

function convictionToRange(conviction: string) {
  switch (conviction) {
    case 'u10':   return { min: 0, max: 0.10 }
    case '10_20': return { min: 0.10, max: 0.20 }
    case '20_30': return { min: 0.20, max: 0.30 }
    case '30p':   return { min: 0.30, max: null }
    default:      return { min: null, max: null }
  }
}

function edgeToRange(edge: string) {
  switch (edge) {
    case 'positive': return { min: 0.001, max: null }
    case '5_15':     return { min: 0.05,  max: 0.15 }
    case '15p':      return { min: 0.15,  max: null }
    default:         return { min: null, max: null }
  }
}

function Field({
  label, value, onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
}) {
  return (
    <div className="space-y-1">
      <label className="block text-[11px] font-medium uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-2 py-1.5 text-[13px] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  )
}

export function StrategyBuilder() {
  const [params, setParams] = useState<Params>({
    side: 'model_pick',
    conviction: 'any',
    edge: 'any',
    weight_class: 'any',
    upset_filter: 'all',
    title_filter: 'all',
  })
  const [result, setResult] = useState<BettingRoiResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetch = useCallback(async (p: Params) => {
    setLoading(true)
    setError(null)
    try {
      const conviction = convictionToRange(p.conviction)
      const edge = edgeToRange(p.edge)
      const data = await analyticsService.getBettingRoi({
        side: p.side,
        conviction_min: conviction.min,
        conviction_max: conviction.max,
        weight_class: p.weight_class === 'any' ? null : p.weight_class,
        edge_min: edge.min,
        edge_max: edge.max,
        upset_filter: p.upset_filter,
        title_filter: p.title_filter,
      })
      setResult(data)
    } catch {
      setError('Failed to load results')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => fetch(params), 400)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [params, fetch])

  const set = (key: keyof Params) => (value: string) =>
    setParams((prev) => ({ ...prev, [key]: value }))

  const noData    = result && result.bets < 10
  const lowSample = result && result.bets >= 10 && result.bets < 30
  const positive  = result && result.roi > 0

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Bet side" value={params.side} onChange={set('side')} options={[
          { value: 'model_pick', label: 'Model pick' },
          { value: 'vegas_fav',  label: 'Vegas favorite' },
          { value: 'vegas_dog',  label: 'Vegas underdog' },
        ]} />
        <Field label="Model conviction" value={params.conviction} onChange={set('conviction')} options={[
          { value: 'any',   label: 'Any' },
          { value: 'u10',   label: 'Under 10%' },
          { value: '10_20', label: '10–20%' },
          { value: '20_30', label: '20–30%' },
          { value: '30p',   label: '30%+' },
        ]} />
        <Field label="Model edge over Vegas" value={params.edge} onChange={set('edge')} options={[
          { value: 'any',      label: 'Any' },
          { value: 'positive', label: 'Positive only' },
          { value: '5_15',     label: '5–15% only' },
          { value: '15p',      label: '15%+ only' },
        ]} />
        <Field label="Weight class" value={params.weight_class} onChange={set('weight_class')} options={[
          { value: 'any', label: 'All divisions' },
          ...WEIGHT_CLASSES.map((wc) => ({ value: wc, label: wc })),
        ]} />
        <Field label="Upset filter" value={params.upset_filter} onChange={set('upset_filter')} options={[
          { value: 'all',         label: 'All fights' },
          { value: 'upsets_only', label: 'Upsets only (≥20pp conviction wrong)' },
          { value: 'non_upsets',  label: 'Non-upsets only' },
        ]} />
        <Field label="Title fight" value={params.title_filter} onChange={set('title_filter')} options={[
          { value: 'all',       label: 'All fights' },
          { value: 'title',     label: 'Title fights only' },
          { value: 'non_title', label: 'Non-title only' },
        ]} />
      </div>

      {/* Result card */}
      <div className="rounded-lg border border-[var(--color-border)] p-4 min-h-[88px] flex items-center">
        {loading && (
          <p className="text-sm text-[var(--color-text-muted)] animate-pulse">Calculating…</p>
        )}
        {error && <p className="text-sm text-[var(--color-error-light)] dark:text-[var(--color-error)]">{error}</p>}
        {!loading && !error && noData && (
          <p className="text-sm text-[var(--color-text-muted)]">
            Not enough data for this combination.
          </p>
        )}
        {!loading && !error && result && !noData && (
          <div className="w-full">
            {lowSample && (
              <p className="mb-2 text-xs text-[var(--color-warning-light)] dark:text-[var(--color-warning)]">
                Small sample (n={result.bets}) — treat with caution.
              </p>
            )}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {[
                { label: 'Bets', value: String(result.bets) },
                { label: 'Win rate', value: result.bets > 0 ? `${((result.wins / result.bets) * 100).toFixed(0)}%` : '—' },
                { label: 'Total P&L', value: `${result.pnl * 100 >= 0 ? '+' : ''}$${(result.pnl * 100).toFixed(0)}`, colored: true },
                { label: 'ROI', value: `${result.roi >= 0 ? '+' : ''}${(result.roi * 100).toFixed(1)}%`, colored: true },
              ].map((stat) => (
                <div key={stat.label}>
                  <p className="text-[11px] uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>{stat.label}</p>
                  <p className={`mt-0.5 font-mono text-[20px] font-medium tabular-nums leading-tight ${stat.colored ? (positive ? 'text-[var(--color-success-light)] dark:text-[var(--color-success)]' : 'text-[var(--color-error-light)] dark:text-[var(--color-error)]') : ''}`}>
                    {stat.value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      <p className="text-xs text-[var(--color-text-muted)]">
        Flat $100/bet. Edge filter is model's predicted win probability minus Vegas implied probability on
        the selected side. Conviction = max(win prob) − 50%.
      </p>
    </div>
  )
}
