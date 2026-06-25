import { useNavigate } from 'react-router-dom'
import type { UpsetRateRow } from '@t/api'

interface Props {
  data: UpsetRateRow[]
}

export function UpsetRateChart({ data }: Props) {
  const navigate = useNavigate()
  const sorted = [...data].sort((a, b) => b.upset_rate - a.upset_rate)
  const maxRate = Math.max(...sorted.map((d) => d.upset_rate), 0.01)

  return (
    <div className="space-y-2">
      {sorted.map((row) => {
        const pct = (row.upset_rate / maxRate) * 100
        const ratePct = (row.upset_rate * 100).toFixed(1)

        return (
          <button
            key={row.weight_class}
            onClick={() =>
              navigate(
                `/past-predictions?upset=true&weight_class=${encodeURIComponent(row.weight_class)}`,
              )
            }
            className="group w-full text-left"
            title={`View ${row.weight_class} upsets`}
          >
            <div className="flex items-center gap-3">
              <span className="w-40 shrink-0 text-right text-sm text-[var(--color-text-muted)] group-hover:text-[var(--color-text)] transition-colors">
                {row.weight_class}
              </span>
              <div className="relative flex-1 h-6 rounded overflow-hidden bg-[var(--color-border)]">
                <div
                  className="h-full bg-[var(--color-accent)] opacity-70 group-hover:opacity-100 transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <div className="w-28 shrink-0 flex items-center gap-2">
                <span className="font-mono tabular-nums text-sm font-semibold">{ratePct}%</span>
                <span className="text-xs text-[var(--color-text-muted)]">
                  {row.upset_count}/{row.total_fights}
                </span>
              </div>
            </div>
          </button>
        )
      })}
      <p className="pt-2 text-xs text-[var(--color-text-muted)]">
        Click any bar to see those upsets in Past Predictions.
        <br />
        "Upset" = model was wrong AND conviction ≥ 30%. Not the same as a Vegas underdog winning.
      </p>
    </div>
  )
}
