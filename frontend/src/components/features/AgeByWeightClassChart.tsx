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
import type { AgeByWeightClassPoint } from '@t/api'

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

// ── Time-series view (single weight class selected) ───────────────────────────

function TimeSeriesView({ data, weightClass }: { data: AgeByWeightClassPoint[]; weightClass: string }) {
  const filtered = data
    .filter((d) => d.weight_class === weightClass)
    .sort((a, b) => a.year - b.year)

  if (!filtered.length) {
    return (
      <p className="text-sm text-[var(--color-text-muted)]">
        No age data available for {weightClass}.
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
      <ResponsiveContainer width="100%" height={260}>
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
            tickFormatter={(v: number) => String(Math.round(v))}
            allowDecimals={false}
            tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
            tickLine={false}
            axisLine={false}
            domain={['auto', 'auto']}
            width={32}
          />
          <Tooltip
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            content={((props: any) => {
              if (!props.active || !props.payload?.length) return null
              const d = props.payload[0]?.payload as AgeByWeightClassPoint
              return (
                <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-xs shadow-lg">
                  <p className="font-bold mb-1">{d.year}</p>
                  <p style={{ color: '#e63946' }}>Avg age: {Math.round(d.avg_age)}</p>
                  <p className="mt-1 text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                    {d.fighter_count} fighters
                  </p>
                </div>
              )
            }) as any}
          />
          <Line
            dataKey="avg_age"
            name="Avg age"
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

function SnapshotView({ data }: { data: AgeByWeightClassPoint[] }) {
  const latestByWc: Record<string, AgeByWeightClassPoint> = {}
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
      avg_age: latestByWc[wc].avg_age,
      year: latestByWc[wc].year,
      fighter_count: latestByWc[wc].fighter_count,
    }))
    .reverse()

  return (
    <ResponsiveContainer width="100%" height={Math.max(260, chartData.length * 26)}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 4, right: 48, left: 0, bottom: 4 }}
        barCategoryGap="35%"
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="var(--color-border-light)"
          className="dark:[stroke:var(--color-border)]"
          horizontal={false}
        />
        <XAxis
          type="number"
          domain={[25, 35]}
          tickFormatter={(v: number) => `${v}`}
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={false}
          label={{ value: 'avg age (years)', position: 'insideBottomRight', offset: -4, fontSize: 10, fill: 'var(--color-text-muted)' }}
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
          content={((props: any) => {
            if (!props.active || !props.payload?.length) return null
            const d = props.payload[0]?.payload
            return (
              <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-xs shadow-lg">
                <p className="font-bold mb-1">{d.full_name}</p>
                <p style={{ color: '#e63946' }}>Avg age: {d.avg_age.toFixed(1)}</p>
                <p className="mt-1 text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                  {d.fighter_count} fighters · latest data: {d.year}
                </p>
              </div>
            )
          }) as any}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
          formatter={(value: string) => (
            <span className="text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
              {value}
            </span>
          )}
        />
        <Bar dataKey="avg_age" name="Avg age" fill="#e63946" radius={[0, 2, 2, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Public component ──────────────────────────────────────────────────────────

interface Props {
  data: AgeByWeightClassPoint[]
  weightClass?: string | null
}

export default function AgeByWeightClassChart({ data, weightClass }: Props) {
  if (!data.length) return null
  if (weightClass) return <TimeSeriesView data={data} weightClass={weightClass} />
  return <SnapshotView data={data} />
}
