/** Format an ISO date string "YYYY-MM-DD" into a readable date (e.g. "Mar 8, 2026"). */
export function formatDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00') // force local midnight parse
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

/** Convert decimal inches to feet'inches" string (e.g. 72 → "6'0\""). */
export function inchesToFeet(inches: number): string {
  const ft = Math.floor(inches / 12)
  const ins = Math.round(inches % 12)
  return `${ft}'${ins}"`
}

/** Calculate age in full years from an ISO date string "YYYY-MM-DD". */
export function ageFromDob(dob: string): number {
  const today = new Date()
  const birth = new Date(dob + 'T00:00:00')
  let age = today.getFullYear() - birth.getFullYear()
  const m = today.getMonth() - birth.getMonth()
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--
  return age
}

/**
 * Given a bout string "Fighter A vs. Fighter B" and the viewing fighter's full name,
 * return the opponent's name. Falls back to the full bout string if parsing fails.
 */
export function parseOpponent(bout: string, fighterName: string): string {
  const parts = bout.split(' vs. ')
  if (parts.length !== 2) return bout
  const nameLower = fighterName.toLowerCase()
  if (parts[0].toLowerCase().includes(nameLower)) return parts[1].trim()
  if (parts[1].toLowerCase().includes(nameLower)) return parts[0].trim()
  return bout
}
