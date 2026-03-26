import { apiClient } from './api'
import type { FightListResponse, FightResponse, FightSearchResponse } from '@t/api'

export interface GetFightsParams {
  page?: number
  page_size?: number
  event_id?: string
  fighter_id?: string
  weight_class?: string
  method?: string
}

export interface SearchFightsParams {
  fighter_name?: string
  event_name?: string
  weight_class?: string
  method?: string
  page?: number
  page_size?: number
}

export const fightsService = {
  getList: (params: GetFightsParams = {}) =>
    apiClient.get<FightListResponse>('/fights', { params }).then((r) => r.data),

  getById: (id: string) =>
    apiClient.get<FightResponse>(`/fights/${id}`).then((r) => r.data),

  search: (params: SearchFightsParams = {}) =>
    apiClient.get<FightSearchResponse>('/fights/search', { params }).then((r) => r.data),
}
