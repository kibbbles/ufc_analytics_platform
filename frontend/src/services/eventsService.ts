import { apiClient } from './api'
import type { EventListResponse, EventWithFightsResponse } from '@t/api'

export interface GetEventsParams {
  page?: number
  page_size?: number
  year?: number
}

export const eventsService = {
  getList: (params: GetEventsParams = {}) =>
    apiClient.get<EventListResponse>('/events', { params }).then((r) => r.data),

  getById: (id: string) =>
    apiClient.get<EventWithFightsResponse>(`/events/${id}`).then((r) => r.data),
}
