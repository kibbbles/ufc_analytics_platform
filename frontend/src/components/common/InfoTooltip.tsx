import { useState, useRef, useEffect, type ReactNode } from 'react'

interface InfoTooltipProps {
  /** Accessible name for the trigger button (e.g. "What does pp mean?"). */
  label: string
  /** Popover content shown on tap. */
  children: ReactNode
}

/**
 * A tap-to-reveal info affordance. Renders a small "i" button that toggles a
 * popover on click/tap (never hover, so it works on touch). Closes on outside
 * tap or Escape. Each instance manages its own open state.
 */
export default function InfoTooltip({ label, children }: InfoTooltipProps) {
  const [open, setOpen] = useState(false)
  const wrapRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!open) return
    function onDocPointer(e: PointerEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onDocPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onDocPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <span ref={wrapRef} className="relative inline-flex align-middle">
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        onClick={(e) => {
          e.stopPropagation()
          setOpen((o) => !o)
        }}
        className="relative inline-flex h-4 w-4 items-center justify-center rounded-full border border-current text-xs font-semibold leading-none opacity-60 transition-opacity hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] before:absolute before:-inset-3 before:content-['']"
      >
        i
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute right-0 top-[calc(100%+8px)] z-30 w-[min(260px,78vw)] rounded-lg border border-[var(--color-border)] bg-white px-3 py-2.5 text-left text-xs font-normal normal-case leading-snug tracking-normal text-[var(--color-text-secondary-light)] shadow-lg dark:bg-[var(--color-surface)] dark:text-[var(--color-text-secondary)]"
        >
          {children}
        </span>
      )}
    </span>
  )
}
