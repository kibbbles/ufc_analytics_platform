import type { BettingInsightsResponse } from '@t/api'

interface Props {
  data: BettingInsightsResponse
}

interface KPI {
  label: string
  value: string
  sub: string
}

export function BettingKPIRow({ data }: Props) {
  const modelPick = data.strategies.find((s) => s.strategy_key === 'model_pick')
  const accuracy = modelPick ? ((modelPick.wins / modelPick.bets) * 100).toFixed(1) : '—'
  const accuracySub = modelPick ? `${modelPick.wins} of ${modelPick.bets} correct` : ''

  const totalFights = data.upset_rates.reduce((sum, r) => sum + r.total_fights, 0)
  const totalUpsets = data.upset_rates.reduce((sum, r) => sum + r.upset_count, 0)
  const upsetRate = totalFights > 0 ? ((totalUpsets / totalFights) * 100).toFixed(1) : '—'

  const avgEdgePp = (data.avg_edge_qualifying * 100).toFixed(1)

  const kpis: KPI[] = [
    { label: 'Fights tracked', value: String(data.sample_size), sub: 'since Mar 2026' },
    { label: 'Model accuracy', value: `${accuracy}%`, sub: accuracySub },
    { label: 'Upset rate', value: `${upsetRate}%`, sub: 'high-conviction misses' },
    { label: 'Avg model edge', value: `${avgEdgePp}pp`, sub: '5–15% filter' },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 py-5 lg:grid-cols-4">
      {kpis.map((k) => (
        <div
          key={k.label}
          className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3"
        >
          <p
            className="text-[11px] font-medium uppercase tracking-wider text-[var(--color-text-muted)]"
            style={{ letterSpacing: '0.04em' }}
          >
            {k.label}
          </p>
          <p className="mt-1 text-[20px] font-medium tabular-nums leading-tight">{k.value}</p>
          <p className="mt-0.5 text-[11px] text-[var(--color-text-muted)]">{k.sub}</p>
        </div>
      ))}
    </div>
  )
}
