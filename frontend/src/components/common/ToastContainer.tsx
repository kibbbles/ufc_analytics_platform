import { useEffect } from 'react'
import { useNotification } from '@hooks/useNotification'
import Toast from './Toast'

const AUTO_DISMISS_MS = 4000

export default function ToastContainer() {
  const { notification, dismissNotification } = useNotification()

  useEffect(() => {
    if (!notification) return
    const timer = setTimeout(dismissNotification, AUTO_DISMISS_MS)
    return () => clearTimeout(timer)
  }, [notification, dismissNotification])

  if (!notification) return null

  return (
    <div className="fixed bottom-6 right-6 z-50 w-full max-w-sm" aria-live="polite">
      <Toast notification={notification} onDismiss={dismissNotification} />
    </div>
  )
}
