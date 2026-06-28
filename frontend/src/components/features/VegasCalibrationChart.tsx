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

interface Props {
  data: VegasCalibrationRow[]
}

const CALLOUTS = [
  {
    bucket: '50–60%',
    text: 'Vegas implied ~55.9%, actual 61.7%. These modest favorites are consistently underestimated — this slight miscalibration is where the 5–15% edge filter finds its signal.',
  },
  {
    bucket: '60–70%',
    text: 'Vegas implied ~65.3%, actual 66.7%. Well-calibrated. No systematic edge here.',
  },
  {
    bucket: '70–80%',
    text: 'Vegas accurate or slightly over-estimates. Betting blindly loses to vig.',
  },
  {
    bucket: '80%+',
    text: 'Heavy favorites. Vegas is right. The model is rarely wrong here — but when it disagrees, results are very bad (−61.6% ROI).',
  },
]

export function VegasCalibrationChart({ data }: Props) {
  const chartData = [...data]
    .sort((a, b) => a.bucket_order - b.bucket_order)
    .map((d) => ({
      ...d,
      'Vegas implied': +(d.avg_implied_prob * 100).toFixed(1),
      'Actual win rate': +(d.actual_win_rate * 100).toFixed(1),
    }))

  return (
    <div className="space-y-6">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }} barCategoryGap="28%">
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
          <XAxis
            dataKey="bucket"
            tick={{ fill: '#898781', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[40, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fill: '#898781', fontSize: 12 }}
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
          <Legend wrapperStyle={{ fontSize: 12, color: '#898781' }} />
          <Bar dataKey="Vegas implied" fill="#898781" fillOpacity={0.5} radius={[3, 3, 0, 0]} maxBarSize={40} />
          <Bar dataKey="Actual win rate" fill="#2a78d6" radius={[3, 3, 0, 0]} maxBarSize={40} />
        </BarChart>
      </ResponsiveContainer>

      <div className="space-y-3">
        {CALLOUTS.map((c) => {
          const row = chartData.find((d) => d.bucket === c.bucket)
          return (
            <div key={c.bucket} className="text-sm">
              <span className="font-semibold">{c.bucket} bucket</span>
              {row && (
                <span className="ml-2 font-mono text-xs text-[var(--color-text-muted)]">
                  implied {row['Vegas implied']}% → actual {row['Actual win rate']}% ({row.fights} fights)
                </span>
              )}
              <p className="mt-0.5 text-[var(--color-text-muted)]">{c.text}</p>
            </div>
          )
        })}
        <p className="border-t border-[var(--color-border)] pt-3 text-sm">
          <strong>Bottom line:</strong>{' '}
          <span className="text-[var(--color-text-muted)]">
            Vegas is mostly right. The only exploitable gap in this data is in the 50–60% bucket,
            and only when the model agrees with the direction but is slightly more confident than
            Vegas (5–15% edge).
          </span>
        </p>
      </div>
    </div>
  )
}
