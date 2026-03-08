import { apiClient } from './api'
import type { StyleEvolutionResponse, FighterEnduranceResponse } from '@t/api'

export const analyticsService = {
  getStyleEvolution: (weightClass?: string) =>
    apiClient
      .get<StyleEvolutionResponse>('/analytics/style-evolution', {
        params: weightClass ? { weight_class: weightClass } : {},
      })
      .then((r) => r.data),

  getFighterEndurance: (fighterId: string) =>
    apiClient
      .get<FighterEnduranceResponse>(`/analytics/fighter-endurance/${fighterId}`)
      .then((r) => r.data),
}
