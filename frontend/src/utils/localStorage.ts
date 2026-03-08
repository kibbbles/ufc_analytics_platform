export const STORAGE_KEYS = {
  FILTERS: 'ufc-analytics:filters',
} as const

export function getStoredItem<T>(key: string): T | null {
  try {
    const item = localStorage.getItem(key)
    return item ? (JSON.parse(item) as T) : null
  } catch {
    return null
  }
}

export function setStoredItem<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Storage quota exceeded or private browsing — fail silently
  }
}

export function removeStoredItem(key: string): void {
  try {
    localStorage.removeItem(key)
  } catch {
    // fail silently
  }
}
