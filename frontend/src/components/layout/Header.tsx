import { NavLink } from 'react-router-dom'
import { useTheme } from './ThemeProvider'

const navLinks = [
  { to: '/',                      label: 'Home',            end: true },
  { to: '/predictions',           label: 'Predictions' },
  { to: '/upcoming',              label: 'Upcoming' },
  { to: '/fighters',              label: 'Fighters' },
  { to: '/events',                label: 'Events' },
  { to: '/analytics/style-evolution', label: 'Analytics' },
]

export default function Header() {
  const { isDark, toggle } = useTheme()

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-surface-light)] dark:bg-[var(--color-surface)] backdrop-blur-sm">
      <div className="mx-auto max-w-[1440px] px-4 md:px-6 lg:px-8 flex items-center justify-between h-14">

        {/* Logo */}
        <NavLink to="/" className="flex items-center gap-2 font-bold text-lg tracking-tight text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
          <span className="text-[var(--color-primary)]">UFC</span>
          <span>Analytics</span>
        </NavLink>

        {/* Nav */}
        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-[var(--color-primary)] text-white'
                    : 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-high-light)] dark:hover:bg-[var(--color-surface-high)]'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Dark mode toggle */}
        <button
          onClick={toggle}
          aria-label="Toggle dark mode"
          className="p-2 rounded-md text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-high-light)] dark:hover:bg-[var(--color-surface-high)] transition-colors"
        >
          {isDark ? '☀' : '☾'}
        </button>
      </div>
    </header>
  )
}
