// Shared model-feature metadata and formatting for the fight prediction breakdowns.
// Used by both UpcomingFightPage and PastPredictionFightPage. Do not duplicate this
// table into a page file - drift between copies is what this module exists to prevent.

export interface FeatureMeta {
  label: string
  higherIsBetter: boolean
}

export const FEATURE_META: Record<string, FeatureMeta> = {
  diff_ko_rate:                { label: 'KO/TKO finish rate',                       higherIsBetter: true  },
  diff_ewa_kd:                 { label: 'Knockdowns — recent (weighted)',            higherIsBetter: true  },
  diff_career_avg_kd:          { label: 'Knockdowns per fight (career)',             higherIsBetter: true  },
  diff_td_def_rate:            { label: 'Takedown defense %',                        higherIsBetter: true  },
  diff_roll3_sig_str_landed:   { label: 'Avg sig. strikes landed (last 3 fights)',   higherIsBetter: true  },
  diff_roll7_total_str_landed: { label: 'Avg total strikes landed (last 7 fights)',  higherIsBetter: true  },
  diff_roll7_sig_str_pct:      { label: 'Avg sig. strike accuracy (last 7 fights)',  higherIsBetter: true  },
  diff_career_avg_ctrl_s:      { label: 'Avg control time per fight (career)',       higherIsBetter: true  },
  diff_roll3_ctrl_s:           { label: 'Avg control time (last 3 fights)',          higherIsBetter: true  },
  diff_days_in_weight_class:   { label: 'Experience in weight class',                higherIsBetter: true  },
  diff_career_length_days:     { label: 'Career length',                             higherIsBetter: true  },
  diff_roll5_td_pct:           { label: 'Avg takedown accuracy (last 5 fights)',     higherIsBetter: true  },
  diff_roll7_td_landed:        { label: 'Avg takedowns landed (last 7 fights)',      higherIsBetter: true  },
  diff_aggression_score:       { label: 'Aggression score',                          higherIsBetter: true  },
  diff_defense_score:          { label: 'Defense score',                             higherIsBetter: true  },
  diff_grappling_ratio:        { label: 'Grappling ratio',                           higherIsBetter: true  },
  diff_roll7_sig_str_att:      { label: 'Avg sig. strike volume (last 7 fights)',    higherIsBetter: true  },
  diff_career_avg_td_attempted:{ label: 'Avg takedown attempts per fight (career)',  higherIsBetter: true  },
  win_streak_diff:             { label: 'Win streak',                                higherIsBetter: true  },
  win_rate_diff:               { label: 'Overall win rate',                          higherIsBetter: true  },
  reach_diff_inches:           { label: 'Reach advantage (in)',                      higherIsBetter: true  },
  diff_sapm:                   { label: 'Strikes absorbed per min',                  higherIsBetter: false },
  diff_age_at_fight:           { label: 'Age (younger is better)',                   higherIsBetter: false },
  loss_streak_diff:            { label: 'Loss streak',                               higherIsBetter: false },
  diff_decision_rate:          { label: 'Decision rate',                             higherIsBetter: false },
}

/** Feature keys that are metadata, not comparative signals - excluded from the breakdown. */
export const FEATURE_SKIP = new Set(['is_title_fight', 'is_women_division', 'weight_class'])

/** Format a raw feature-differential value for display, based on its label's unit. */
export function fmtFeature(label: string, raw: number): string {
  if (label.includes('%') || label.includes('rate') || label.includes('accuracy') || label.includes('win rate')) {
    return `${(Math.abs(raw) * 100).toFixed(1)}%`
  }
  if (label.includes('(in)')) return `${Math.abs(raw).toFixed(1)} in`
  if (label.includes('control time') || label.includes('Control time')) return `${Math.abs(raw).toFixed(0)}s`
  if (label.includes('Experience') || label.includes('Career length') || label.includes('younger')) {
    return `${(Math.abs(raw) / 365).toFixed(1)} yrs`
  }
  return Math.abs(raw).toFixed(2)
}

export interface FavoredFeature {
  label: string
  display: string
}

/**
 * Split a fight's feature_json into the metrics favoring fighter A vs fighter B,
 * each sorted by descending magnitude. A positive adjusted value favors A.
 */
export function splitFavoredFeatures(
  features: Record<string, unknown>,
): { favA: FavoredFeature[]; favB: FavoredFeature[] } {
  const favA: FavoredFeature[] = []
  const favB: FavoredFeature[] = []

  Object.entries(features)
    .filter(([k, v]) => !FEATURE_SKIP.has(k) && v != null && k in FEATURE_META)
    .map(([k, v]) => {
      const meta = FEATURE_META[k]
      const adjusted = meta.higherIsBetter ? (v as number) : -(v as number)
      return { raw: v as number, adjusted, meta }
    })
    .filter((e) => Math.abs(e.adjusted) > 0.001)
    .sort((a, b) => Math.abs(b.adjusted) - Math.abs(a.adjusted))
    .forEach((e) => {
      const item = { label: e.meta.label, display: fmtFeature(e.meta.label, e.raw) }
      if (e.adjusted > 0) favA.push(item)
      else favB.push(item)
    })

  return { favA, favB }
}
