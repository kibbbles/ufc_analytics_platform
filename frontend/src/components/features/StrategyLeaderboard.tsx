import type { StrategyRoiRow } from '@t/api'

interface Props {
  strategies: StrategyRoiRow[]
}

function pnlLabel(pnl: number): string {
  const sign = pnl >= 0 ? '+' : ''
  return `${sign}$${pnl.toFixed(2)}`
}

function roiLabel(roi: number): string {
  const sign = roi >= 0 ? '+' : ''
  return `${sign}${(roi * 100).toFixed(1)}%`
}

export function StrategyLeaderboard({ strategies }: Props) {
  const sorted = [...strategies].sort((a, b) => b.roi - a.roi)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--color-border)]">
            <th className="py-2 pr-4 text-left font-medium text-[var(--color-text-muted)]">Strategy</th>
            <th className="py-2 px-3 text-right font-medium text-[var(--color-text-muted)]">Bets</th>
            <th className="py-2 px-3 text-right font-medium text-[var(--color-text-muted)]">Wins</th>
            <th className="py-2 px-3 text-right font-medium text-[var(--color-text-muted)]">P&L / bet</th>
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
                className={`border-b border-[var(--color-border)] transition-opacity ${lowSample ? 'opacity-40' : ''}`}
              >
                <td className="py-3 pr-4 font-medium">
                  {row.strategy_name}
                  {lowSample && (
                    <span className="ml-2 text-xs text-[var(--color-text-muted)]">
                      (n={row.bets}, low sample)
                    </span>
                  )}
                </td>
                <td className="py-3 px-3 text-right font-mono tabular-nums">{row.bets}</td>
                <td className="py-3 px-3 text-right font-mono tabular-nums">{row.wins}</td>
                <td className="py-3 px-3 text-right font-mono tabular-nums">
                  <span className={positive ? 'text-emerald-500' : 'text-[var(--color-text-muted)]'}>
                    {pnlLabel(row.pnl)}
                  </span>
                </td>
                <td className="py-3 pl-3 text-right font-mono tabular-nums font-semibold">
                  <span className={positive ? 'text-emerald-500' : 'text-red-400'}>
                    {roiLabel(row.roi)}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-[var(--color-text-muted)]">
        Rows faded at n&nbsp;&lt;&nbsp;50. Flat $1 unit per bet. P&amp;L = profit/loss in units.
      </p>
    </div>
  )
}
