import { apiClient } from './api'
import type { FighterListResponse, FighterResponse } from '@t/api'

export interface GetFightersParams {
  page?: number
  page_size?: number
  search?: string
}

export const fightersService = {
  getList: (params: GetFightersParams = {}) =>
    apiClient.get<FighterListResponse>('/fighters', { params }).then((r) => r.data),

  getById: (id: string) =>
    apiClient.get<FighterResponse>(`/fighters/${id}`).then((r) => r.data),
}
