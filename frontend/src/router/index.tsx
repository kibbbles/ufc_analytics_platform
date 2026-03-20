import { lazy, Suspense } from 'react'
import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import Layout from '@components/layout/Layout'
import LoadingSpinner from '@components/common/LoadingSpinner'
import NotFoundPage from '@pages/NotFoundPage'

// Wrap lazy imports so stale-chunk errors (after a new deploy) trigger a hard
// reload instead of showing the React Router error boundary.
function lazyWithReload<T extends React.ComponentType>(
  factory: () => Promise<{ default: T }>
) {
  return lazy(() =>
    factory().catch(() => {
      window.location.reload()
      return new Promise<{ default: T }>(() => {})
    })
  )
}

// Lazy-loaded pages — each becomes its own JS chunk
const HomePage            = lazyWithReload(() => import('@pages/HomePage'))
const PredictionsPage     = lazyWithReload(() => import('@pages/PredictionsPage'))
const FightersPage        = lazyWithReload(() => import('@pages/FightersPage'))
const FighterDetailPage   = lazyWithReload(() => import('@pages/FighterDetailPage'))
const EventsPage          = lazyWithReload(() => import('@pages/EventsPage'))
const EventDetailPage     = lazyWithReload(() => import('@pages/EventDetailPage'))
const UpcomingPage        = lazyWithReload(() => import('@pages/UpcomingPage'))
const UpcomingFightPage   = lazyWithReload(() => import('@pages/UpcomingFightPage'))
const StyleEvolutionPage  = lazyWithReload(() => import('@pages/StyleEvolutionPage'))
const EndurancePage       = lazyWithReload(() => import('@pages/EndurancePage'))
const AboutPage                  = lazyWithReload(() => import('@pages/AboutPage'))
const PastPredictionEventPage    = lazyWithReload(() => import('@pages/PastPredictionEventPage'))
const PastPredictionFightPage    = lazyWithReload(() => import('@pages/PastPredictionFightPage'))

const fallback = <LoadingSpinner fullScreen />

const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true,                    element: <Suspense fallback={fallback}><HomePage /></Suspense> },
      { path: 'predictions',            element: <Suspense fallback={fallback}><PredictionsPage /></Suspense> },
      { path: 'fighters',               element: <Suspense fallback={fallback}><FightersPage /></Suspense> },
      { path: 'fighters/:id',           element: <Suspense fallback={fallback}><FighterDetailPage /></Suspense> },
      { path: 'events',                 element: <Suspense fallback={fallback}><EventsPage /></Suspense> },
      { path: 'events/:id',             element: <Suspense fallback={fallback}><EventDetailPage /></Suspense> },
      { path: 'upcoming',               element: <Suspense fallback={fallback}><UpcomingPage /></Suspense> },
      { path: 'upcoming/fights/:id',    element: <Suspense fallback={fallback}><UpcomingFightPage /></Suspense> },
      { path: 'analytics/style-evolution', element: <Suspense fallback={fallback}><StyleEvolutionPage /></Suspense> },
      { path: 'analytics/endurance',    element: <Suspense fallback={fallback}><EndurancePage /></Suspense> },
      { path: 'about',                  element: <Suspense fallback={fallback}><AboutPage /></Suspense> },
      { path: 'past-predictions/events/:event_id', element: <Suspense fallback={fallback}><PastPredictionEventPage /></Suspense> },
      { path: 'past-predictions/fights/:fight_id', element: <Suspense fallback={fallback}><PastPredictionFightPage /></Suspense> },
      { path: '*',                      element: <NotFoundPage /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
