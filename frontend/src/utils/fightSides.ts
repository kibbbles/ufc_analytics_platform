import type { FightListItem, FightResponse, PastPredictionItem } from '@t/api'
import { EMPTY } from './format'

export interface FightSide {
  id: string | null
  name: string
}

export interface FightSides {
  /** Left column. The prediction's fighter A when there is a prediction. */
  a: FightSide
  /** Right column. */
  b: FightSide
  /** Who won, by id. Null for a draw or no contest. */
  winner: FightSide | null
}

/**
 * Decides which fighter sits on each side of a past fight page, and names
 * every fighter by id.
 *
 * Two sources describe the same fight, and they can list the two fighters in
 * opposite order: fight_details follows the UFCStats bout, while a backfilled
 * prediction follows its training row (UFC 293 stores Adesanya first in one
 * and Strickland first in the other). Pairing one source's ids with the other
 * source's names put the loser's name on the winner and Adesanya's stats under
 * Strickland's name. So the order comes from one source only, and a name is
 * only ever looked up by the id it belongs to, never taken from a position.
 *
 * The order follows the prediction when there is one, because its win
 * probabilities and feature differentials are written in that order.
 */
export function resolveFightSides(
  fight: FightResponse,
  pred: PastPredictionItem | null | undefined,
): FightSides {
  const names = new Map<string, string>()
  const addName = (id: string | null | undefined, name: string | null | undefined) => {
    if (id && name && !names.has(id)) names.set(id, name)
  }
  // fighter_details names first: they are the canonical record. The prediction
  // row's copies fill in only when the API did not send one.
  addName(fight.fighter_a_id, fight.fighter_a_name)
  addName(fight.fighter_b_id, fight.fighter_b_name)
  addName(pred?.fighter_a_id, pred?.fighter_a_name)
  addName(pred?.fighter_b_id, pred?.fighter_b_name)

  const side = (id: string | null | undefined): FightSide => ({
    id: id ?? null,
    name: (id && names.get(id)) || EMPTY,
  })

  const fromPred = Boolean(pred?.fighter_a_id && pred?.fighter_b_id)
  const aId = fromPred ? pred!.fighter_a_id : fight.fighter_a_id
  const bId = fromPred ? pred!.fighter_b_id : fight.fighter_b_id

  return {
    a: side(aId),
    b: side(bId),
    winner: fight.winner_id ? side(fight.winner_id) : null,
  }
}

/**
 * Looks up per-fighter data (profiles, recent fights) for each side by id.
 * The data is fetched in fight_details order, which may be the reverse of the
 * page's order, so it is never matched up by position.
 */
export function orientById<T>(
  sides: FightSides,
  entries: ReadonlyArray<readonly [string | null, T | null | undefined]>,
): { a: T | null; b: T | null } {
  const byId = new Map<string, T>()
  for (const [id, value] of entries) {
    if (id && value != null) byId.set(id, value)
  }
  return {
    a: (sides.a.id && byId.get(sides.a.id)) || null,
    b: (sides.b.id && byId.get(sides.b.id)) || null,
  }
}

/** A fight-list row's two fighters, each named by its own id, and who won. */
export interface ListedFight {
  a: FightSide
  b: FightSide
  /** 'a' or 'b' when the winner is one of the two ids; null for a draw, a no contest or an unknown id. */
  won: 'a' | 'b' | null
}

/**
 * Names both fighters of a fight-list row from the names the API joined to
 * each id. The BOUT string is never split: its order is the UFCStats listing,
 * and matching its halves to ids by position is the mistake that put the
 * wrong winner on past prediction pages.
 */
export function listedFight(fight: FightListItem): ListedFight {
  const won =
    fight.winner_id == null
      ? null
      : fight.winner_id === fight.fighter_a_id
        ? 'a'
        : fight.winner_id === fight.fighter_b_id
          ? 'b'
          : null
  return {
    a: { id: fight.fighter_a_id, name: fight.fighter_a_name || EMPTY },
    b: { id: fight.fighter_b_id, name: fight.fighter_b_name || EMPTY },
    won,
  }
}

/** The other fighter in a row, seen from viewingFighterId. Null when that id is in neither seat. */
export function opponentOf(fight: FightListItem, viewingFighterId: string): FightSide | null {
  const { a, b } = listedFight(fight)
  if (a.id === viewingFighterId) return b
  if (b.id === viewingFighterId) return a
  return null
}
