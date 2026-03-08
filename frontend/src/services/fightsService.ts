import { apiClient } from './api'
import type { FightListResponse, FightResponse } from '@t/api'

export interface GetFightsParams {
  page?: number
  page_size?: number
  event_id?: string
  fighter_id?: string
  weight_class?: string
  method?: string
}

export const fightsService = {
  getList: (params: GetFightsParams = {}) =>
    apiClient.get<FightListResponse>('/fights', { params }).then((r) => r.data),

  getById: (id: string) =>
    apiClient.get<FightResponse>(`/fights/${id}`).then((r) => r.data),
}
