import { useCallback } from 'react'
import { useAppContext } from '@store/AppContext'

export function useFilters() {
  const { state, dispatch } = useAppContext()

  const setWeightClass = useCallback(
    (wc: string | null) => dispatch({ type: 'SET_WEIGHT_CLASS', payload: wc }),
    [dispatch],
  )

  const setYear = useCallback(
    (year: number | null) => dispatch({ type: 'SET_YEAR', payload: year }),
    [dispatch],
  )

  const setSearchQuery = useCallback(
    (q: string) => dispatch({ type: 'SET_SEARCH_QUERY', payload: q }),
    [dispatch],
  )

  const clearFilters = useCallback(() => dispatch({ type: 'CLEAR_FILTERS' }), [dispatch])

  return {
    filters: state.filters,
    setWeightClass,
    setYear,
    setSearchQuery,
    clearFilters,
  }
}
