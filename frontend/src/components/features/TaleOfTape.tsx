import type { FighterResponse } from '@t/api'
import { inchesToFeet, formatDate, formatFightTime, EMPTY } from '@utils/format'

interface Props {
  a: FighterResponse | null
  b: FighterResponse | null
  nameA: string
  nameB: string
}

function heightDisplay(inches: number | null | undefined): string {
  return inches != null ? inchesToFeet(inches) : EMPTY
}

function record(f: FighterResponse | null): string {
  if (!f) return EMPTY
  if (f.career_wins != null) return `${f.career_wins}-${f.career_losses ?? 0}-${f.career_draws ?? 0}`
  return `${f.wins ?? 0}-${f.losses ?? 0}-${f.draws ?? 0}`
}

/** Two-column physical/record comparison table shared by the upcoming and past fight pages. */
export default function TaleOfTape({ a, b, nameA, nameB }: Props) {
  const hasCareer = (a?.career_wins != null) || (b?.career_wins != null)

  const rows: { label: string; valA: string; valB: string }[] = [
    { label: hasCareer ? 'Record' : 'Record (UFC)', valA: record(a), valB: record(b) },
    { label: 'Avg. Fight', valA: formatFightTime(a?.avg_fight_time_seconds), valB: formatFightTime(b?.avg_fight_time_seconds) },
    { label: 'Height', valA: heightDisplay(a?.height_inches), valB: heightDisplay(b?.height_inches) },
    { label: 'Weight', valA: a?.weight_lbs != null ? `${a.weight_lbs} lbs` : EMPTY, valB: b?.weight_lbs != null ? `${b.weight_lbs} lbs` : EMPTY },
    { label: 'Reach', valA: a?.reach_inches != null ? `${a.reach_inches}"` : EMPTY, valB: b?.reach_inches != null ? `${b.reach_inches}"` : EMPTY },
    { label: 'Stance', valA: a?.stance ?? EMPTY, valB: b?.stance ?? EMPTY },
    { label: 'DOB', valA: a?.dob_date ? formatDate(String(a.dob_date)) : EMPTY, valB: b?.dob_date ? formatDate(String(b.dob_date)) : EMPTY },
  ]

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
          <th className="pb-2 text-left font-medium">{nameA}</th>
          <th className="pb-2 text-center font-medium"></th>
          <th className="pb-2 text-right font-medium">{nameB}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ label, valA, valB }) => (
          <tr key={label} className="border-t border-[var(--color-border)]">
            <td className="py-2 font-mono tabular-nums">{valA}</td>
            <td className="py-2 text-center text-xs text-[var(--color-text-muted)]">{label}</td>
            <td className="py-2 text-right font-mono tabular-nums">{valB}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
