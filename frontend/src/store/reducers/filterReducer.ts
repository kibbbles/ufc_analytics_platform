import type { FilterState, FilterAction } from '@t/store'

export const initialFilterState: FilterState = {
  weightClass: null,
  year: null,
  searchQuery: '',
}

export function filterReducer(state: FilterState, action: FilterAction): FilterState {
  switch (action.type) {
    case 'SET_WEIGHT_CLASS':
      return { ...state, weightClass: action.payload }
    case 'SET_YEAR':
      return { ...state, year: action.payload }
    case 'SET_SEARCH_QUERY':
      return { ...state, searchQuery: action.payload }
    case 'CLEAR_FILTERS':
      return initialFilterState
    default:
      return state
  }
}
