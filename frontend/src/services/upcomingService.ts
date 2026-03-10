import { apiClient } from './api'
import type { UpcomingEventListResponse, UpcomingEventWithFights } from '@t/api'

export const upcomingService = {
  getEvents: () =>
    apiClient.get<UpcomingEventListResponse>('/upcoming/events').then((r) => r.data),

  getEventWithFights: (id: string) =>
    apiClient.get<UpcomingEventWithFights>(`/upcoming/events/${id}`).then((r) => r.data),
}
