import type { ReactNode } from 'react'

/**
 * RouteGuard — scaffold for future protected routes.
 * Currently passes through all children (no auth required per CLAUDE.md).
 * Extend here if auth is added later.
 */
interface RouteGuardProps {
  children: ReactNode
}

export default function RouteGuard({ children }: RouteGuardProps) {
  return <>{children}</>
}
