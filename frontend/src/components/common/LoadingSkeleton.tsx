interface LoadingSkeletonProps {
  lines?: number
  className?: string
}

export default function LoadingSkeleton({ lines = 3, className = '' }: LoadingSkeletonProps) {
  return (
    <div className={`space-y-3 animate-pulse ${className}`} aria-busy="true" aria-label="Loading">
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="h-4 rounded bg-[var(--color-surface-high)]"
          style={{ width: i === lines - 1 ? '60%' : '100%' }}
        />
      ))}
    </div>
  )
}
