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
import type { PhysicalStatPoint } from '@t/api'

// Display order: heaviest first so bars read top-to-bottom in a familiar weight-class hierarchy
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

interface Props {
  data: PhysicalStatPoint[]
}

export default function PhysicalStatsChart({ data }: Props) {
  if (!data.length) return null

  // Use the most recent year available per weight class
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
      avg_reach: latestByWc[wc].avg_reach_inches,
      year: latestByWc[wc].year,
      fighter_count: latestByWc[wc].fighter_count,
    }))
    .reverse() // lightest at top in a horizontal chart

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
        />
        <Tooltip
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          content={((props: any) => {
            if (!props.active || !props.payload?.length) return null
            const d = props.payload[0]?.payload
            return (
              <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-xs shadow-lg">
                <p className="font-bold mb-1">{d.full_name}</p>
                <p style={{ color: '#4361ee' }}>Avg height: {d.avg_height}"</p>
                <p style={{ color: '#e63946' }}>Avg reach: {d.avg_reach}"</p>
                <p className="mt-1 text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                  {d.fighter_count} fighters · most recent data: {d.year}
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
        <Bar dataKey="avg_height" name="Avg height (in)" fill="#4361ee" radius={[0, 2, 2, 0]} isAnimationActive={false} />
        <Bar dataKey="avg_reach"  name="Avg reach (in)"  fill="#e63946" radius={[0, 2, 2, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}
