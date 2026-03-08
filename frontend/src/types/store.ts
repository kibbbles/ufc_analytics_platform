// Filter state — shared across fighters list, events list, and analytics pages
export interface FilterState {
  weightClass: string | null
  year: number | null
  searchQuery: string
}

export interface AppNotification {
  id: string
  message: string
  type: 'success' | 'error' | 'info'
}

export interface UIState {
  notification: AppNotification | null
}

export interface AppState {
  filters: FilterState
  ui: UIState
}

// Discriminated union action types
export type FilterAction =
  | { type: 'SET_WEIGHT_CLASS'; payload: string | null }
  | { type: 'SET_YEAR'; payload: number | null }
  | { type: 'SET_SEARCH_QUERY'; payload: string }
  | { type: 'CLEAR_FILTERS' }

export type UIAction =
  | { type: 'SHOW_NOTIFICATION'; payload: AppNotification }
  | { type: 'DISMISS_NOTIFICATION' }

export type AppAction = FilterAction | UIAction
