import { lazy, Suspense } from 'react'
import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import Layout from '@components/layout/Layout'
import LoadingSpinner from '@components/common/LoadingSpinner'
import NotFoundPage from '@pages/NotFoundPage'

// Lazy-loaded pages — each becomes its own JS chunk
const HomePage            = lazy(() => import('@pages/HomePage'))
const PredictionsPage     = lazy(() => import('@pages/PredictionsPage'))
const FightersPage        = lazy(() => import('@pages/FightersPage'))
const FighterDetailPage   = lazy(() => import('@pages/FighterDetailPage'))
const EventsPage          = lazy(() => import('@pages/EventsPage'))
const EventDetailPage     = lazy(() => import('@pages/EventDetailPage'))
const UpcomingPage        = lazy(() => import('@pages/UpcomingPage'))
const UpcomingFightPage   = lazy(() => import('@pages/UpcomingFightPage'))
const StyleEvolutionPage  = lazy(() => import('@pages/StyleEvolutionPage'))
const EndurancePage       = lazy(() => import('@pages/EndurancePage'))
const AboutPage                  = lazy(() => import('@pages/AboutPage'))
const PastPredictionEventPage    = lazy(() => import('@pages/PastPredictionEventPage'))
const PastPredictionFightPage    = lazy(() => import('@pages/PastPredictionFightPage'))

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
