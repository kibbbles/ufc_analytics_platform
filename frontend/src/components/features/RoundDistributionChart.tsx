import type { ChartTooltipProps } from '@t/chart'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { RoundDistributionPoint } from '@t/api'

// Round number is ordinal: earlier rounds finish more urgently. Encode that as a
// single-hue intensity ramp keyed to the primary chart colour, strongest for R1.
// Mix toward white (opaque) rather than transparent so the faint rounds fade to
// pale pink and stay legible on BOTH the light and dark backgrounds - mixing
// toward transparent blends into the page and turns muddy on the dark theme.
const ROUND_COLORS = {
  r1:     'color-mix(in srgb, var(--color-chart-1) 100%, white)',
  r2:     'color-mix(in srgb, var(--color-chart-1) 75%, white)',
  r3:     'color-mix(in srgb, var(--color-chart-1) 50%, white)',
  r4plus: 'color-mix(in srgb, var(--color-chart-1) 30%, white)',
}

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload as RoundDistributionPoint | undefined
  if (!d) return null
  return (
    <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-xs shadow-lg">
      <p className="font-bold mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.fill }}>
          {p.name}: {(Number(p.value) * 100).toFixed(1)}%
        </p>
      ))}
      <p className="mt-1 text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
        {d.total_finishes} finishes{d.is_partial_year ? ' · partial year' : ''}
      </p>
    </div>
  )
}

interface Props {
  data: RoundDistributionPoint[]
}

export default function RoundDistributionChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="var(--color-border-light)"
          className="dark:[stroke:var(--color-border)]"
          vertical={false}
        />
        <XAxis
          dataKey="year"
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={false}
          domain={[0, 1]}
          width={36}
        />
        <Tooltip content={<ChartTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
          formatter={(value: string) => (
            <span className="text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
              {value}
            </span>
          )}
        />
        <Bar dataKey="r1_pct"     name="Round 1" stackId="a" fill={ROUND_COLORS.r1}     isAnimationActive={false} />
        <Bar dataKey="r2_pct"     name="Round 2" stackId="a" fill={ROUND_COLORS.r2}     isAnimationActive={false} />
        <Bar dataKey="r3_pct"     name="Round 3" stackId="a" fill={ROUND_COLORS.r3}     isAnimationActive={false} />
        <Bar dataKey="r4plus_pct" name="Round 4/5" stackId="a" fill={ROUND_COLORS.r4plus} isAnimationActive={false} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
