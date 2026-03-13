import { Link, useParams } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { upcomingService } from '@services/upcomingService'
import { fightersService } from '@services/fightersService'
import { fightsService } from '@services/fightsService'
import { Card, LoadingSkeleton } from '@components/common'
import type { FighterResponse, FightListItem, UpcomingFight } from '@t/api'
import { inchesToFeet, formatDate } from '@utils/format'

// ── Feature metadata (keeps labels + sign convention) ────────────────────────

const FEATURE_META: Record<string, { label: string; higherIsBetter: boolean }> = {
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

const SKIP = new Set(['is_title_fight', 'is_women_division', 'weight_class'])

// ── Formatters ────────────────────────────────────────────────────────────────

function pct(v: number | null): string {
  if (v == null) return '—'
  return `${(v * 100).toFixed(1)}%`
}

function fmtFeature(label: string, raw: number): string {
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

function heightDisplay(inches: number | null): string {
  return inches != null ? inchesToFeet(inches) : '—'
}


function fmtTime(seconds: number | null): string {
  if (seconds == null) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

// ── Sub-components ────────────────────────────────────────────────────────────

function TaleOfTape({
  a,
  b,
  nameA,
  nameB,
}: {
  a: FighterResponse | null
  b: FighterResponse | null
  nameA: string
  nameB: string
}) {
  const hasCareer = (a?.career_wins != null) || (b?.career_wins != null)
  const record = (f: FighterResponse | null) => {
    if (!f) return '—'
    if (f.career_wins != null) return `${f.career_wins}-${f.career_losses ?? 0}-${f.career_draws ?? 0}`
    return `${f.wins ?? 0}-${f.losses ?? 0}-${f.draws ?? 0}`
  }

  const rows: { label: string; valA: string; valB: string }[] = [
    { label: hasCareer ? 'Record' : 'Record (UFC)',  valA: record(a),                                                          valB: record(b)                                                          },
    { label: 'Avg. Fight',   valA: fmtTime(a?.avg_fight_time_seconds ?? null),                         valB: fmtTime(b?.avg_fight_time_seconds ?? null)                         },
    { label: 'Height',       valA: heightDisplay(a?.height_inches ?? null),                             valB: heightDisplay(b?.height_inches ?? null)                             },
    { label: 'Weight',       valA: a?.weight_lbs != null ? `${a.weight_lbs} lbs` : '—',               valB: b?.weight_lbs != null ? `${b.weight_lbs} lbs` : '—'               },
    { label: 'Reach',        valA: a?.reach_inches != null ? `${a.reach_inches}"` : '—',               valB: b?.reach_inches != null ? `${b.reach_inches}"` : '—'               },
    { label: 'Stance',       valA: a?.stance ?? '—',                                                   valB: b?.stance ?? '—'                                                   },
    { label: 'DOB',          valA: a?.dob_date ? formatDate(String(a.dob_date)) : '—',                 valB: b?.dob_date ? formatDate(String(b.dob_date)) : '—'                 },
  ]

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
          <th className="pb-2 text-left font-medium">{nameA}</th>
          <th className="pb-2 text-center font-medium"></th>
          <th className="pb-2 text-right font-medium">{nameB}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ label, valA, valB }) => (
          <tr key={label} className="border-t border-[var(--color-border)]">
            <td className="py-2 font-mono tabular-nums">{valA}</td>
            <td className="py-2 text-center text-xs text-[var(--color-text-muted)]">{label}</td>
            <td className="py-2 text-right font-mono tabular-nums">{valB}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function RecentFightMini({
  fights,
  viewingFighterId,
}: {
  fights: FightListItem[]
  viewingFighterId: string
}) {
  return (
    <div className="space-y-2">
      {fights.map((f) => {
        const parts = (f.bout ?? '').split(' vs. ')
        const isA = f.fighter_a_id === viewingFighterId
        const opponentRaw = (isA ? parts[1] : parts[0] ?? '').trim()
        const opponentLastName = opponentRaw.split(' ').at(-1) ?? '—'
        const opponentId = isA ? f.fighter_b_id : f.fighter_a_id
        const isWin = f.winner_id === viewingFighterId
        const isLoss = f.winner_id !== null && f.winner_id !== viewingFighterId
        return (
          <div key={f.id} className="flex items-center gap-2 text-sm">
            <span
              className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-bold tabular-nums ${
                isWin
                  ? 'bg-green-500/15 text-green-600 dark:text-green-400'
                  : isLoss
                  ? 'bg-red-500/15 text-red-600 dark:text-red-400'
                  : 'bg-[var(--color-border)] text-[var(--color-text-muted)]'
              }`}
            >
              {isWin ? 'W' : isLoss ? 'L' : '—'}
            </span>
            {opponentId ? (
              <Link
                to={`/fighters/${opponentId}`}
                className="font-medium hover:text-[var(--color-primary)] transition-colors"
              >
                {opponentLastName}
              </Link>
            ) : (
              <span className="font-medium text-[var(--color-text-muted)]">{opponentLastName}</span>
            )}
          </div>
        )
      })}
    </div>
  )
}

function FeatureBreakdown({ fight }: { fight: UpcomingFight }) {
  const features = fight.prediction?.features_json ?? null
  const nameA = fight.fighter_a_name?.split(' ').pop() ?? 'A'
  const nameB = fight.fighter_b_name?.split(' ').pop() ?? 'B'

  if (!features) return null

  const favA: { label: string; display: string }[] = []
  const favB: { label: string; display: string }[] = []

  const entries = Object.entries(features)
    .filter(([k, v]) => !SKIP.has(k) && v != null && k in FEATURE_META)
    .map(([k, v]) => {
      const meta = FEATURE_META[k]
      const adjusted = meta.higherIsBetter ? (v as number) : -(v as number)
      return { key: k, raw: v as number, adjusted, meta }
    })
    .filter((e) => Math.abs(e.adjusted) > 0.001)
    .sort((a, b) => Math.abs(b.adjusted) - Math.abs(a.adjusted))

  for (const e of entries) {
    const item = { label: e.meta.label, display: fmtFeature(e.meta.label, e.raw) }
    if (e.adjusted > 0) favA.push(item)
    else favB.push(item)
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
          Favours {nameA}
        </h3>
        {favA.length === 0 ? (
          <p className="text-xs text-[var(--color-text-muted)]">No clear advantages</p>
        ) : (
          favA.slice(0, 8).map(({ label, display }) => (
            <div key={label} className="mb-2">
              <div className="text-xs font-semibold text-[var(--color-primary)]">+{display}</div>
              <div className="text-[11px] leading-snug text-[var(--color-text-muted)]">{label}</div>
            </div>
          ))
        )}
      </div>
      <div>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
          Favours {nameB}
        </h3>
        {favB.length === 0 ? (
          <p className="text-xs text-[var(--color-text-muted)]">No clear advantages</p>
        ) : (
          favB.slice(0, 8).map(({ label, display }) => (
            <div key={label} className="mb-2">
              <div className="text-xs font-semibold text-[var(--color-primary)]">+{display}</div>
              <div className="text-[11px] leading-snug text-[var(--color-text-muted)]">{label}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function UpcomingFightPage() {
  const { id } = useParams<{ id: string }>()

  const { data: fight, loading, error } = useApi(
    () => upcomingService.getFightById(id!),
    [id],
  )

  const { data: fighterA } = useApi(
    () =>
      fight?.fighter_a_id
        ? fightersService.getById(fight.fighter_a_id)
        : Promise.resolve(null),
    [fight?.fighter_a_id],
  )

  const { data: fighterB } = useApi(
    () =>
      fight?.fighter_b_id
        ? fightersService.getById(fight.fighter_b_id)
        : Promise.resolve(null),
    [fight?.fighter_b_id],
  )

  const { data: fightsA } = useApi(
    () =>
      fight?.fighter_a_id
        ? fightsService.getList({ fighter_id: fight.fighter_a_id, page_size: 5 })
        : Promise.resolve(null),
    [fight?.fighter_a_id],
  )

  const { data: fightsB } = useApi(
    () =>
      fight?.fighter_b_id
        ? fightsService.getList({ fighter_id: fight.fighter_b_id, page_size: 5 })
        : Promise.resolve(null),
    [fight?.fighter_b_id],
  )

  const pred = fight?.prediction
  const aWins = (pred?.win_prob_a ?? 0) >= (pred?.win_prob_b ?? 0)
  const nameA = fight?.fighter_a_name ?? '—'
  const nameB = fight?.fighter_b_name ?? '—'

  return (
    <div className="mx-auto max-w-[640px]">
      <Link
        to="/upcoming"
        className="inline-flex items-center gap-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors mb-6"
      >
        ← Upcoming
      </Link>

      {loading && (
        <div className="space-y-4">
          <LoadingSkeleton lines={2} />
          <LoadingSkeleton lines={4} />
          <LoadingSkeleton lines={6} />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {fight && !loading && (
        <div className="space-y-4">
          {/* Header: fighter names + weight class below */}
          <div className="text-center">
            <div className="flex items-center justify-center gap-3 flex-wrap">
              {fight.fighter_a_id ? (
                <Link
                  to={`/fighters/${fight.fighter_a_id}`}
                  className={`text-xl font-bold hover:text-[var(--color-primary)] transition-colors ${
                    aWins
                      ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                      : 'text-[var(--color-text-muted)]'
                  }`}
                >
                  {nameA}
                </Link>
              ) : (
                <span className={`text-xl font-bold ${aWins ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                  {nameA}
                </span>
              )}
              <span className="text-sm text-[var(--color-text-muted)]">vs</span>
              {fight.fighter_b_id ? (
                <Link
                  to={`/fighters/${fight.fighter_b_id}`}
                  className={`text-xl font-bold hover:text-[var(--color-primary)] transition-colors ${
                    !aWins
                      ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                      : 'text-[var(--color-text-muted)]'
                  }`}
                >
                  {nameB}
                </Link>
              ) : (
                <span className={`text-xl font-bold ${!aWins ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                  {nameB}
                </span>
              )}
            </div>
            {(fight.weight_class || fight.is_title_fight) && (
              <div className="mt-2 flex justify-center gap-2">
                {fight.weight_class && (
                  <span className="text-xs text-[var(--color-text-muted)]">{fight.weight_class}</span>
                )}
                {fight.is_title_fight && (
                  <span className="rounded-sm bg-[var(--color-primary)] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                    Title
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Condensed prediction: probabilities + method line */}
          {pred?.win_prob_a != null && pred.win_prob_b != null && (() => {
            const methods = [
              { label: 'KO/TKO', value: pred.method_ko_tko },
              { label: 'Sub',    value: pred.method_sub },
              { label: 'Dec',    value: pred.method_dec },
            ]
            const topLabel = methods.reduce((a, b) => ((a.value ?? 0) > (b.value ?? 0) ? a : b)).label
            return (
              <Card>
                <div className="flex items-center justify-between gap-4">
                  <span
                    className={`font-mono text-3xl font-bold tabular-nums ${
                      aWins
                        ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                        : 'text-[var(--color-text-muted)]'
                    }`}
                  >
                    {pct(pred.win_prob_a)}
                  </span>
                  <span className="text-xs text-[var(--color-text-muted)]">win prob</span>
                  <span
                    className={`font-mono text-3xl font-bold tabular-nums ${
                      !aWins
                        ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                        : 'text-[var(--color-text-muted)]'
                    }`}
                  >
                    {pct(pred.win_prob_b)}
                  </span>
                </div>
                <div className="mt-2 flex justify-center gap-4 font-mono text-sm tabular-nums">
                  {methods.map(({ label, value }) => (
                    <span
                      key={label}
                      className={
                        label === topLabel
                          ? 'font-bold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                          : 'text-[var(--color-text-muted)] opacity-50'
                      }
                    >
                      {label} {pct(value)}
                    </span>
                  ))}
                </div>
              </Card>
            )
          })()}

          {/* Tale of the Tape — only if we have at least one fighter profile */}
          {(fighterA || fighterB) && (
            <Card header={<span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Tale of the Tape</span>}>
              <TaleOfTape
                a={fighterA}
                b={fighterB}
                nameA={nameA}
                nameB={nameB}
              />
            </Card>
          )}

          {/* Striking */}
          {(fighterA || fighterB) && (
            <Card header={<span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Striking</span>}>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                    <th className="pb-2 text-left font-medium">{nameA}</th>
                    <th className="pb-2 text-center font-medium"></th>
                    <th className="pb-2 text-right font-medium">{nameB}</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { label: 'SLpM',      valA: fighterA?.slpm?.toFixed(2)  ?? '—', valB: fighterB?.slpm?.toFixed(2)  ?? '—' },
                    { label: 'Str. Acc.', valA: fighterA?.str_acc            ?? '—', valB: fighterB?.str_acc            ?? '—' },
                    { label: 'SApM',      valA: fighterA?.sapm?.toFixed(2)  ?? '—', valB: fighterB?.sapm?.toFixed(2)  ?? '—' },
                    { label: 'Str. Def.', valA: fighterA?.str_def            ?? '—', valB: fighterB?.str_def            ?? '—' },
                  ].map(({ label, valA, valB }) => (
                    <tr key={label} className="border-t border-[var(--color-border)]">
                      <td className="py-2 font-mono tabular-nums">{valA}</td>
                      <td className="py-2 text-center text-xs text-[var(--color-text-muted)]">{label}</td>
                      <td className="py-2 text-right font-mono tabular-nums">{valB}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}

          {/* Grappling */}
          {(fighterA || fighterB) && (
            <Card header={<span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Grappling</span>}>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                    <th className="pb-2 text-left font-medium">{nameA}</th>
                    <th className="pb-2 text-center font-medium"></th>
                    <th className="pb-2 text-right font-medium">{nameB}</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { label: 'TD Avg.',   valA: fighterA?.td_avg?.toFixed(2)  ?? '—', valB: fighterB?.td_avg?.toFixed(2)  ?? '—' },
                    { label: 'TD Acc.',   valA: fighterA?.td_acc               ?? '—', valB: fighterB?.td_acc               ?? '—' },
                    { label: 'TD Def.',   valA: fighterA?.td_def               ?? '—', valB: fighterB?.td_def               ?? '—' },
                    { label: 'Sub. Avg.', valA: fighterA?.sub_avg?.toFixed(2) ?? '—', valB: fighterB?.sub_avg?.toFixed(2) ?? '—' },
                  ].map(({ label, valA, valB }) => (
                    <tr key={label} className="border-t border-[var(--color-border)]">
                      <td className="py-2 font-mono tabular-nums">{valA}</td>
                      <td className="py-2 text-center text-xs text-[var(--color-text-muted)]">{label}</td>
                      <td className="py-2 text-right font-mono tabular-nums">{valB}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}

          {/* Recent fights */}
          {(fight.fighter_a_id || fight.fighter_b_id) && (
            <Card header={<span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Recent Fights</span>}>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <p className="mb-3 text-xs font-semibold text-[var(--color-text-muted)]">{nameA}</p>
                  {!fight.fighter_a_id ? (
                    <p className="text-xs text-[var(--color-text-muted)]">No history</p>
                  ) : !fightsA ? (
                    <LoadingSkeleton lines={3} />
                  ) : fightsA.data.length === 0 ? (
                    <p className="text-xs text-[var(--color-text-muted)]">No history</p>
                  ) : (
                    <RecentFightMini fights={fightsA.data} viewingFighterId={fight.fighter_a_id} />
                  )}
                </div>
                <div>
                  <p className="mb-3 text-xs font-semibold text-[var(--color-text-muted)]">{nameB}</p>
                  {!fight.fighter_b_id ? (
                    <p className="text-xs text-[var(--color-text-muted)]">No history</p>
                  ) : !fightsB ? (
                    <LoadingSkeleton lines={3} />
                  ) : fightsB.data.length === 0 ? (
                    <p className="text-xs text-[var(--color-text-muted)]">No history</p>
                  ) : (
                    <RecentFightMini fights={fightsB.data} viewingFighterId={fight.fighter_b_id} />
                  )}
                </div>
              </div>
            </Card>
          )}

          {/* Feature breakdown */}
          {pred?.features_json && (
            <Card header={<span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Model Breakdown</span>}>
              <FeatureBreakdown fight={fight} />
              <p className="mt-4 text-center text-[10px] text-[var(--color-text-muted)]">
                Values are per-fight averages (Fighter A − Fighter B), sorted by magnitude. Model: {pred.model_version ?? 'win_loss_v1'}.
              </p>
            </Card>
          )}

          {!pred && (
            <p className="py-8 text-center text-sm text-[var(--color-text-muted)]">
              No prediction available for this fight.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
