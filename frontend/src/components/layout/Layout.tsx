import { Outlet } from 'react-router-dom'
import Header from './Header'
import { ToastContainer } from '@components/common'
import ChatWidget from '@components/features/ChatWidget/ChatWidget'

export default function Layout() {
  return (
    <div className="min-h-screen bg-[var(--color-bg-light)] dark:bg-[var(--color-bg)] text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
      <Header />
      {/* pb-24 (96px) clears the floating chat button (56px, 16px from the
          bottom), so the last thing on a page, often its pagination, can
          scroll out from under it on a phone. */}
      <main className="mx-auto max-w-[1440px] px-4 md:px-6 lg:px-8 pt-6 pb-24">
        <Outlet />
      </main>
      <ToastContainer />
      <ChatWidget />
    </div>
  )
}
