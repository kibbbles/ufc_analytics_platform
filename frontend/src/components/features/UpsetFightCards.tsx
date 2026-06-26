import { useState, useEffect, useCallback } from 'react'
import { analyticsService } from '@services/analyticsService'
import type { UpsetFightCard } from '@t/api'

const WEIGHT_CLASSES = [
  'Heavyweight', 'Light Heavyweight', 'Middleweight', 'Welterweight',
  'Lightweight', 'Featherweight', 'Bantamweight', 'Flyweight',
  "Women's Featherweight", "Women's Bantamweight", "Women's Flyweight", "Women's Strawweight",
]

const CONVICTION_OPTIONS = [
  { value: 0.30, label: 'Any ≥30%' },
  { value: 0.40, label: 'High ≥40%' },
  { value: 0.45, label: 'Very high ≥45%' },
]

function formatDate(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function oddsLabel(odds: number | null) {
  if (odds === null) return '—'
  return odds > 0 ? `+${odds}` : String(odds)
}

export function UpsetFightCards() {
  const [weightClass, setWeightClass] = useState<string>('')
  const [convictionMin, setConvictionMin] = useState<number>(0.30)
  const [fights, setFights] = useState<UpsetFightCard[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (wc: string, conv: number) => {
    setLoading(true)
    try {
      const res = await analyticsService.getBettingUpsets({
        weight_class: wc || null,
        conviction_min: conv,
      })
      setFights(res.fights)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(weightClass, convictionMin) }, [weightClass, convictionMin, load])

  return (
    <div className="space-y-5">
      {/* Definition */}
      <p className="text-sm text-[var(--color-text-muted)]">
        <strong className="text-[var(--color-text)]">"Upset" here</strong> means the model was wrong AND had ≥30% conviction on the losing pick.
        This is NOT the same as a Vegas underdog winning — it measures where the model gets confidently fooled.
      </p>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={weightClass}
          onChange={(e) => setWeightClass(e.target.value)}
          className="rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
        >
          <option value="">All divisions</option>
          {WEIGHT_CLASSES.map((wc) => (
            <option key={wc} value={wc}>{wc}</option>
          ))}
        </select>
        <select
          value={convictionMin}
          onChange={(e) => setConvictionMin(Number(e.target.value))}
          className="rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
        >
          {CONVICTION_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg bg-[var(--color-border)]" />
          ))}
        </div>
      )}

      {!loading && fights.length === 0 && (
        <p className="text-sm text-[var(--color-text-muted)]">No upsets match this filter.</p>
      )}

      {!loading && fights.length > 0 && (
        <div className="space-y-2">
          {fights.map((f) => (
            <div
              key={f.fight_id}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-[11px] font-medium uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>
                    {f.event_name ?? f.event_id} · {formatDate(f.event_date)} · {f.weight_class ?? ''}
                  </p>
                  <p className="mt-1 font-semibold">
                    {f.fighter_a_name ?? '?'} vs. {f.fighter_b_name ?? '?'}
                  </p>
                  {f.winner_name && (
                    <p className="text-sm text-[var(--color-text-muted)]">
                      {f.winner_name} wins{f.method ? ` by ${f.method}` : ''}
                    </p>
                  )}
                </div>
                <span className="shrink-0 rounded px-2 py-0.5 text-[11px] font-semibold text-red-700 dark:text-red-400"
                  style={{ background: 'transparent', border: '1px solid currentColor' }}>
                  Upset
                </span>
              </div>
              <p className="mt-2 text-[12px] text-[var(--color-text-muted)]">
                Conviction: <span className="font-mono font-semibold text-[var(--color-text)]">{(f.conviction * 100).toFixed(0)}%</span>
                {f.model_pick_name && (
                  <> · Model pick: <span className="text-[var(--color-text)]">{f.model_pick_name}</span></>
                )}
                {f.model_pick_odds !== null && (
                  <> · odds: <span className="font-mono text-[var(--color-text)]">{oddsLabel(f.model_pick_odds)}</span></>
                )}
                {' · '}loss: <span className="font-mono text-red-600 dark:text-red-400">$100</span>
              </p>
            </div>
          ))}
          <p className="pt-1 text-xs text-[var(--color-text-muted)]">
            {fights.length} upset{fights.length !== 1 ? 's' : ''} shown. Includes all predictions, not just Vegas-odds fights.
          </p>
        </div>
      )}
    </div>
  )
}
