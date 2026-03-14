import { useParams, Link, useNavigate } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { pastPredictionsService } from '@services/pastPredictionsService'
import { fightersService } from '@services/fightersService'
import { fightsService } from '@services/fightsService'
import { Card, LoadingSkeleton } from '@components/common'
import { inchesToFeet, formatDate } from '@utils/format'
import type { FighterResponse, FightListItem, PastPredictionItem } from '@t/api'

// ── Helpers ───────────────────────────────────────────────────────────────────

function pct(v: number | null | undefined): string {
  if (v == null) return '—'
  return `${(v * 100).toFixed(1)}%`
}

function heightDisplay(inches: number | null | undefined): string {
  return inches != null ? inchesToFeet(inches) : '—'
}

function fmtTime(seconds: number | null | undefined): string {
  if (seconds == null) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function winnerName(item: PastPredictionItem, id: string | null | undefined): string {
  if (!id) return '—'
  if (id === item.fighter_a_id) return item.fighter_a_name ?? '—'
  if (id === item.fighter_b_id) return item.fighter_b_name ?? '—'
  return '—'
}

// ── TaleOfTape ────────────────────────────────────────────────────────────────

function TaleOfTape({
  a, b, nameA, nameB,
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

  const rows = [
    { label: hasCareer ? 'Record' : 'Record (UFC)', valA: record(a), valB: record(b) },
    { label: 'Avg. Fight', valA: fmtTime(a?.avg_fight_time_seconds), valB: fmtTime(b?.avg_fight_time_seconds) },
    { label: 'Height',     valA: heightDisplay(a?.height_inches),    valB: heightDisplay(b?.height_inches) },
    { label: 'Weight',     valA: a?.weight_lbs != null ? `${a.weight_lbs} lbs` : '—', valB: b?.weight_lbs != null ? `${b.weight_lbs} lbs` : '—' },
    { label: 'Reach',      valA: a?.reach_inches != null ? `${a.reach_inches}"` : '—', valB: b?.reach_inches != null ? `${b.reach_inches}"` : '—' },
    { label: 'Stance',     valA: a?.stance ?? '—', valB: b?.stance ?? '—' },
    { label: 'DOB',        valA: a?.dob_date ? formatDate(String(a.dob_date)) : '—', valB: b?.dob_date ? formatDate(String(b.dob_date)) : '—' },
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

// ── RecentFightMini ───────────────────────────────────────────────────────────

function RecentFightMini({
  fights, viewingFighterId,
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
        const isWin  = f.winner_id === viewingFighterId
        const isLoss = f.winner_id !== null && f.winner_id !== viewingFighterId
        return (
          <div key={f.id} className="flex items-center gap-2 text-sm">
            <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-bold tabular-nums ${
              isWin  ? 'bg-green-500/15 text-green-600 dark:text-green-400'
              : isLoss ? 'bg-red-500/15 text-red-600 dark:text-red-400'
              : 'bg-[var(--color-border)] text-[var(--color-text-muted)]'
            }`}>
              {isWin ? 'W' : isLoss ? 'L' : '—'}
            </span>
            {opponentId ? (
              <Link to={`/fighters/${opponentId}`} className="font-medium hover:text-[var(--color-primary)] transition-colors">
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

// ── Actual result card ────────────────────────────────────────────────────────

function ActualResultCard({ item }: { item: PastPredictionItem }) {
  const isUpset   = item.is_upset
  const isCorrect = item.is_correct

  let badge: string
  let bgClass: string
  let badgeClass: string
  if (isUpset)        { badge = '~ Upset';     bgClass = 'bg-amber-500/10 border-amber-500/30'; badgeClass = 'text-amber-600 dark:text-amber-400' }
  else if (isCorrect) { badge = '✓ Correct';   bgClass = 'bg-green-500/10 border-green-500/30'; badgeClass = 'text-green-600 dark:text-green-400' }
  else                { badge = '✗ Incorrect'; bgClass = 'bg-red-500/10 border-red-500/30';     badgeClass = 'text-red-600 dark:text-red-400' }

  return (
    <div className={`rounded-lg border p-4 ${bgClass}`}>
      <p className={`text-xs font-semibold uppercase tracking-wide mb-2 ${badgeClass}`}>{badge}</p>
      <div className="flex items-center justify-between text-sm">
        <span className="font-semibold">{winnerName(item, item.actual_winner_id)}</span>
        <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          {item.actual_method ?? '—'}
        </span>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PastPredictionFightPage() {
  const { fight_id } = useParams<{ fight_id: string }>()
  const navigate     = useNavigate()

  const { data: item, loading, error } = useApi(
    () => pastPredictionsService.getFight(fight_id!),
    [fight_id],
  )

  const { data: fighterA } = useApi(
    () => item?.fighter_a_id ? fightersService.getById(item.fighter_a_id) : Promise.resolve(null),
    [item?.fighter_a_id],
  )
  const { data: fighterB } = useApi(
    () => item?.fighter_b_id ? fightersService.getById(item.fighter_b_id) : Promise.resolve(null),
    [item?.fighter_b_id],
  )
  const { data: fightsA } = useApi(
    () => item?.fighter_a_id ? fightsService.getList({ fighter_id: item.fighter_a_id, page_size: 5 }) : Promise.resolve(null),
    [item?.fighter_a_id],
  )
  const { data: fightsB } = useApi(
    () => item?.fighter_b_id ? fightsService.getList({ fighter_id: item.fighter_b_id, page_size: 5 }) : Promise.resolve(null),
    [item?.fighter_b_id],
  )

  const nameA  = item?.fighter_a_name ?? '—'
  const nameB  = item?.fighter_b_name ?? '—'
  const probA  = item?.win_prob_a ?? 0
  const probB  = item?.win_prob_b ?? 0
  const aWins  = probA >= probB

  const methods = [
    { label: 'KO/TKO', value: item?.pred_method_ko_tko },
    { label: 'Sub',    value: item?.pred_method_sub },
    { label: 'Dec',    value: item?.pred_method_dec },
  ]
  const topLabel = methods.reduce((a, b) => ((a.value ?? 0) > (b.value ?? 0) ? a : b)).label

  return (
    <div className="mx-auto max-w-[640px]">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors mb-6"
      >
        ← Back
      </button>

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

      {item && !loading && (
        <div className="space-y-4">
          {/* Header: fighter names */}
          <div className="text-center">
            <div className="flex items-center justify-center gap-3 flex-wrap">
              {item.fighter_a_id ? (
                <Link
                  to={`/fighters/${item.fighter_a_id}`}
                  className={`text-xl font-bold hover:text-[var(--color-primary)] transition-colors ${
                    aWins ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'
                  }`}
                >
                  {nameA}
                </Link>
              ) : (
                <span className={`text-xl font-bold ${aWins ? '' : 'text-[var(--color-text-muted)]'}`}>{nameA}</span>
              )}
              <span className="text-sm text-[var(--color-text-muted)]">vs</span>
              {item.fighter_b_id ? (
                <Link
                  to={`/fighters/${item.fighter_b_id}`}
                  className={`text-xl font-bold hover:text-[var(--color-primary)] transition-colors ${
                    !aWins ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'
                  }`}
                >
                  {nameB}
                </Link>
              ) : (
                <span className={`text-xl font-bold ${!aWins ? '' : 'text-[var(--color-text-muted)]'}`}>{nameB}</span>
              )}
            </div>
            <div className="mt-2 flex justify-center gap-2 flex-wrap">
              {item.weight_class && (
                <span className="text-xs text-[var(--color-text-muted)]">{item.weight_class}</span>
              )}
              {item.event_name && (
                <span className="text-xs text-[var(--color-text-muted)]">
                  · {item.event_name}
                  {item.event_date ? ` · ${formatDate(item.event_date)}` : ''}
                </span>
              )}
            </div>
          </div>

          {/* Prediction card — same layout as UpcomingFightPage */}
          {item.win_prob_a != null && item.win_prob_b != null && (
            <Card>
              <div className="flex items-center justify-between gap-4">
                <span className={`font-mono text-3xl font-bold tabular-nums ${aWins ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                  {pct(item.win_prob_a)}
                </span>
                <span className="text-xs text-[var(--color-text-muted)]">win prob</span>
                <span className={`font-mono text-3xl font-bold tabular-nums ${!aWins ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                  {pct(item.win_prob_b)}
                </span>
              </div>
              <div className="mt-2 flex justify-center gap-4 font-mono text-sm tabular-nums">
                {methods.map(({ label, value }) => (
                  <span
                    key={label}
                    className={label === topLabel
                      ? 'font-bold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                      : 'text-[var(--color-text-muted)] opacity-50'
                    }
                  >
                    {label} {pct(value)}
                  </span>
                ))}
              </div>
              {item.confidence != null && (
                <div className="mt-2 text-center text-xs text-[var(--color-text-muted)]">
                  confidence{' '}
                  <span className={`font-mono tabular-nums font-semibold ${item.confidence >= 0.65 ? 'text-green-600 dark:text-green-400' : ''}`}>
                    {pct(item.confidence)}
                  </span>
                </div>
              )}
            </Card>
          )}

          {/* Prediction provenance badge */}
          {item.prediction_source && (
            <div className="flex justify-center">
              {item.prediction_source === 'pre_fight_archive' ? (
                <span
                  title="Prediction was frozen before this fight occurred — no post-fight data was used"
                  className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium bg-green-500/10 text-green-700 dark:text-green-400 border border-green-500/20"
                >
                  pre-fight prediction
                </span>
              ) : (
                <span
                  title="Prediction was computed retrospectively from historical data — may reflect post-fight stats"
                  className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20"
                >
                  legacy backfill
                </span>
              )}
            </div>
          )}

          {/* Actual result */}
          <ActualResultCard item={item} />

          {/* Tale of the Tape */}
          {(fighterA || fighterB) && (
            <Card header={<span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Tale of the Tape</span>}>
              <TaleOfTape a={fighterA} b={fighterB} nameA={nameA} nameB={nameB} />
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
                    { label: 'SLpM',      valA: fighterA?.slpm?.toFixed(2) ?? '—', valB: fighterB?.slpm?.toFixed(2) ?? '—' },
                    { label: 'Str. Acc.', valA: fighterA?.str_acc ?? '—',           valB: fighterB?.str_acc ?? '—' },
                    { label: 'SApM',      valA: fighterA?.sapm?.toFixed(2) ?? '—', valB: fighterB?.sapm?.toFixed(2) ?? '—' },
                    { label: 'Str. Def.', valA: fighterA?.str_def ?? '—',           valB: fighterB?.str_def ?? '—' },
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
                    { label: 'TD Avg.',   valA: fighterA?.td_avg?.toFixed(2) ?? '—',  valB: fighterB?.td_avg?.toFixed(2) ?? '—' },
                    { label: 'TD Acc.',   valA: fighterA?.td_acc ?? '—',               valB: fighterB?.td_acc ?? '—' },
                    { label: 'TD Def.',   valA: fighterA?.td_def ?? '—',               valB: fighterB?.td_def ?? '—' },
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
          {(item.fighter_a_id || item.fighter_b_id) && (
            <Card header={<span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Recent Fights</span>}>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <p className="mb-3 text-xs font-semibold text-[var(--color-text-muted)]">{nameA}</p>
                  {!item.fighter_a_id ? (
                    <p className="text-xs text-[var(--color-text-muted)]">No history</p>
                  ) : !fightsA ? (
                    <LoadingSkeleton lines={3} />
                  ) : fightsA.data.length === 0 ? (
                    <p className="text-xs text-[var(--color-text-muted)]">No history</p>
                  ) : (
                    <RecentFightMini fights={fightsA.data} viewingFighterId={item.fighter_a_id} />
                  )}
                </div>
                <div>
                  <p className="mb-3 text-xs font-semibold text-[var(--color-text-muted)]">{nameB}</p>
                  {!item.fighter_b_id ? (
                    <p className="text-xs text-[var(--color-text-muted)]">No history</p>
                  ) : !fightsB ? (
                    <LoadingSkeleton lines={3} />
                  ) : fightsB.data.length === 0 ? (
                    <p className="text-xs text-[var(--color-text-muted)]">No history</p>
                  ) : (
                    <RecentFightMini fights={fightsB.data} viewingFighterId={item.fighter_b_id} />
                  )}
                </div>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
