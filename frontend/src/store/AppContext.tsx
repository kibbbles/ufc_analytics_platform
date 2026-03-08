import {
  createContext,
  useContext,
  useReducer,
  useEffect,
} from 'react'
import type { Dispatch, ReactNode } from 'react'
import type { AppState, AppAction, FilterState } from '@t/store'
import { filterReducer, initialFilterState } from './reducers/filterReducer'
import { uiReducer, initialUIState } from './reducers/uiReducer'
import { getStoredItem, setStoredItem, STORAGE_KEYS } from '@utils/localStorage'

interface AppContextValue {
  state: AppState
  dispatch: Dispatch<AppAction>
}

const AppContext = createContext<AppContextValue | null>(null)

function rootReducer(state: AppState, action: AppAction): AppState {
  return {
    filters: filterReducer(state.filters, action as Parameters<typeof filterReducer>[1]),
    ui: uiReducer(state.ui, action as Parameters<typeof uiReducer>[1]),
  }
}

function getInitialState(): AppState {
  const stored = getStoredItem<Partial<FilterState>>(STORAGE_KEYS.FILTERS)
  return {
    filters: stored
      ? { ...initialFilterState, weightClass: stored.weightClass ?? null, year: stored.year ?? null }
      : initialFilterState,
    ui: initialUIState,
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(rootReducer, undefined, getInitialState)

  // Persist weight class + year; searchQuery is always transient
  useEffect(() => {
    setStoredItem(STORAGE_KEYS.FILTERS, {
      weightClass: state.filters.weightClass,
      year: state.filters.year,
    })
  }, [state.filters.weightClass, state.filters.year])

  return <AppContext.Provider value={{ state, dispatch }}>{children}</AppContext.Provider>
}

export function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useAppContext must be used inside <AppProvider>')
  return ctx
}
