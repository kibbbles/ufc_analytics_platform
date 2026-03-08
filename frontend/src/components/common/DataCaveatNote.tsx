import type { ReactNode } from 'react'

interface DataCaveatNoteProps {
  children: ReactNode
  className?: string
}

export default function DataCaveatNote({ children, className = '' }: DataCaveatNoteProps) {
  return (
    <div
      role="note"
      className={[
        'flex items-start gap-2.5 rounded-md px-4 py-3 text-sm',
        'border border-amber-500/30 bg-amber-500/10',
        'text-amber-700 dark:text-amber-300',
        className,
      ].join(' ')}
    >
      <span className="mt-0.5 shrink-0" aria-hidden="true">
        ⓘ
      </span>
      <span>{children}</span>
    </div>
  )
}
