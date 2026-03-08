import type { UIState, UIAction } from '@t/store'

export const initialUIState: UIState = {
  notification: null,
}

export function uiReducer(state: UIState, action: UIAction): UIState {
  switch (action.type) {
    case 'SHOW_NOTIFICATION':
      return { ...state, notification: action.payload }
    case 'DISMISS_NOTIFICATION':
      return { ...state, notification: null }
    default:
      return state
  }
}
