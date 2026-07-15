import { createContext, type Dispatch } from 'react'
import type { AppState, AppAction } from '@t/store'

export interface AppContextValue {
  state: AppState
  dispatch: Dispatch<AppAction>
}

export const AppContext = createContext<AppContextValue | null>(null)
