import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { PhysicalStatPoint } from '@t/api'

// Heaviest → lightest so bars read top-to-bottom in a familiar weight-class hierarchy
const WC_ORDER = [
  'Heavyweight',
  'Light Heavyweight',
  'Middleweight',
  'Welterweight',
  'Lightweight',
  'Featherweight',
  'Bantamweight',
  'Flyweight',
  'Strawweight',
  "Women's Featherweight",
  "Women's Bantamweight",
  "Women's Flyweight",
  "Women's Strawweight",
]

const WC_SHORT: Record<string, string> = {
  'Heavyweight':            'HW',
  'Light Heavyweight':      'LHW',
  'Middleweight':           'MW',
  'Welterweight':           'WW',
  'Lightweight':            'LW',
  'Featherweight':          'FW',
  'Bantamweight':           'BW',
  'Flyweight':              'FLY',
  'Strawweight':            'STR',
  "Women's Featherweight":  'W-FW',
  "Women's Bantamweight":   'W-BW',
  "Women's Flyweight":      'W-FLY',
  "Women's Strawweight":    'W-STR',
}

// ── Shared tooltip ────────────────────────────────────────────────────────────

function PhysicalTooltip({ active, payload, label, isTimeSeries }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-xs shadow-lg">
      <p className="font-bold mb-1">
        {isTimeSeries ? label : payload[0]?.payload?.full_name ?? label}
      </p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color ?? p.fill }}>
          {p.name}: {typeof p.value === 'number' ? `${p.value.toFixed(1)}"` : p.value}
        </p>
      ))}
      {!isTimeSeries && payload[0]?.payload?.fighter_count != null && (
        <p className="mt-1 text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          {payload[0].payload.fighter_count} fighters · latest data: {payload[0].payload.year}
        </p>
      )}
      {isTimeSeries && payload[0]?.payload?.fighter_count != null && (
        <p className="mt-1 text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          {payload[0].payload.fighter_count} fighters
        </p>
      )}
    </div>
  )
}

// ── Time-series view (single weight class selected) ───────────────────────────

function TimeSeriesView({ data, weightClass }: { data: PhysicalStatPoint[]; weightClass: string }) {
  const filtered = data
    .filter((d) => d.weight_class === weightClass)
    .sort((a, b) => a.year - b.year)

  if (!filtered.length) {
    return (
      <p className="text-sm text-[var(--color-text-muted)]">
        No physical stats available for {weightClass}.
      </p>
    )
  }

  const currentYear = new Date().getFullYear()
  const hasCurrentYear = filtered.some((d) => d.year === currentYear)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const partialDot = (color: string) => (props: any) => {
    if (props.payload?.year === currentYear) {
      return <circle key={props.index} cx={props.cx} cy={props.cy} r={3} fill="none" stroke={color} strokeWidth={2} />
    }
    return <g key={props.index} />
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={filtered} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
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
            tickFormatter={(v: number) => `${v}"`}
            tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
            tickLine={false}
            axisLine={false}
            domain={['auto', 'auto']}
            allowDecimals={false}
            width={36}
          />
          <Tooltip
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            content={((props: any) => <PhysicalTooltip {...props} isTimeSeries />) as any}
          />
          <Legend
            wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
            formatter={(value: string) => (
              <span className="text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
                {value}
              </span>
            )}
          />
          <Line
            dataKey="avg_height_inches"
            name="Avg height (in)"
            stroke="#4361ee"
            strokeWidth={2}
            dot={partialDot('#4361ee')}
            connectNulls
          />
          <Line
            dataKey="avg_reach_inches"
            name="Avg reach (in)"
            stroke="#e63946"
            strokeWidth={2}
            dot={partialDot('#e63946')}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
      {hasCurrentYear && (
        <p className="text-[11px] text-[var(--color-text-muted)] mt-1">
          ○ Open circle = {currentYear} (partial year, fights still ongoing).
        </p>
      )}
    </div>
  )
}

// ── Snapshot view (all weight classes, most recent year) ──────────────────────

function SnapshotView({ data }: { data: PhysicalStatPoint[] }) {
  const latestByWc: Record<string, PhysicalStatPoint> = {}
  for (const d of data) {
    if (!latestByWc[d.weight_class] || d.year > latestByWc[d.weight_class].year) {
      latestByWc[d.weight_class] = d
    }
  }

  const chartData = WC_ORDER
    .filter((wc) => latestByWc[wc])
    .map((wc) => ({
      wc: WC_SHORT[wc] ?? wc,
      full_name: wc,
      avg_height: latestByWc[wc].avg_height_inches,
      avg_reach:  latestByWc[wc].avg_reach_inches,
      year: latestByWc[wc].year,
      fighter_count: latestByWc[wc].fighter_count,
    }))
    .reverse() // lightest at top in horizontal chart

  return (
    <ResponsiveContainer width="100%" height={Math.max(280, chartData.length * 28)}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 4, right: 48, left: 0, bottom: 4 }}
        barCategoryGap="30%"
        barGap={2}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="var(--color-border-light)"
          className="dark:[stroke:var(--color-border)]"
          horizontal={false}
        />
        <XAxis
          type="number"
          domain={[60, 80]}
          tickFormatter={(v: number) => `${v}"`}
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          type="category"
          dataKey="wc"
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={false}
          width={40}
          interval={0}
        />
        <Tooltip
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          content={((props: any) => <PhysicalTooltip {...props} isTimeSeries={false} />) as any}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
          formatter={(value: string) => (
            <span className="text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
              {value}
            </span>
          )}
        />
        <Bar dataKey="avg_height" name="Avg height (in)" fill="#4361ee" radius={[0, 2, 2, 0]} isAnimationActive={false} />
        <Bar dataKey="avg_reach"  name="Avg reach (in)"  fill="#e63946" radius={[0, 2, 2, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Public component ──────────────────────────────────────────────────────────

interface Props {
  data: PhysicalStatPoint[]
  weightClass?: string | null
}

export default function PhysicalStatsChart({ data, weightClass }: Props) {
  if (!data.length) return null

  if (weightClass) {
    return <TimeSeriesView data={data} weightClass={weightClass} />
  }
  return <SnapshotView data={data} />
}
