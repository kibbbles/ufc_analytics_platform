import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import type { StyleEvolutionPoint } from '@t/api'

// ---------------------------------------------------------------------------
// Config — change colors, labels, and which lines are visible here
// ---------------------------------------------------------------------------

export interface FinishRateChartConfig {
  showKoTko?: boolean
  showSubmission?: boolean
  showDecision?: boolean
  showFinishRate?: boolean   // combined KO/TKO + Sub line
  colorKoTko?: string
  colorSubmission?: string
  colorDecision?: string
  colorFinishRate?: string
  showEraAnnotations?: boolean
}

const DEFAULT_CONFIG: Required<FinishRateChartConfig> = {
  showKoTko: false,
  showSubmission: false,
  showDecision: false,
  showFinishRate: true,      // default: show combined Finish vs Decision
  colorKoTko: '#e63946',
  colorSubmission: '#4361ee',
  colorDecision: 'var(--color-text-muted)',
  colorFinishRate: '#e63946',
  showEraAnnotations: true,
}

const ERA_ANNOTATIONS = [
  { year: 2001, label: 'Zuffa era' },
  { year: 2015, label: 'USADA begins' },
]

// ---------------------------------------------------------------------------
// Tooltip
// ---------------------------------------------------------------------------

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload as StyleEvolutionPoint | undefined
  if (!d) return null

  return (
    <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-xs shadow-lg">
      <p className="font-bold mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {(p.value * 100).toFixed(1)}%
        </p>
      ))}
      <p className="mt-1 text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
        {d.total_fights} fights
        {d.is_partial_year ? ' · partial year' : ''}
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// FinishRateChart
// ---------------------------------------------------------------------------

interface Props {
  data: StyleEvolutionPoint[]
  config?: FinishRateChartConfig
}

export default function FinishRateChart({ data, config = {} }: Props) {
  const cfg = { ...DEFAULT_CONFIG, ...config }

  // Partial year rendered as dashed at the end
  const chartData = data.map((d) => ({
    ...d,
    finish_rate_solid: d.is_partial_year ? null : d.finish_rate,
    finish_rate_partial: d.is_partial_year ? d.finish_rate : null,
    decision_rate_solid: d.is_partial_year ? null : d.decision_rate,
    decision_rate_partial: d.is_partial_year ? d.decision_rate : null,
  }))

  // Carry last solid point into partial so the line connects
  const lastSolidIdx = chartData.findLastIndex((d) => !d.is_partial_year)
  if (lastSolidIdx >= 0 && lastSolidIdx + 1 < chartData.length) {
    chartData[lastSolidIdx + 1].finish_rate_partial = chartData[lastSolidIdx].finish_rate
    chartData[lastSolidIdx + 1].decision_rate_partial = chartData[lastSolidIdx].decision_rate
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
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
          tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={false}
          domain={[0, 1]}
          width={36}
        />
        <Tooltip content={<ChartTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
          formatter={(value) => (
            <span className="text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
              {value}
            </span>
          )}
        />

        {cfg.showEraAnnotations &&
          ERA_ANNOTATIONS.map(({ year, label }) => (
            <ReferenceLine
              key={year}
              x={year}
              stroke="var(--color-border)"
              strokeDasharray="4 2"
              label={{
                value: label,
                position: 'insideTopRight',
                fontSize: 10,
                fill: 'var(--color-text-muted)',
              }}
            />
          ))}

        {/* Combined finish rate */}
        {cfg.showFinishRate && (
          <>
            <Line
              dataKey="finish_rate_solid"
              name="Finish rate"
              stroke={cfg.colorFinishRate}
              strokeWidth={2.5}
              dot={false}
              connectNulls={false}
              legendType="line"
            />
            <Line
              dataKey="finish_rate_partial"
              name=" "
              stroke={cfg.colorFinishRate}
              strokeWidth={2.5}
              strokeDasharray="5 4"
              dot={false}
              connectNulls={false}
              legendType="none"
            />
          </>
        )}

        {/* Decision rate — always shown alongside finish rate for context */}
        {(cfg.showFinishRate || cfg.showDecision) && (
          <>
            <Line
              dataKey="decision_rate_solid"
              name="Decision rate"
              stroke={cfg.colorDecision}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              legendType="line"
            />
            <Line
              dataKey="decision_rate_partial"
              name=" "
              stroke={cfg.colorDecision}
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={false}
              connectNulls={false}
              legendType="none"
            />
          </>
        )}

        {/* Individual breakdown lines */}
        {cfg.showKoTko && (
          <Line
            dataKey="ko_tko_rate"
            name="KO/TKO"
            stroke={cfg.colorKoTko}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        )}
        {cfg.showSubmission && (
          <Line
            dataKey="submission_rate"
            name="Submission"
            stroke={cfg.colorSubmission}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  )
}
