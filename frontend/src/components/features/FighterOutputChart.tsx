import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { TooltipProps } from 'recharts'
import type { FighterOutputPoint } from '@t/api'

// ---------------------------------------------------------------------------
// Config — change colors, labels, and which panels are visible here
// ---------------------------------------------------------------------------

export interface FighterOutputChartConfig {
  color?: string
  colorPartial?: string
}

const DEFAULT_CONFIG: Required<FighterOutputChartConfig> = {
  color: '#4361ee',
  colorPartial: '#4361ee80',
}

// ---------------------------------------------------------------------------
// Single metric panel
// ---------------------------------------------------------------------------

interface PanelProps {
  data: FighterOutputPoint[]
  dataKey: keyof FighterOutputPoint
  label: string
  formatValue: (v: number) => string
  color: string
  colorPartial: string
}

function MetricPanel({ data, dataKey, label, formatValue, color, colorPartial }: PanelProps) {
  const chartData = data.map((d) => ({
    ...d,
    value: d[dataKey] as number,
    fill: d.is_partial_year ? colorPartial : color,
  }))

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
        {label}
      </p>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
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
            width={32}
          />
          <Tooltip
            content={(props: TooltipProps<number, string>) => {
              if (!props.active || !props.payload?.length) return null
              const d = props.payload[0]?.payload as FighterOutputPoint & { value: number }
              return (
                <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-xs shadow-lg">
                  <p className="font-bold">{d.year}</p>
                  <p>{label}: {formatValue(d.value)}</p>
                  <p className="mt-1 text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                    {d.total_fights} fights{d.is_partial_year ? ' · partial year' : ''}
                  </p>
                </div>
              )
            }}
          />
          <Bar dataKey="value" radius={[2, 2, 0, 0]}>
            {chartData.map((entry, i) => (
              <rect key={i} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ---------------------------------------------------------------------------
// FighterOutputChart — three small panels side by side
// ---------------------------------------------------------------------------

interface Props {
  data: FighterOutputPoint[]
  config?: FighterOutputChartConfig
}

export default function FighterOutputChart({ data, config = {} }: Props) {
  const cfg = { ...DEFAULT_CONFIG, ...config }

  const panels: Omit<PanelProps, 'data' | 'color' | 'colorPartial'>[] = [
    {
      dataKey: 'avg_sig_str_per_fight',
      label: 'Avg sig strikes per fight',
      formatValue: (v) => v.toFixed(0),
    },
    {
      dataKey: 'avg_td_attempts_per_fight',
      label: 'Avg TD attempts per fight',
      formatValue: (v) => v.toFixed(1),
    },
    {
      dataKey: 'avg_ctrl_seconds_per_fight',
      label: 'Avg control time per fight',
      formatValue: (v) => `${Math.round(v)}s`,
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
      {panels.map((p) => (
        <MetricPanel
          key={String(p.dataKey)}
          data={data}
          color={cfg.color}
          colorPartial={cfg.colorPartial}
          {...p}
        />
      ))}
    </div>
  )
}
