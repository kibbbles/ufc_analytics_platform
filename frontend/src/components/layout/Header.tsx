import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useTheme } from './ThemeProvider'

const navLinks = [
  { to: '/',                           label: 'Home',       end: true },
  { to: '/predictions',                label: 'Predictions' },
  { to: '/upcoming',                   label: 'Upcoming' },
  { to: '/fighters',                   label: 'Fighters' },
  { to: '/events',                     label: 'Events' },
  { to: '/analytics/style-evolution',  label: 'Analytics' },
]

function SunIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M10 2a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1Zm4.22 1.78a1 1 0 0 1 0 1.42l-.71.7a1 1 0 1 1-1.41-1.41l.7-.71a1 1 0 0 1 1.42 0ZM18 9a1 1 0 1 1 0 2h-1a1 1 0 1 1 0-2h1Zm-2.07 5.66a1 1 0 0 1-1.41 0l-.71-.71a1 1 0 1 1 1.41-1.41l.71.71a1 1 0 0 1 0 1.41ZM11 16a1 1 0 1 1-2 0v-1a1 1 0 1 1 2 0v1Zm-4.95-.34a1 1 0 0 1 0-1.41l.7-.71a1 1 0 0 1 1.42 1.41l-.71.71a1 1 0 0 1-1.41 0ZM4 11a1 1 0 1 1 0-2h1a1 1 0 0 1 0 2H4Zm.34-6.61a1 1 0 0 1 1.41 0l.71.71A1 1 0 0 1 5.05 6.5l-.7-.7a1 1 0 0 1 0-1.41ZM10 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z" />
    </svg>
  )
}

function MoonIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M17.293 13.293A8 8 0 0 1 6.707 2.707a8.001 8.001 0 1 0 10.586 10.586Z" />
    </svg>
  )
}

function ThemeToggle() {
  const { isDark, toggle } = useTheme()

  return (
    <button
      role="switch"
      aria-checked={isDark}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      onClick={toggle}
      className="flex items-center gap-1.5 group"
    >
      <SunIcon
        className={`size-3.5 transition-colors duration-200 ${
          isDark ? 'text-slate-500' : 'text-amber-500'
        }`}
      />
      {/* Track */}
      <span
        className={`relative inline-flex h-[22px] w-[40px] shrink-0 rounded-full border transition-colors duration-200 ${
          isDark
            ? 'bg-[var(--color-primary)]/20 border-[var(--color-primary)]/40'
            : 'bg-slate-200 border-slate-300'
        }`}
      >
        {/* Thumb */}
        <span
          className={`absolute top-[2px] left-[2px] size-[16px] rounded-full shadow-md transition-transform duration-200 ${
            isDark ? 'translate-x-[18px] bg-[var(--color-primary)]' : 'translate-x-0 bg-white'
          }`}
        />
      </span>
      <MoonIcon
        className={`size-3.5 transition-colors duration-200 ${
          isDark ? 'text-[var(--color-primary)]' : 'text-slate-400'
        }`}
      />
    </button>
  )
}

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false)

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-[var(--color-primary)] text-white'
        : 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-high-light)] dark:hover:bg-[var(--color-surface-high)]'
    }`

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-surface-light)]/95 dark:bg-[var(--color-surface)]/95 backdrop-blur-sm">
      <div className="mx-auto max-w-[1440px] px-4 md:px-6 lg:px-8 flex items-center justify-between h-14">

        {/* Logo */}
        <NavLink
          to="/"
          className="flex items-center gap-2 font-bold text-lg tracking-tight text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]"
        >
          <span className="text-[var(--color-primary)]">UFC</span>
          <span>Analytics</span>
        </NavLink>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
          {navLinks.map(({ to, label, end }) => (
            <NavLink key={to} to={to} end={end} className={linkClass}>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Right side: toggle + hamburger */}
        <div className="flex items-center gap-3">
          <ThemeToggle />

          {/* Hamburger — mobile only */}
          <button
            className="md:hidden p-1.5 rounded-md text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-high-light)] dark:hover:bg-[var(--color-surface-high)] transition-colors"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((o) => !o)}
          >
            {menuOpen ? (
              <svg className="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <nav
          className="md:hidden border-t border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-surface-light)] dark:bg-[var(--color-surface)] px-4 py-3 space-y-1"
          aria-label="Mobile navigation"
        >
          {navLinks.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-[var(--color-primary)] text-white'
                    : 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-high-light)] dark:hover:bg-[var(--color-surface-high)]'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  )
}
