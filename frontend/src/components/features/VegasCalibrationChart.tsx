import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { VegasCalibrationRow } from '@t/api'

interface Props {
  data: VegasCalibrationRow[]
}

interface TooltipPayload {
  payload: VegasCalibrationRow & { implied_label: string }
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm shadow">
      <p className="font-semibold">{d.bucket}</p>
      <p className="text-[var(--color-text-muted)]">Avg implied: {(d.avg_implied_prob * 100).toFixed(1)}%</p>
      <p>
        Actual win rate:{' '}
        <span className="font-mono font-semibold">{(d.actual_win_rate * 100).toFixed(1)}%</span>
      </p>
      <p className="text-[var(--color-text-muted)]">
        {d.wins}/{d.fights} fights
      </p>
    </div>
  )
}

export function VegasCalibrationChart({ data }: Props) {
  const chartData = [...data]
    .sort((a, b) => a.bucket_order - b.bucket_order)
    .map((d) => ({
      ...d,
      actual_pct: +(d.actual_win_rate * 100).toFixed(1),
      implied_pct: +(d.avg_implied_prob * 100).toFixed(1),
    }))

  return (
    <div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
          <XAxis
            dataKey="bucket"
            tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[40, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--color-border)', opacity: 0.4 }} />
          <ReferenceLine
            y={chartData.map((d) => d.implied_pct)[0] ?? 55}
            strokeDasharray="0"
            stroke="transparent"
          />
          {/* Perfect calibration reference line — drawn per bucket as a separate shape */}
          <Bar dataKey="actual_pct" name="Actual win rate" radius={[3, 3, 0, 0]} maxBarSize={64}>
            {chartData.map((entry) => (
              <Cell
                key={entry.bucket}
                fill={entry.actual_pct >= entry.implied_pct ? '#10b981' : '#e63946'}
              />
            ))}
          </Bar>
          {/* Reference: Vegas implied prob average per bucket */}
          <ReferenceLine
            y={55}
            stroke="var(--color-text-muted)"
            strokeDasharray="4 2"
            label={{ value: 'implied', fill: 'var(--color-text-muted)', fontSize: 11, position: 'insideTopRight' }}
          />
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-[var(--color-text-muted)]">
        {chartData.map((d) => (
          <span key={d.bucket}>
            <span className="font-semibold text-[var(--color-text)]">{d.bucket}</span>:{' '}
            implied {d.implied_pct}% → actual {d.actual_pct}% ({d.fights} fights)
          </span>
        ))}
      </div>
    </div>
  )
}
