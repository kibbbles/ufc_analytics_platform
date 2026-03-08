interface LoadingSpinnerProps {
  fullScreen?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export default function LoadingSpinner({ fullScreen = false, size = 'md' }: LoadingSpinnerProps) {
  const sizeClass = { sm: 'w-5 h-5', md: 'w-8 h-8', lg: 'w-12 h-12' }[size]

  const spinner = (
    <div
      className={`${sizeClass} rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-primary)] animate-spin`}
      role="status"
      aria-label="Loading"
    />
  )

  if (fullScreen) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[var(--color-bg-light)] dark:bg-[var(--color-bg)]">
        {spinner}
      </div>
    )
  }

  return <div className="flex items-center justify-center p-8">{spinner}</div>
}
