import type { StrategyRoiRow } from '@t/api'

interface Props {
  strategies: StrategyRoiRow[]
}

function roiLabel(roi: number) {
  const sign = roi >= 0 ? '+' : ''
  return `${sign}${(roi * 100).toFixed(1)}%`
}

export function StrategyTicker({ strategies }: Props) {
  const sorted = [...strategies].sort((a, b) => b.roi - a.roi)

  const items = sorted.map((s) => ({
    name: s.strategy_name,
    roi: s.roi,
    bets: s.bets,
    wins: s.wins,
    roiLabel: roiLabel(s.roi),
  }))

  // Duplicate for seamless loop
  const doubled = [...items, ...items]

  return (
    <div className="overflow-hidden border-b border-t border-[var(--color-border)] py-1.5 text-xs">
      <div
        className="flex gap-8 whitespace-nowrap"
        style={{
          animation: 'ticker 28s linear infinite',
          width: 'max-content',
        }}
        onMouseEnter={(e) =>
          ((e.currentTarget as HTMLElement).style.animationPlayState = 'paused')
        }
        onMouseLeave={(e) =>
          ((e.currentTarget as HTMLElement).style.animationPlayState = 'running')
        }
      >
        {doubled.map((item, i) => (
          <span key={i} className="flex items-center gap-2">
            <span className="text-[var(--color-text-muted)]">{item.name}</span>
            <span
              className={`font-mono font-semibold tabular-nums ${item.roi >= 0 ? 'text-[var(--color-success-light)] dark:text-[var(--color-success)]' : 'text-[var(--color-error-light)] dark:text-[var(--color-error)]'}`}
            >
              {item.roiLabel}
            </span>
            <span className="text-[var(--color-text-muted)]">
              {item.bets} bets · {item.wins} wins
            </span>
            <span className="text-[var(--color-border)]">·</span>
          </span>
        ))}
      </div>
      <style>{`@keyframes ticker { 0% { transform: translateX(0) } 100% { transform: translateX(-50%) } }`}</style>
    </div>
  )
}
