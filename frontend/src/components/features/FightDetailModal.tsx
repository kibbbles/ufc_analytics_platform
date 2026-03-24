import { useEffect } from 'react'
import type { UpcomingFight } from '@t/api'

interface Props {
  fight: UpcomingFight
  onClose: () => void
}

// Human-readable labels + whether a positive diff favours Fighter A
const FEATURE_META: Record<string, { label: string; higherIsBetter: boolean }> = {
  diff_ko_rate:                { label: 'KO/TKO finish rate',                  higherIsBetter: true  },
  diff_ewa_kd:                 { label: 'Knockdowns — recent (weighted)',       higherIsBetter: true  },
  diff_career_avg_kd:          { label: 'Knockdowns per fight (career)',        higherIsBetter: true  },
  diff_td_def_rate:            { label: 'Takedown defense %',                   higherIsBetter: true  },
  diff_roll3_sig_str_landed:   { label: 'Avg sig. strikes landed (last 3 fights)',  higherIsBetter: true  },
  diff_roll7_total_str_landed: { label: 'Avg total strikes landed (last 7 fights)', higherIsBetter: true  },
  diff_roll7_sig_str_pct:      { label: 'Avg sig. strike accuracy (last 7 fights)', higherIsBetter: true  },
  diff_career_avg_ctrl_s:      { label: 'Avg control time per fight (career)',      higherIsBetter: true  },
  diff_roll3_ctrl_s:           { label: 'Avg control time (last 3 fights)',         higherIsBetter: true  },
  diff_days_in_weight_class:   { label: 'Experience in weight class',               higherIsBetter: true  },
  diff_career_length_days:     { label: 'Career length',                            higherIsBetter: true  },
  diff_roll5_td_pct:           { label: 'Avg takedown accuracy (last 5 fights)',    higherIsBetter: true  },
  diff_roll7_td_landed:        { label: 'Avg takedowns landed (last 7 fights)',     higherIsBetter: true  },
  diff_aggression_score:       { label: 'Aggression score',                         higherIsBetter: true  },
  diff_defense_score:          { label: 'Defense score',                            higherIsBetter: true  },
  diff_grappling_ratio:        { label: 'Grappling ratio',                          higherIsBetter: true  },
  diff_roll7_sig_str_att:      { label: 'Avg sig. strike volume (last 7 fights)',   higherIsBetter: true  },
  diff_career_avg_td_attempted:{ label: 'Avg takedown attempts per fight (career)', higherIsBetter: true  },
  win_streak_diff:             { label: 'Win streak',                           higherIsBetter: true  },
  win_rate_diff:               { label: 'Overall win rate',                     higherIsBetter: true  },
  reach_diff_inches:           { label: 'Reach advantage (in)',                 higherIsBetter: true  },
  // Inverted: lower is better for Fighter A
  diff_sapm:                   { label: 'Strikes absorbed per min',             higherIsBetter: false },
  diff_age_at_fight:           { label: 'Age (younger is better)',              higherIsBetter: false },
  loss_streak_diff:            { label: 'Loss streak',                          higherIsBetter: false },
  diff_decision_rate:          { label: 'Decision rate',                        higherIsBetter: false },
}

const SKIP = new Set(['is_title_fight', 'is_women_division', 'weight_class'])

function pct(v: number | null): string {
  if (v == null) return '—'
  return `${(v * 100).toFixed(1)}%`
}

