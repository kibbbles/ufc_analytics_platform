import { Fragment } from 'react'
import type { FighterStatsByWeightClass } from '@t/api'

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

interface Column {
  key: keyof FighterStatsByWeightClass
  label: string
  format: (v: number) => string
  // Higher = better for a striker (heat direction: high = more intense color)
  // We always color high values more intensely regardless of whether "high" is "good"
}

const COLUMNS: Column[] = [
  { key: 'avg_slpm',    label: 'SLpM',      format: (v) => v.toFixed(2) },
  { key: 'avg_str_acc', label: 'Str. Acc.', format: (v) => `${(v * 100).toFixed(0)}%` },
  { key: 'avg_sapm',    label: 'SApM',      format: (v) => v.toFixed(2) },
  { key: 'avg_str_def', label: 'Str. Def.', format: (v) => `${(v * 100).toFixed(0)}%` },
  { key: 'avg_td_avg',  label: 'TD Avg.',   format: (v) => v.toFixed(2) },
  { key: 'avg_td_acc',  label: 'TD Acc.',   format: (v) => `${(v * 100).toFixed(0)}%` },
  { key: 'avg_td_def',  label: 'TD Def.',   format: (v) => `${(v * 100).toFixed(0)}%` },
  { key: 'avg_sub_avg', label: 'Sub. Avg.', format: (v) => v.toFixed(2) },
]

function cellColor(value: number, min: number, max: number): string {
  if (max === min) return 'transparent'
  const t = (value - min) / (max - min)
  return `rgba(230, 57, 70, ${(0.05 + t * 0.55).toFixed(2)})`
}

interface Props {
  data: FighterStatsByWeightClass[]
}

export default function FighterStatsByWeightClassTable({ data }: Props) {
  if (!data.length) return null

  const byWc = Object.fromEntries(data.map((d) => [d.weight_class, d]))
  const rows = WC_ORDER.filter((wc) => byWc[wc])

  // Per-column min/max for normalization
  const colStats = COLUMNS.map(({ key }) => {
    const vals = data.map((d) => d[key] as number).filter((v) => v > 0)
    return { min: Math.min(...vals), max: Math.max(...vals) }
  })

  return (
    <div className="overflow-x-auto -mx-1">
      <table className="min-w-max w-full text-xs border-collapse px-1">
        <thead>
          <tr>
            <th className="text-left pr-4 py-2 text-[var(--color-text-muted)] font-medium sticky left-0 bg-[var(--color-surface-light)] dark:bg-[var(--color-surface)]">
              Division
            </th>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                className="px-3 py-2 text-right text-[var(--color-text-muted)] font-medium whitespace-nowrap"
              >
                {col.label}
              </th>
            ))}
            <th className="px-3 py-2 text-right text-[var(--color-text-muted)] font-medium whitespace-nowrap">
              Fighters
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((wc) => {
            const row = byWc[wc]
            return (
              <Fragment key={wc}>
                <tr className="border-t border-[var(--color-border-light)] dark:border-[var(--color-border)]">
                  <td className="pr-4 py-2 font-medium text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] whitespace-nowrap sticky left-0 bg-[var(--color-surface-light)] dark:bg-[var(--color-surface)]">
                    <span className="hidden sm:inline">{wc}</span>
                    <span className="sm:hidden">{WC_SHORT[wc] ?? wc}</span>
                  </td>
                  {COLUMNS.map((col, i) => {
                    const val = row[col.key] as number
                    return (
                      <td
                        key={col.key}
                        className="px-3 py-2 text-right font-mono tabular-nums"
                        style={{ backgroundColor: cellColor(val, colStats[i].min, colStats[i].max) }}
                      >
                        {col.format(val)}
                      </td>
                    )
                  })}
                  <td className="px-3 py-2 text-right text-[var(--color-text-muted)] tabular-nums">
                    {row.fighter_count}
                  </td>
                </tr>
              </Fragment>
            )
          })}
        </tbody>
      </table>

      {/* Column legend */}
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-[var(--color-text-muted)]">
        <span>SLpM = sig. strikes landed per min</span>
        <span>SApM = sig. strikes absorbed per min</span>
        <span>TD Avg. = takedowns per 15 min</span>
        <span>Sub. Avg. = submission attempts per 15 min</span>
        <span>Color intensity = relative value within each column</span>
      </div>
    </div>
  )
}
