import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { parsePageParam, withParams } from '@utils/pagination'

/**
 * Page number and search text for a paginated list, kept in the URL as ?page=
 * and ?q= so Back, reload and shared links return to the same page.
 *
 * Changing the page adds a history entry, so Back steps to the previous page.
 * Typing a search replaces the current entry and goes back to page 1.
 */
export function useListParams() {
  const [params, setParams] = useSearchParams()
  const page = parsePageParam(params.get('page'))
  const query = params.get('q') ?? ''

  const setPage = useCallback(
    (next: number, options: { replace?: boolean } = {}) =>
      setParams(prev => withParams(prev, { page: next }), { replace: options.replace ?? false }),
    [setParams],
  )

  const setQuery = useCallback(
    (next: string) =>
      setParams(prev => withParams(prev, { q: next, page: null }), { replace: true }),
    [setParams],
  )

  return { page, query, setPage, setQuery }
}