function fmt(label: string, raw: number): string {
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

export default function FightDetailModal({ fight, onClose }: Props) {
  const { fighter_a_name, fighter_b_name, weight_class, is_title_fight, prediction } = fight

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const features = prediction?.features_json ?? null

  // Split features into advantages for each fighter
  const favA: { label: string; display: string }[] = []
  const favB: { label: string; display: string }[] = []

  if (features) {
    const entries = Object.entries(features)
      .filter(([k, v]) => !SKIP.has(k) && v != null && k in FEATURE_META)
      .map(([k, v]) => {
        const meta = FEATURE_META[k]
        const adjusted = meta.higherIsBetter ? (v as number) : -(v as number)
        return { key: k, raw: v as number, adjusted, meta }
      })
      .filter(e => Math.abs(e.adjusted) > 0.001)
      .sort((a, b) => Math.abs(b.adjusted) - Math.abs(a.adjusted))

    for (const e of entries) {
      const item = { label: e.meta.label, display: fmt(e.meta.label, e.raw) }
      if (e.adjusted > 0) favA.push(item)
      else favB.push(item)
    }
  }

  const aWins = (prediction?.win_prob_a ?? 0) >= (prediction?.win_prob_b ?? 0)

  const methods = prediction ? [
    { label: 'KO/TKO', value: prediction.method_ko_tko },
    { label: 'Sub',    value: prediction.method_sub },
    { label: 'Dec',    value: prediction.method_dec },
  ] : []
  const topMethod = methods.reduce(
    (best, m) => ((m.value ?? 0) > (best.value ?? 0) ? m : best),
    { label: '', value: null as number | null }
  ).label

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg overflow-y-auto rounded-xl border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] shadow-2xl max-h-[90vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 border-b border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-5 py-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--color-text-muted)]">
                {weight_class && <span>{weight_class}</span>}
                {is_title_fight && (
                  <span className="rounded-sm bg-[var(--color-primary)] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                    Title
                  </span>
                )}
              </div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className={`font-bold ${aWins ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                  {fighter_a_name ?? '—'}
                </span>
                <span className="text-xs text-[var(--color-text-muted)]">vs</span>
                <span className={`font-bold ${!aWins ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                  {fighter_b_name ?? '—'}
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="shrink-0 rounded-md p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]"
              aria-label="Close"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Win probs */}
          {prediction && (
            <div className="mt-3 flex justify-between font-mono text-sm tabular-nums">
              <div>
                <span className={`text-2xl font-bold ${aWins ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                  {pct(prediction.win_prob_a)}
                </span>
              </div>
              <div className="flex gap-3 font-mono text-xs tabular-nums">
                {methods.map(m => (
                  <span
                    key={m.label}
                    className={m.label === topMethod
                      ? 'font-bold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                      : 'text-[var(--color-text-muted)] opacity-50'}
                  >
                    {m.label} {pct(m.value)}
                  </span>
                ))}
              </div>
              <div className="text-right">
                <span className={`text-2xl font-bold ${!aWins ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                  {pct(prediction.win_prob_b)}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Feature breakdown */}
        <div className="px-5 py-4">
          {!features ? (
            <p className="text-center text-sm text-[var(--color-text-muted)]">No feature data available.</p>
          ) : (
            <>
              <p className="mb-3 text-center text-sm">
                <span className="font-bold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
                  {aWins ? favA.length : favB.length} of {favA.length + favB.length}
                </span>
                <span className="text-[var(--color-text-muted)]"> metrics favour </span>
                <span className="font-semibold text-[var(--color-primary)]">
                  {(aWins ? fighter_a_name : fighter_b_name)?.split(' ').pop()}
                </span>
              </p>
            <div className="grid grid-cols-2 gap-4">
              {/* Fighter A advantages */}
              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
                  Favours {fighter_a_name?.split(' ').pop() ?? 'A'}
                </h3>
                {favA.slice(0, 7).map(({ label, display }) => (
                  <div key={label} className="mb-1.5">
                    <div className="text-xs font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
                      +{display}
                    </div>
                    <div className="text-[11px] text-[var(--color-text-muted)]">{label}</div>
                  </div>
                ))}
                {favA.length === 0 && (
                  <p className="text-xs text-[var(--color-text-muted)]">No clear advantages</p>
                )}
              </div>

              {/* Fighter B advantages */}
              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
                  Favours {fighter_b_name?.split(' ').pop() ?? 'B'}
                </h3>
                {favB.slice(0, 7).map(({ label, display }) => (
                  <div key={label} className="mb-1.5">
                    <div className="text-xs font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
                      +{display}
                    </div>
                    <div className="text-[11px] text-[var(--color-text-muted)]">{label}</div>
                  </div>
                ))}
                {favB.length === 0 && (
                  <p className="text-xs text-[var(--color-text-muted)]">No clear advantages</p>
                )}
              </div>
            </div>
            </>
          )}
          <p className="mt-4 text-center text-[10px] text-[var(--color-text-muted)]">
            Values are per-fight averages (Fighter A − Fighter B). Sorted by magnitude. Model: {prediction?.model_version ?? 'win_loss_v1'}.
          </p>
        </div>
      </div>
    </div>
  )
}
