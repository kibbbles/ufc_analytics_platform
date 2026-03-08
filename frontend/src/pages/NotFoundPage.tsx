import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center">
      <p className="text-6xl font-bold text-[var(--color-primary)]">404</p>
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
        That route doesn't exist.
      </p>
      <Link
        to="/"
        className="mt-2 px-4 py-2 rounded-md bg-[var(--color-primary)] text-white text-sm font-medium hover:bg-[var(--color-primary-hover)] transition-colors"
      >
        Back to home
      </Link>
    </div>
  )
}
