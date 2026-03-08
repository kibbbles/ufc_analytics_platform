import { Component } from 'react'
import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  message: string
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error: unknown): State {
    const message = error instanceof Error ? error.message : 'An unexpected error occurred'
    return { hasError: true, message }
  }

  override render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
            <p className="text-4xl" aria-hidden="true">⚠</p>
            <h2 className="text-lg font-semibold">Something went wrong</h2>
            <p className="text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
              {this.state.message}
            </p>
            <button
              onClick={() => this.setState({ hasError: false, message: '' })}
              className="mt-2 px-4 py-2 rounded-md bg-[var(--color-primary)] text-white text-sm hover:bg-[var(--color-primary-hover)] transition-colors"
            >
              Try again
            </button>
          </div>
        )
      )
    }
    return this.props.children
  }
}
