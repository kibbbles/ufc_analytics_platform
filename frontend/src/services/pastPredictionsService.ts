import { apiClient } from './api'
import type {
  PastPredictionsResponse,
  PastPredictionEventsResponse,
  PastPredictionEventDetail,
  PastPredictionFightsResponse,
  PastPredictionItem,
  PastPredictionModalStats,
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

  getModalStats: () =>
    apiClient
      .get<PastPredictionModalStats>('/past-predictions/stats')
      .then((r) => r.data),

  searchFights: (params: {
    search?: string
    year?: number
    prediction_source?: string
    page?: number
    page_size?: number
  }) =>
    apiClient
      .get<PastPredictionFightsResponse>('/past-predictions/fights', { params })
      .then((r) => r.data),

  getFight: (fightId: string) =>
    apiClient
      .get<PastPredictionItem>(`/past-predictions/fights/${fightId}`)
      .then((r) => r.data),
}
