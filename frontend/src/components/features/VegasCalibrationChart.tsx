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
import type { VegasCalibrationRow } from '@t/api'
import { calibrationVerdict } from '@utils/calibration'

interface Props {
  data: VegasCalibrationRow[]
}

/** What one bucket's implied-vs-actual gap says, judged against binomial sampling noise. */
function bucketReading(implied: number, actual: number, fights: number): string {
  switch (calibrationVerdict(implied, actual, fights)) {
    case 'under':
      return 'Favorites here win clearly more often than Vegas implies: the market underrates them.'
    case 'over':
      return 'Favorites here win clearly less often than Vegas implies: the market overrates them.'
    default:
      return 'The gap is within sampling noise for this many fights, so Vegas looks calibrated here.'
  }
}

export function VegasCalibrationChart({ data }: Props) {
  const chartData = [...data]
    .sort((a, b) => a.bucket_order - b.bucket_order)
    .map((d) => ({
      ...d,
      'Vegas implied': +(d.avg_implied_prob * 100).toFixed(1),
      'Actual win rate': +(d.actual_win_rate * 100).toFixed(1),
    }))

  const mispriced = chartData.filter(
    (r) => calibrationVerdict(r.avg_implied_prob, r.actual_win_rate, r.fights) !== 'noise',
  )

  return (
    <div className="space-y-6">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }} barCategoryGap="28%">
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
          <XAxis
            dataKey="bucket"
            tick={{ fill: 'var(--color-chart-axis)', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[40, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fill: 'var(--color-chart-axis)', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <Tooltip
            formatter={(value, name) => [`${value}%`, String(name)]}
            contentStyle={{
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: 'var(--color-chart-axis)' }} />
          <Bar dataKey="Vegas implied" fill="var(--color-chart-6)" fillOpacity={0.5} radius={[3, 3, 0, 0]} maxBarSize={40} />
          <Bar dataKey="Actual win rate" fill="var(--color-chart-2)" radius={[3, 3, 0, 0]} maxBarSize={40} />
        </BarChart>
      </ResponsiveContainer>

      <div className="space-y-3">
        {chartData.map((row) => (
          <div key={row.bucket} className="text-sm">
            <span className="font-semibold">{row.bucket} bucket</span>
            <span className="ml-2 font-mono text-xs text-[var(--color-text-muted)]">
              implied {row['Vegas implied']}% → actual {row['Actual win rate']}% ({row.fights} fights)
            </span>
            <p className="mt-0.5 text-[var(--color-text-muted)]">
              {bucketReading(row.avg_implied_prob, row.actual_win_rate, row.fights)}
            </p>
          </div>
        ))}
        <p className="border-t border-[var(--color-border)] pt-3 text-sm">
          <strong>Bottom line:</strong>{' '}
          <span className="text-[var(--color-text-muted)]">
            {mispriced.length === 0
              ? 'Every bucket is within sampling noise of its implied probability, so this data shows no systematic Vegas mispricing. Any edge has to come from the model picking the right fights to disagree on, not from a market-wide bias.'
              : `Vegas is clearly off only in the ${mispriced.map((r) => r.bucket).join(' and ')} ${mispriced.length === 1 ? 'bucket' : 'buckets'}; everywhere else the gap is within sampling noise.`}
          </span>
        </p>
      </div>
    </div>
  )
}
