import { useState, useEffect, useCallback, useRef } from 'react'

interface ApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/**
 * Generic data-fetching hook.
 *
 * @param fetcher  Async function that returns the data. Re-runs when deps change.
 * @param deps     Dependency array (same semantics as useEffect deps).
 *
 * @example
 * const { data, loading, error } = useApi(
 *   () => fightersService.getList({ page: 1 }),
 *   [page],
 * )
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: true,
    error: null,
  })

  // Keep fetcher stable across renders without adding it to deps
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const execute = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const data = await fetcherRef.current()
      setState({ data, loading: false, error: null })
    } catch (err) {
      setState({
        data: null,
        loading: false,
        error: err instanceof Error ? err.message : 'Unknown error',
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    void execute()
  }, [execute])

  return { ...state, refetch: execute }
}
