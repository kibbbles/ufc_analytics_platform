import { apiClient } from './api'
import type {
  BettingFightsResponse,
  BettingInsightsResponse,
  BettingRoiResponse,
  BettingUpsetsResponse,
  FighterEnduranceResponse,
  RoiOverTimeResponse,
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

  getRoiOverTime: (strategy: string) =>
    apiClient
      .get<RoiOverTimeResponse>('/analytics/roi-over-time', { params: { strategy } })
      .then((r) => r.data),

  getBettingUpsets: (params: { weight_class?: string | null; conviction_min?: number }) =>
    apiClient
      .get<BettingUpsetsResponse>('/analytics/betting-upsets', { params })
      .then((r) => r.data),

  getBettingFights: () =>
    apiClient
      .get<BettingFightsResponse>('/analytics/betting-insights/fights')
      .then((r) => r.data),
}
