import { useState, useRef } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTheme } from './ThemeProvider'

// Plain nav links (no dropdown)
const navLinks = [
  { to: '/',         label: 'Home',           end: true },
  { to: '/upcoming', label: 'Upcoming' },
  { to: '/events',   label: 'Fight Database' },
  { to: '/fighters', label: 'Fighter Lookup' },
]

const trailingLinks = [
  { to: '/about', label: 'About' },
]

// Analytics dropdown items — add new analytics pages here
const analyticsLinks = [
  { to: '/analytics/style-evolution', label: 'How UFC Changed' },
  // { to: '/analytics/fighter-endurance', label: 'Fighter Endurance' },
  // { to: '/analytics/fight-predictor',   label: 'Fight Predictor' },
]

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`size-3 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
      viewBox="0 0 12 12"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M2 4l4 4 4-4" />
    </svg>
  )
}

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
      className={[
        'relative inline-flex h-7 w-14 shrink-0 rounded-full border',
        'transition-colors duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2',
        isDark
          ? 'bg-slate-700 border-slate-600'
          : 'bg-amber-100 border-amber-300',
      ].join(' ')}
    >
      <span
        aria-hidden="true"
        className={[
          'absolute top-[2px] left-[2px] size-6 rounded-full shadow',
          'flex items-center justify-center',
          'transition-transform duration-200',
          isDark ? 'translate-x-7 bg-slate-900' : 'translate-x-0 bg-white',
        ].join(' ')}
      >
        {isDark
          ? <MoonIcon className="size-3.5 text-slate-300" />
          : <SunIcon className="size-3.5 text-amber-500" />}
      </span>
    </button>
  )
}

// ── Desktop analytics dropdown ────────────────────────────────────────────────

function AnalyticsDropdown() {
  const location = useLocation()
  const isAnalyticsActive = location.pathname.startsWith('/analytics')
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [open, setOpen] = useState(false)

  const handleMouseEnter = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    setOpen(true)
  }

  const handleMouseLeave = () => {
    // Small delay so the user can move the cursor into the dropdown
    timeoutRef.current = setTimeout(() => setOpen(false), 120)
  }

  const dropdownLinkClass = (isActive: boolean) =>
    `block px-3 py-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors ${
      isActive
        ? 'bg-[var(--color-primary)] text-white'
        : 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-high-light)] dark:hover:bg-[var(--color-surface-high)]'
    }`

  return (
    <div
      className="relative"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Trigger button — styled like a nav link, active when on any /analytics route */}
      <button
        aria-haspopup="true"
        aria-expanded={open}
        className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          isAnalyticsActive
            ? 'bg-[var(--color-primary)] text-white'
            : 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-high-light)] dark:hover:bg-[var(--color-surface-high)]'
        }`}
      >
        Analytics
        <ChevronIcon open={open} />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute left-0 top-full mt-1 min-w-[160px] rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-surface-light)] dark:bg-[var(--color-surface)] shadow-lg py-1 z-50">
          {analyticsLinks.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setOpen(false)}
              className={({ isActive }) => dropdownLinkClass(isActive)}
            >
              {label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Mobile analytics accordion ────────────────────────────────────────────────

function MobileAnalyticsAccordion({ onNavigate }: { onNavigate: () => void }) {
  const location = useLocation()
  const isAnalyticsActive = location.pathname.startsWith('/analytics')
  const [open, setOpen] = useState(isAnalyticsActive)

  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium transition-colors ${
          isAnalyticsActive
            ? 'bg-[var(--color-primary)] text-white'
            : 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-high-light)] dark:hover:bg-[var(--color-surface-high)]'
        }`}
      >
        Analytics
        <ChevronIcon open={open} />
      </button>

      {open && (
        <div className="mt-1 ml-3 pl-3 border-l-2 border-[var(--color-border-light)] dark:border-[var(--color-border)] space-y-1">
          {analyticsLinks.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onNavigate}
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
        </div>
      )}
    </div>
  )
}

// ── Header ────────────────────────────────────────────────────────────────────

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
          className="flex flex-col leading-tight text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]"
        >
          <span className="font-bold text-base tracking-tight">
            <span className="text-[var(--color-primary)]">Kabe's</span>
            {' '}Maybes
            <span className="hidden md:inline text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] font-normal"> — UFC odds, my way</span>
          </span>
        </NavLink>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
          {navLinks.map(({ to, label, end }) => (
            <NavLink key={to} to={to} end={end} className={linkClass}>
              {label}
            </NavLink>
          ))}
          <AnalyticsDropdown />
          {trailingLinks.map(({ to, label }) => (
            <NavLink key={to} to={to} className={linkClass}>
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
          {/* Home, Upcoming, Fight Database, Fighter Lookup */}
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
          {/* Analytics accordion */}
          <MobileAnalyticsAccordion onNavigate={() => setMenuOpen(false)} />
          {/* About — always last */}
          {trailingLinks.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
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
