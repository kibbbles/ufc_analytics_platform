import { apiClient } from './api'
import type {
  PastPredictionsResponse,
  PastPredictionEventsResponse,
  PastPredictionEventDetail,
} from '@t/api'

export const pastPredictionsService = {
  get: (limit = 10) =>
    apiClient
      .get<PastPredictionsResponse>('/past-predictions', { params: { limit } })
      .then((r) => r.data),

  getEvents: (params: { page?: number; page_size?: number; search?: string; year?: number }) =>
    apiClient
      .get<PastPredictionEventsResponse>('/past-predictions/events', { params })
      .then((r) => r.data),

  getEvent: (eventId: string) =>
    apiClient
      .get<PastPredictionEventDetail>(`/past-predictions/events/${eventId}`)
      .then((r) => r.data),
}
