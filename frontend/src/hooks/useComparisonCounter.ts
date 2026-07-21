import { useCallback, useState } from 'react'

// Tracks how many DISTINCT strategy/filter combinations the user has looked at,
// persisted across reloads so the count can't be escaped by refreshing. It only
// resets on an explicit user action. This powers the multiple-comparisons
// warning: the more combinations tried, the more likely one looks good by luck.
const KEY = 'kbm.strategy.combos.v1'

function load(): Set<string> {
  try {
    const raw = localStorage.getItem(KEY)
    return new Set(raw ? (JSON.parse(raw) as string[]) : [])
  } catch {
    return new Set()
  }
}

function save(combos: Set<string>): void {
  try {
    localStorage.setItem(KEY, JSON.stringify([...combos]))
  } catch {
    /* localStorage unavailable (private mode / disabled) - counting is best-effort */
  }
}

export function useComparisonCounter() {
  const [combos, setCombos] = useState<Set<string>>(load)

  const record = useCallback((key: string) => {
    setCombos(prev => {
      if (prev.has(key)) return prev
      const next = new Set(prev)
      next.add(key)
      save(next)
      return next
    })
  }, [])

  const reset = useCallback(() => {
    setCombos(new Set())
    save(new Set())
  }, [])

  return { count: combos.size, record, reset }
}
