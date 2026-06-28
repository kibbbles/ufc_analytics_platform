import type { StrategyRoiRow } from '@t/api'

interface Props {
  strategies: StrategyRoiRow[]
}

function pnlLabel(pnl: number): string {
  const usd = pnl * 100
  const sign = usd >= 0 ? '+' : ''
  return `${sign}$${Math.abs(usd).toFixed(0)}`
}

function roiLabel(roi: number): string {
  const sign = roi >= 0 ? '+' : ''
  return `${sign}${(roi * 100).toFixed(1)}%`
}

export function StrategyLeaderboard({ strategies }: Props) {
  const sorted = [...strategies].sort((a, b) => b.roi - a.roi)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-[var(--color-border)]">
            <th className="py-2 pr-4 text-left font-medium text-[var(--color-text-muted)]">Strategy</th>
            <th className="py-2 px-3 text-right font-medium text-[var(--color-text-muted)]">Bets</th>
            <th className="py-2 px-3 text-right font-medium text-[var(--color-text-muted)]">Wins</th>
            <th className="py-2 px-3 text-right font-medium text-[var(--color-text-muted)]">Total P&L</th>
            <th className="py-2 pl-3 text-right font-medium text-[var(--color-text-muted)]">ROI</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => {
            const lowSample = row.bets < 50
            const positive = row.roi > 0

            return (
              <tr
                key={row.strategy_key}
                className="border-b border-[var(--color-border)]"
                style={{ opacity: lowSample ? 0.45 : 1 }}
              >
                <td className="py-3 pr-4">
                  {row.strategy_name}
                  {lowSample && (
                    <span
                      className="ml-2 rounded px-1.5 py-px text-[10px] text-[var(--color-text-muted)]"
                      style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
                    >
                      n={row.bets}, low sample
                    </span>
                  )}
                </td>
                <td className="py-3 px-3 text-right font-mono tabular-nums">{row.bets}</td>
                <td className="py-3 px-3 text-right font-mono tabular-nums">{row.wins}</td>
                <td className="py-3 px-3 text-right font-mono tabular-nums font-medium">
                  <span style={{ color: positive ? '#3b6d11' : '#a32d2d' }}>
                    {pnlLabel(row.pnl)}
                  </span>
                </td>
                <td className="py-3 pl-3 text-right font-mono tabular-nums font-semibold">
                  <span style={{ color: positive ? '#3b6d11' : '#a32d2d', fontWeight: 500 }}>
                    {roiLabel(row.roi)}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-[var(--color-text-muted)]">
        Flat $100/bet. Vegas favorite and underdog are both negative due to the sportsbook vig —
        every line is shaded to give the house edge, so blindly betting either side loses regardless
        of win rate. Faded rows: n &lt; 50, treat as early signal only.
      </p>
    </div>
  )
}
