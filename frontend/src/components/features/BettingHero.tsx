import type { BettingInsightsResponse } from '@t/api'

interface Props {
  data: BettingInsightsResponse
}

export function BettingHero({ data }: Props) {
  const edge = data.strategies.find((s) => s.strategy_key === 'model_edge_5_15')

  const roi = edge ? (edge.roi * 100).toFixed(1) : '—'
  const pnlUsd = edge ? `$${(edge.pnl * 100).toFixed(0)}` : '—'
  const positive = edge ? edge.roi >= 0 : false

  return (
    <div className="py-6 border-b border-[var(--color-border)]">
      <p
        className="text-xs font-medium uppercase tracking-widest text-[var(--color-text-muted)]"
        style={{ letterSpacing: '0.04em' }}
      >
        Model Edge 5–15% over Vegas
      </p>
      <div className="mt-1 flex flex-wrap items-baseline gap-3">
        <span
          className={`text-[32px] font-medium tabular-nums leading-none ${positive ? 'text-[var(--color-success-light)] dark:text-[var(--color-success)]' : 'text-[var(--color-error-light)] dark:text-[var(--color-error)]'}`}
        >
          {positive ? '+' : ''}
          {roi}%
        </span>
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium ${positive ? 'bg-[var(--color-success)]/10 text-[var(--color-success-light)] dark:bg-[var(--color-success)]/10 dark:text-[var(--color-success)]' : 'bg-[var(--color-error)]/10 text-[var(--color-error-light)] dark:bg-[var(--color-error)]/10 dark:text-[var(--color-error)]'}`}
        >
          Best strategy ROI
        </span>
      </div>
      <p className="mt-2 text-sm text-[var(--color-text-muted)]">
        {edge ? `${edge.bets} bets · ${edge.wins} wins · ${positive ? '+' : ''}${pnlUsd} P&L ($100/bet) · ` : ''}
        {data.sample_size} fights tracked total
      </p>
      <p className="mt-1 text-xs text-[var(--color-text-muted)]">
        Early signal — needs ~400 fights to confirm. 26 bets is not a sufficient sample.
      </p>
    </div>
  )
}
