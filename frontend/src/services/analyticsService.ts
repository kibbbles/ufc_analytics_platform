import { apiClient } from './api'
import type {
  BettingInsightsResponse,
  BettingRoiResponse,
  FighterEnduranceResponse,
  StyleEvolutionResponse,
} from '@t/api'

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

  getBettingInsights: () =>
    apiClient
      .get<BettingInsightsResponse>('/analytics/betting-insights')
      .then((r) => r.data),

  getBettingRoi: (params: {
    side?: string
    conviction_min?: number | null
    conviction_max?: number | null
    weight_class?: string | null
    edge_min?: number | null
    edge_max?: number | null
    upset_filter?: string
    title_filter?: string
  }) =>
    apiClient
      .get<BettingRoiResponse>('/analytics/betting-roi', { params })
      .then((r) => r.data),
}
