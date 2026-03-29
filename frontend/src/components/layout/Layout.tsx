import { Outlet } from 'react-router-dom'
import Header from './Header'
import { ToastContainer } from '@components/common'
import ChatWidget from '@components/features/ChatWidget/ChatWidget'

export default function Layout() {
  return (
    <div className="min-h-screen bg-[var(--color-bg-light)] dark:bg-[var(--color-bg)] text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
      <Header />
      <main className="mx-auto max-w-[1440px] px-4 md:px-6 lg:px-8 py-6">
        <Outlet />
      </main>
      <ToastContainer />
      <ChatWidget />
    </div>
  )
}
