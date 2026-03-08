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
  success: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  warning: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  danger: 'bg-red-500/15 text-red-600 dark:text-red-400',
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
