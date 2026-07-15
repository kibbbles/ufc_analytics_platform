import type { ReactNode } from 'react'

type BadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'danger'

interface BadgeProps {
  variant?: BadgeVariant
  children: ReactNode
  className?: string
}

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-[var(--color-surface-high)] text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]',
  primary: 'bg-[var(--color-primary)]/15 text-[var(--color-primary)]',
  success: 'bg-[var(--color-success)]/15 text-[var(--color-success-light)] dark:text-[var(--color-success)]',
  warning: 'bg-[var(--color-warning)]/15 text-[var(--color-warning-light)] dark:text-[var(--color-warning)]',
  danger: 'bg-[var(--color-error)]/15 text-[var(--color-error-light)] dark:text-[var(--color-error)]',
}

export default function Badge({ variant = 'default', children, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  )
}
