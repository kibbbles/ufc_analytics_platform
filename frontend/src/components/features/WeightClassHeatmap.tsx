import { Fragment } from 'react'
import type { WeightClassYearPoint } from '@t/api'

// Heaviest to lightest — rows rendered top-to-bottom in this order
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
  data: WeightClassYearPoint[]
}

export default function WeightClassHeatmap({ data }: Props) {
  if (!data.length) return null

  // Build lookup: [weight_class][year] → point
  const lookup: Record<string, Record<number, WeightClassYearPoint>> = {}
  for (const d of data) {
    if (!lookup[d.weight_class]) lookup[d.weight_class] = {}
    lookup[d.weight_class][d.year] = d
  }

  const years = [...new Set(data.map((d) => d.year))].sort()
  const weightClasses = WC_ORDER.filter((wc) => lookup[wc])

  // Normalise finish rate across whole dataset for color scale
  const allRates = data.map((d) => d.finish_rate)
  const minRate = Math.min(...allRates)
  const maxRate = Math.max(...allRates)

  const cellColor = (rate: number | undefined): string => {
    if (rate === undefined) return 'transparent'
    const t = maxRate === minRate ? 0.5 : (rate - minRate) / (maxRate - minRate)
    return `rgba(230, 57, 70, ${(0.08 + t * 0.82).toFixed(2)})`
  }

  // Show year label only every 5 years to avoid crowding
  const showYearLabel = (y: number) => y % 5 === 0

  return (
    <div className="overflow-x-auto -mx-1">
      <div
        className="grid text-[10px] min-w-max px-1"
        style={{ gridTemplateColumns: `56px repeat(${years.length}, 26px)` }}
      >
        {/* Year header — spacer for sticky label column */}
        <div className="sticky left-0 bg-[var(--color-bg-light)] dark:bg-[var(--color-bg)]" />
        {years.map((y) => (
          <div
            key={y}
            className="text-center text-[var(--color-text-muted)] pb-1 font-mono tabular-nums leading-none"
          >
            {showYearLabel(y) ? y : ''}
          </div>
        ))}

        {/* One row per weight class */}
        {weightClasses.map((wc) => (
          <Fragment key={wc}>
            <div className="text-right pr-2 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] leading-7 truncate sticky left-0 bg-[var(--color-bg-light)] dark:bg-[var(--color-bg)]">
              {WC_SHORT[wc] ?? wc}
            </div>
            {years.map((y) => {
              const cell = lookup[wc]?.[y]
              return (
                <div
                  key={y}
                  title={
                    cell
                      ? `${wc} ${y}: ${(cell.finish_rate * 100).toFixed(0)}% finish rate (${cell.total_fights} fights)`
                      : `${wc} ${y}: no data`
                  }
                  className="h-7 border border-[var(--color-surface-light)] dark:border-[var(--color-surface)]"
                  style={{ backgroundColor: cellColor(cell?.finish_rate) }}
                />
              )
            })}
          </Fragment>
        ))}
      </div>

      {/* Color scale legend */}
      <div className="flex items-center gap-2 mt-3 ml-14">
        <span className="text-[10px] text-[var(--color-text-muted)]">
          Lower finish rate
        </span>
        <div
          className="h-2.5 w-28 rounded"
          style={{
            background:
              'linear-gradient(to right, rgba(230,57,70,0.08), rgba(230,57,70,0.9))',
          }}
        />
        <span className="text-[10px] text-[var(--color-text-muted)]">
          Higher finish rate
        </span>
      </div>
    </div>
  )
}
