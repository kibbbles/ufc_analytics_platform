import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { StyleStatsByWeightClassPoint } from '@t/api'

interface PanelProps {
  data: StyleStatsByWeightClassPoint[]
  dataKey: keyof StyleStatsByWeightClassPoint
  label: string
  formatValue: (v: number) => string
  color: string
}

function MetricPanel({ data, dataKey, label, formatValue, color }: PanelProps) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
        {label}
      </p>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--color-border-light)"
            className="dark:[stroke:var(--color-border)]"
            vertical={false}
          />
          <XAxis
            dataKey="year"
            tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={formatValue}
            tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
            tickLine={false}
            axisLine={false}
            width={36}
            domain={['auto', 'auto']}
          />
          <Tooltip
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            content={((props: any) => {
              if (!props.active || !props.payload?.length) return null
              const d = props.payload[0]?.payload as StyleStatsByWeightClassPoint
              return (
                <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-xs shadow-lg">
                  <p className="font-bold">{d.year}</p>
                  <p style={{ color }}>{label}: {formatValue(d[dataKey] as number)}</p>
                  <p className="mt-1 text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                    {d.fight_count} fights
                  </p>
                </div>
              )
            }) as any}
          />
          <Line
            dataKey={dataKey as string}
            stroke={color}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

interface Props {
  data: StyleStatsByWeightClassPoint[]
  weightClass: string
}

export default function FighterStatsTimeSeriesChart({ data, weightClass }: Props) {
  const filtered = data
    .filter((d) => d.weight_class === weightClass)
    .sort((a, b) => a.year - b.year)

  if (!filtered.length) {
    return (
      <p className="text-sm text-[var(--color-text-muted)]">
        No detailed stats available for {weightClass} (fight_stats data starts 2015+).
      </p>
    )
  }

  const panels: Omit<PanelProps, 'data'>[] = [
    {
      dataKey: 'avg_slpm',
      label: 'SLpM',
      formatValue: (v) => v.toFixed(1),
      color: '#e63946',
    },
    {
      dataKey: 'avg_str_acc',
      label: 'Str. Acc.',
      formatValue: (v) => `${(v * 100).toFixed(0)}%`,
      color: '#c05c63',
    },
    {
      dataKey: 'avg_td_per_fight',
      label: 'TD per fight',
      formatValue: (v) => v.toFixed(1),
      color: '#4361ee',
    },
    {
      dataKey: 'avg_td_acc',
      label: 'TD Acc.',
      formatValue: (v) => `${(v * 100).toFixed(0)}%`,
      color: '#6b82f0',
    },
    {
      dataKey: 'avg_ctrl_seconds',
      label: 'Ctrl time (s)',
      formatValue: (v) => `${Math.round(v)}s`,
      color: '#2a9d8f',
    },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-6">
      {panels.map((p) => (
        <MetricPanel key={String(p.dataKey)} data={filtered} {...p} />
      ))}
    </div>
  )
}
