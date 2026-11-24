import { describe, it, expect } from 'vitest'
import type { FightResponse, FighterResponse, PastPredictionItem } from '@t/api'
import { resolveFightSides, orientById } from './fightSides'

const STRICKLAND = '0d801111'
const ADESANYA = '1338e2c7'

/**
 * UFC 293, Sep 9 2023: Sean Strickland beat Israel Adesanya by unanimous
 * decision. Taken from the live API on 2026-11-24.
 *
 * fight_details lists Adesanya first. The backfilled prediction lists
 * Strickland first. The page used to take ids from the first and names from
 * the second, so it printed "Israel Adesanya" as the winner and put
 * Adesanya's profile link and stats under Strickland's name.
 */
function ufc293Fight(overrides: Partial<FightResponse> = {}): FightResponse {
  return {
    id: '7f16e772',
    event_id: 'ece28074',
    bout: 'Israel Adesanya vs. Sean Strickland',
    fighter_a_id: ADESANYA,
    fighter_b_id: STRICKLAND,
    fighter_a_name: 'Israel Adesanya',
    fighter_b_name: 'Sean Strickland',
    winner_id: STRICKLAND,
    weight_class: 'Middleweight',
    method: 'Decision - Unanimous',
    round: 5,
    time: '5:00',
    is_title_fight: true,
    is_interim_title: false,
    is_championship_rounds: true,
    total_fight_time_seconds: 1500,
    stats: [],
    ...overrides,
  }
}

function ufc293Prediction(): PastPredictionItem {
  return {
    fight_id: '7f16e772',
    event_id: 'ece28074',
    event_name: 'UFC 293: Adesanya vs. Strickland',
    event_date: '2023-09-09',
    fighter_a_id: STRICKLAND,
    fighter_b_id: ADESANYA,
    fighter_a_name: 'Sean Strickland',
    fighter_b_name: 'Israel Adesanya',
    weight_class: 'Middleweight',
    is_title_fight: true,
    is_interim_title: false,
    win_prob_a: 0.503445602101234,
    win_prob_b: 0.496554397898766,
    pred_method_ko_tko: 0.361423263493525,
    pred_method_sub: 0.263121645433673,
    pred_method_dec: 0.375455091072801,
    predicted_winner_id: STRICKLAND,
    predicted_method: 'Decision',
    actual_winner_id: STRICKLAND,
    actual_method: 'Decision - Unanimous',
    is_correct: true,
    confidence: 0.00689120420246736,
    is_upset: false,
    model_version: 'win_loss_v1',
    features_json: null,
    prediction_source: 'backfill',
    pre_fight_predicted_at: null,
  } as PastPredictionItem
}

function profile(id: string, first: string, last: string): FighterResponse {
  return { id, first_name: first, last_name: last } as FighterResponse
}

describe('resolveFightSides - UFC 293, Strickland vs. Adesanya', () => {
  it('names Strickland as the winner', () => {
    const sides = resolveFightSides(ufc293Fight(), ufc293Prediction())
    expect(sides.winner).toEqual({ id: STRICKLAND, name: 'Sean Strickland' })
  })

  it("keeps the prediction's order, with each name on its own id", () => {
    const sides = resolveFightSides(ufc293Fight(), ufc293Prediction())
    // Left column is the prediction's fighter A, so the 50.3% sits under him.
    expect(sides.a).toEqual({ id: STRICKLAND, name: 'Sean Strickland' })
    expect(sides.b).toEqual({ id: ADESANYA, name: 'Israel Adesanya' })
  })

  it('puts each fighter profile under that fighter, not under the other one', () => {
    const sides = resolveFightSides(ufc293Fight(), ufc293Prediction())
    // Profiles arrive in fight_details order: Adesanya first.
    const { a, b } = orientById(sides, [
      [ADESANYA, profile(ADESANYA, 'Israel', 'Adesanya')],
      [STRICKLAND, profile(STRICKLAND, 'Sean', 'Strickland')],
    ])
    expect(a?.id).toBe(STRICKLAND)
    expect(b?.id).toBe(ADESANYA)
  })

  it('still names the winner correctly against an API without the joined names', () => {
    const fight = ufc293Fight({ fighter_a_name: undefined, fighter_b_name: undefined })
    const sides = resolveFightSides(fight, ufc293Prediction())
    expect(sides.winner?.name).toBe('Sean Strickland')
    expect(sides.a.name).toBe('Sean Strickland')
  })
})

describe('resolveFightSides - other cases', () => {
  it('uses fight_details order when there is no prediction', () => {
    const sides = resolveFightSides(ufc293Fight(), null)
    expect(sides.a).toEqual({ id: ADESANYA, name: 'Israel Adesanya' })
    expect(sides.b).toEqual({ id: STRICKLAND, name: 'Sean Strickland' })
    expect(sides.winner?.name).toBe('Sean Strickland')
  })

  it('never reads a name out of the bout string', () => {
    // A bout string that disagrees with the ids must not leak into the page.
    const fight = ufc293Fight({
      bout: 'Sean Strickland vs. Israel Adesanya',
      fighter_a_name: null,
      fighter_b_name: null,
    })
    const sides = resolveFightSides(fight, null)
    expect(sides.a).toEqual({ id: ADESANYA, name: '—' })
    expect(sides.winner).toEqual({ id: STRICKLAND, name: '—' })
  })

  it('has no winner for a draw or no contest', () => {
    const sides = resolveFightSides(ufc293Fight({ winner_id: null }), ufc293Prediction())
    expect(sides.winner).toBeNull()
  })

  it('prefers the fighter_details name over the prediction row copy', () => {
    // Some prediction rows store mononym fighters with a mangled name.
    const pred = { ...ufc293Prediction(), fighter_a_name: 'Sean Strickland vs. Israel Adesanya' }
    const sides = resolveFightSides(ufc293Fight(), pred)
    expect(sides.a.name).toBe('Sean Strickland')
  })
})
