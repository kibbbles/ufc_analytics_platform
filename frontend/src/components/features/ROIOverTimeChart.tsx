import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import type { RoiOverTimeRow } from '@t/api'

interface Props {
  data: RoiOverTimeRow[]
}

function formatDate(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: { payload: RoiOverTimeRow; value: number }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  const sign = d.cumulative_pnl >= 0 ? '+' : ''
  return (
    <div className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm shadow max-w-56">
      <p className="font-semibold truncate">{d.event_name ?? label}</p>
      <p className="text-[var(--color-text-muted)]">{formatDate(d.event_date)}</p>
      <p>
        Cumulative P&L:{' '}
        <span
          className={`font-mono font-semibold ${d.cumulative_pnl >= 0 ? 'text-emerald-500' : 'text-red-400'}`}
        >
          {sign}${d.cumulative_pnl.toFixed(2)}
        </span>
      </p>
      <p className="text-[var(--color-text-muted)]">
        This event: {d.bets} bets, {d.pnl >= 0 ? '+' : ''}
        ${d.pnl.toFixed(2)} P&L
      </p>
      <p className="text-[var(--color-text-muted)]">Total bets so far: {d.cumulative_bets}</p>
    </div>
  )
}

export function ROIOverTimeChart({ data }: Props) {
  const chartData = data.map((d) => ({
    ...d,
    date_label: formatDate(d.event_date),
  }))

  const finalPnl = data.at(-1)?.cumulative_pnl ?? 0
  const positive = finalPnl >= 0

  return (
    <div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
          <XAxis
            dataKey="date_label"
            tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={(v) => `$${v}`}
            tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={52}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="var(--color-border)" strokeWidth={1.5} />
          <Line
            type="monotone"
            dataKey="cumulative_pnl"
            stroke={positive ? '#10b981' : '#e63946'}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: positive ? '#10b981' : '#e63946' }}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-2 text-xs text-[var(--color-text-muted)]">
        Model-pick strategy only. Flat $1 unit per bet. Vegas odds fights only ({data.length}{' '}
        events).
      </p>
    </div>
  )
}
