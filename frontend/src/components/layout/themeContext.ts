import { createContext } from 'react'

export interface ThemeContextValue {
  isDark: boolean
  toggle: () => void
}

export const ThemeContext = createContext<ThemeContextValue | null>(null)
