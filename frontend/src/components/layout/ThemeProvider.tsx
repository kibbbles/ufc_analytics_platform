import { type ReactNode } from 'react'
import { useDarkMode } from '@hooks/useDarkMode'
import { ThemeContext } from './themeContext'

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { isDark, toggle } = useDarkMode()

  return (
    <ThemeContext.Provider value={{ isDark, toggle }}>
      {children}
    </ThemeContext.Provider>
  )
}
