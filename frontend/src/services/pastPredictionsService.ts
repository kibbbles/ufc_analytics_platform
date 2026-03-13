import { apiClient } from './api'
import type { PastPredictionsResponse } from '@t/api'

export const pastPredictionsService = {
  get: (limit = 10) =>
    apiClient
      .get<PastPredictionsResponse>('/past-predictions', { params: { limit } })
      .then((r) => r.data),
}
