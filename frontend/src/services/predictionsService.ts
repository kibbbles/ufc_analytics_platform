import { apiClient } from './api'
import type { PredictionRequest, PredictionResponse } from '@t/api'

export const predictionsService = {
  predict: (request: PredictionRequest) =>
    apiClient
      .post<PredictionResponse>('/predictions/fight-outcome', request)
      .then((r) => r.data),
}
