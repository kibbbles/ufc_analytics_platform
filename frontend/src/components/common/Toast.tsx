import type { AppNotification } from '@t/store'

interface ToastProps {
  notification: AppNotification
  onDismiss: () => void
}

const typeClasses: Record<AppNotification['type'], string> = {
  success: 'border-[var(--color-success)]/40 bg-[var(--color-success)]/10 text-[var(--color-success-light)] dark:text-[var(--color-success)]',
  error: 'border-[var(--color-error)]/40 bg-[var(--color-error)]/10 text-[var(--color-error-light)] dark:text-[var(--color-error)]',
  info: 'border-[var(--color-accent)]/40 bg-[var(--color-accent)]/10 text-[var(--color-accent)]',
}

const typeIcons: Record<AppNotification['type'], string> = {
  success: '✓',
  error: '✕',
  info: 'ⓘ',
}

export default function Toast({ notification, onDismiss }: ToastProps) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className={[
        'flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg text-sm',
        typeClasses[notification.type],
      ].join(' ')}
    >
      <span aria-hidden="true" className="shrink-0 font-bold">
        {typeIcons[notification.type]}
      </span>
      <span className="flex-1">{notification.message}</span>
      <button
        onClick={onDismiss}
        aria-label="Dismiss notification"
        className="shrink-0 opacity-60 hover:opacity-100 transition-opacity"
      >
        ✕
      </button>
    </div>
  )
}
