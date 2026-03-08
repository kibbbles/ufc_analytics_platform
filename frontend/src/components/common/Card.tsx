import type { ReactNode } from 'react'

interface CardProps {
  header?: ReactNode
  footer?: ReactNode
  children: ReactNode
  className?: string
}

export default function Card({ header, footer, children, className = '' }: CardProps) {
  return (
    <div
      className={[
        'rounded-lg border border-[var(--color-border)]',
        'bg-white dark:bg-[var(--color-surface)]',
        'shadow-[var(--shadow-card)]',
        className,
      ].join(' ')}
    >
      {header && (
        <div className="px-5 py-4 border-b border-[var(--color-border)]">{header}</div>
      )}
      <div className="px-5 py-4">{children}</div>
      {footer && (
        <div className="px-5 py-3 border-t border-[var(--color-border)] bg-[var(--color-surface-high)] rounded-b-lg">
          {footer}
        </div>
      )}
    </div>
  )
}
