// TypeScript interfaces mirroring the backend Pydantic schemas.
// Keep in sync with backend/schemas/*.py

// ── Shared ──────────────────────────────────────────────────────────────────

export interface PaginationMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

// ── Fighters ─────────────────────────────────────────────────────────────────

export interface FighterListItem {
  id: string
  first_name: string | null
  last_name: string | null
  nickname: string | null
  weight_class: string | null
  wins: number | null
  losses: number | null
}

export interface FighterListResponse {
  data: FighterListItem[]
  meta: PaginationMeta
}

export interface FighterResponse {
  id: string
  first_name: string | null
  last_name: string | null
  nickname: string | null
  // Physical stats (fighter_tott typed columns)
  height_inches: number | null
  weight_lbs: number | null
  reach_inches: number | null
  stance: string | null
  dob_date: string | null // ISO date string "YYYY-MM-DD"
  // Career averages
  slpm: number | null
  str_acc: string | null
  sapm: number | null
  str_def: string | null
  td_avg: number | null
  td_acc: string | null
  td_def: string | null
  sub_avg: number | null
  // Record (UFC bouts only)
  wins: number | null
  losses: number | null
  draws: number | null
  no_contests: number | null
  avg_fight_time_seconds: number | null
  // All-time career record (includes non-UFC bouts, null until bulk scrape runs)
  career_wins: number | null
  career_losses: number | null
  career_draws: number | null
}

// ── Events ───────────────────────────────────────────────────────────────────

export interface EventResponse {
  id: string
  name: string | null
  event_date: string | null // ISO date string
  location: string | null
}

export interface EventListResponse {
  data: EventResponse[]
  meta: PaginationMeta
}

export interface EventWithFightsResponse extends EventResponse {
  fights: FightListItem[]
}

// ── Fights ───────────────────────────────────────────────────────────────────

export interface FightStatsResponse {
  fighter_id: string | null
  round: string | null
  kd_int: number | null
  sig_str_landed: number | null
  sig_str_attempted: number | null
  sig_str_pct: number | null
  total_str_landed: number | null
  total_str_attempted: number | null
  td_landed: number | null
  td_attempted: number | null
  td_pct: number | null
  ctrl_seconds: number | null
  head_landed: number | null
  head_attempted: number | null
  body_landed: number | null
  body_attempted: number | null
  leg_landed: number | null
  leg_attempted: number | null
  distance_landed: number | null
  distance_attempted: number | null
  clinch_landed: number | null
  clinch_attempted: number | null
  ground_landed: number | null
  ground_attempted: number | null
}

export interface FightListItem {
  id: string
  event_id: string | null
  bout: string | null
  fighter_a_id: string | null
  fighter_b_id: string | null
  weight_class: string | null
  method: string | null
  round: number | null
  winner_id: string | null
  is_title_fight: boolean | null
}

export interface FightListResponse {
  data: FightListItem[]
  meta: PaginationMeta
}

export interface FightResponse {
  id: string
  event_id: string | null
  bout: string | null
  fighter_a_id: string | null
  fighter_b_id: string | null
  winner_id: string | null
  weight_class: string | null
  method: string | null
  round: number | null
  time: string | null
  is_title_fight: boolean | null
  is_interim_title: boolean | null
  is_championship_rounds: boolean | null
  total_fight_time_seconds: number | null
  stats: FightStatsResponse[]
}

// ── Analytics ────────────────────────────────────────────────────────────────

export interface StyleEvolutionPoint {
  year: number
  ko_tko_rate: number
  submission_rate: number
  decision_rate: number
  total_fights: number
  weight_class: string | null
}

export interface StyleEvolutionResponse {
  data: StyleEvolutionPoint[]
  weight_class: string | null
}

export interface EnduranceRoundData {
  round: number
  avg_sig_str_landed: number | null
  avg_sig_str_pct: number | null
  avg_ctrl_seconds: number | null
  avg_kd: number | null
  fight_count: number | null
}

export interface FighterEnduranceResponse {
  fighter_id: string
  fighter_name: string | null
  rounds: EnduranceRoundData[]
  note: string | null
}

// ── Upcoming Events ──────────────────────────────────────────────────────────

export interface UpcomingEventListItem {
  id: string
  event_name: string | null
  event_date: string | null
  location: string | null
  is_numbered: boolean | null
  fight_count: number
}

export interface UpcomingEventListResponse {
  data: UpcomingEventListItem[]
}

export interface UpcomingFightPrediction {
  win_prob_a: number | null
  win_prob_b: number | null
  method_ko_tko: number | null
  method_sub: number | null
  method_dec: number | null
  model_version: string | null
  features_json: Record<string, number | null> | null
}

export interface UpcomingFight {
  id: string
  event_id: string
  fighter_a_name: string | null
  fighter_b_name: string | null
  fighter_a_id: string | null
  fighter_b_id: string | null
  weight_class: string | null
  is_title_fight: boolean
  prediction: UpcomingFightPrediction | null
}

export interface UpcomingEventWithFights extends UpcomingEventListItem {
  fights: UpcomingFight[]
}

// ── Past Predictions (Model Scorecard) ───────────────────────────────────────

export interface PastPredictionItem {
  fight_id: string
  event_id: string | null
  event_name: string | null
  event_date: string | null
  fighter_a_id: string | null
  fighter_b_id: string | null
  fighter_a_name: string | null
  fighter_b_name: string | null
  weight_class: string | null
  win_prob_a: number | null
  win_prob_b: number | null
  pred_method_ko_tko: number | null
  pred_method_sub: number | null
  pred_method_dec: number | null
  predicted_winner_id: string | null
  predicted_method: string | null
  actual_winner_id: string | null
  actual_method: string | null
  is_correct: boolean | null
  confidence: number | null
  is_upset: boolean | null
}

export interface PastPredictionSummary {
  total_fights: number
  correct: number
  accuracy: number
  high_conf_fights: number
  high_conf_correct: number
  high_conf_accuracy: number
  date_from: string
  date_to: string
  available_years: number[]
}

export interface PastPredictionsResponse {
  summary: PastPredictionSummary
  recent: PastPredictionItem[]
}

export interface PastPredictionEventItem {
  event_id: string
  event_name: string | null
  event_date: string | null
  fight_count: number
  correct_count: number
  accuracy: number
}

export interface PastPredictionEventsResponse {
  data: PastPredictionEventItem[]
  total: number
  total_pages: number
  page: number
  page_size: number
}

export interface PastPredictionEventDetail extends PastPredictionEventItem {
  fights: PastPredictionItem[]
}

export interface PastPredictionFightsResponse {
  data: PastPredictionItem[]
  total: number
  total_pages: number
  page: number
  page_size: number
}

// ── Predictions ──────────────────────────────────────────────────────────────

export interface PredictionRequest {
  fighter_a_id: string
  fighter_b_id: string
  weight_class?: string
  fighter_a_weight_lbs?: number
  fighter_a_reach_inches?: number
  fighter_a_age?: number
  fighter_b_weight_lbs?: number
  fighter_b_reach_inches?: number
  fighter_b_age?: number
}

export interface MethodProbabilities {
  ko_tko: number
  submission: number
  decision: number
}

export interface PredictionResponse {
  fighter_a_id: string
  fighter_b_id: string
  predicted_winner_id: string
  win_probability: number
  confidence: number
  method_probabilities: MethodProbabilities
  similar_fight_ids: string[]
}
