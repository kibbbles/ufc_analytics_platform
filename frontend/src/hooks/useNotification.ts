import { useCallback } from 'react'
import { useAppContext } from '@store/AppContext'
import type { AppNotification } from '@t/store'

export function useNotification() {
  const { state, dispatch } = useAppContext()

  const showNotification = useCallback(
    (notification: Omit<AppNotification, 'id'>) => {
      dispatch({
        type: 'SHOW_NOTIFICATION',
        payload: { ...notification, id: crypto.randomUUID() },
      })
    },
    [dispatch],
  )

  const dismissNotification = useCallback(() => {
    dispatch({ type: 'DISMISS_NOTIFICATION' })
  }, [dispatch])

  return {
    notification: state.ui.notification,
    showNotification,
    dismissNotification,
  }
}
