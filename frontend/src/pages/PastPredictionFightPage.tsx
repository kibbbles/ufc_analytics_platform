import { useParams, Link, useNavigate } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { pastPredictionsService } from '@services/pastPredictionsService'
import { fightersService } from '@services/fightersService'
import { fightsService } from '@services/fightsService'
import { Card, LoadingSkeleton, Badge } from '@components/common'
import TaleOfTape from '@components/features/TaleOfTape'
import RecentFightMini from '@components/features/RecentFightMini'
import { splitFavoredFeatures } from '@components/features/fightPrediction/featureMeta'
import { formatPct as pct, formatDate } from '@utils/format'
import type { PastPredictionItem } from '@t/api'

export default function PastPredictionFightPage() {
  const { fight_id } = useParams<{ fight_id: string }>()
  const navigate     = useNavigate()

  // Base fight data — always loaded, drives the entire page
  const { data: fightDetail, loading, error } = useApi(
    () => fightsService.getById(fight_id!),
    [fight_id],
  )

  // Prediction — optional; 404 silently becomes null
  const { data: predItem } = useApi(
    () => pastPredictionsService.getFight(fight_id!).catch((): PastPredictionItem | null => null),
    [fight_id],
  )

  const faId = fightDetail?.fighter_a_id ?? null
  const fbId = fightDetail?.fighter_b_id ?? null

  const { data: fighterA } = useApi(
    () => faId ? fightersService.getById(faId) : Promise.resolve(null),
    [faId],
  )
  const { data: fighterB } = useApi(
    () => fbId ? fightersService.getById(fbId) : Promise.resolve(null),
    [fbId],
  )
  const { data: fightsA } = useApi(
    () => faId ? fightsService.getList({ fighter_id: faId, page_size: 5 }) : Promise.resolve(null),
    [faId],
  )
  const { data: fightsB } = useApi(
    () => fbId ? fightsService.getList({ fighter_id: fbId, page_size: 5 }) : Promise.resolve(null),
    [fbId],
  )

  // Resolve names: prediction has clean full names; fall back to parsing bout string
  const boutParts = (fightDetail?.bout ?? '').split(' vs. ')
  const nameA = predItem?.fighter_a_name ?? boutParts[0]?.trim() ?? '—'
  const nameB = predItem?.fighter_b_name ?? boutParts[1]?.trim() ?? '—'

  // Win probability (prediction only)
  const hasPred   = predItem?.win_prob_a != null && predItem?.win_prob_b != null
  const probA     = predItem?.win_prob_a ?? 0
  const probB     = predItem?.win_prob_b ?? 0
  const predAWins = probA >= probB

  // Actual result from base fight data
  const winnerId        = fightDetail?.winner_id
  const actualWinnerName = winnerId === faId ? nameA : winnerId === fbId ? nameB : '—'

  const methods = [
    { label: 'KO/TKO', value: predItem?.pred_method_ko_tko },
    { label: 'Sub',    value: predItem?.pred_method_sub },
    { label: 'Dec',    value: predItem?.pred_method_dec },
  ]
  const topLabel = methods.reduce((a, b) => ((a.value ?? 0) > (b.value ?? 0) ? a : b)).label

  // Actual result card styling
  const isCorrect = predItem?.is_correct ?? null
  const isUpset   = predItem?.is_upset   ?? null
  let resultBadge: string, resultBg: string, resultBadgeCls: string
  if (isCorrect === null)  { resultBadge = 'Result';      resultBg = 'bg-[var(--color-border)]/20 border-[var(--color-border)]'; resultBadgeCls = 'text-[var(--color-text-muted)]' }
  else if (isUpset)        { resultBadge = '~ Upset';     resultBg = 'bg-[var(--color-warning)]/10 border-[var(--color-warning)]/30';                     resultBadgeCls = 'text-[var(--color-warning-light)] dark:text-[var(--color-warning)]' }
  else if (isCorrect)      { resultBadge = '✓ Correct';   resultBg = 'bg-[var(--color-success)]/10 border-[var(--color-success)]/30';                     resultBadgeCls = 'text-[var(--color-success-light)] dark:text-[var(--color-success)]' }
  else                     { resultBadge = '✗ Incorrect'; resultBg = 'bg-[var(--color-error)]/10 border-[var(--color-error)]/30';                         resultBadgeCls = 'text-[var(--color-error-light)] dark:text-[var(--color-error)]' }

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
        <p className="text-sm text-[var(--color-error-light)] dark:text-[var(--color-error)]">{error}</p>
      )}

      {fightDetail && !loading && (
        <div className="space-y-4">
          {/* Header: fighter names */}
          <div className="text-center">
            <div className="flex items-center justify-center gap-3 flex-wrap">
              {faId ? (
                <Link
                  to={`/fighters/${faId}`}
                  className={`text-xl font-bold hover:text-[var(--color-primary)] transition-colors ${
                    hasPred
                      ? predAWins
                        ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                        : 'text-[var(--color-text-muted)]'
                      : winnerId === faId
                        ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                        : winnerId ? 'text-[var(--color-text-muted)]' : ''
                  }`}
                >
                  {nameA}
                </Link>
              ) : (
                <span className="text-xl font-bold">{nameA}</span>
              )}
              <span className="text-sm text-[var(--color-text-muted)]">vs</span>
              {fbId ? (
                <Link
                  to={`/fighters/${fbId}`}
                  className={`text-xl font-bold hover:text-[var(--color-primary)] transition-colors ${
                    hasPred
                      ? !predAWins
                        ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                        : 'text-[var(--color-text-muted)]'
                      : winnerId === fbId
                        ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                        : winnerId ? 'text-[var(--color-text-muted)]' : ''
                  }`}
                >
                  {nameB}
                </Link>
              ) : (
                <span className="text-xl font-bold">{nameB}</span>
              )}
            </div>
            <div className="mt-2 flex justify-center gap-2 flex-wrap items-center">
              {predItem?.is_title_fight && !predItem?.is_interim_title && <Badge variant="warning">Title</Badge>}
              {predItem?.is_interim_title && <Badge variant="warning">Interim</Badge>}
              {fightDetail.weight_class && (
                <span className="text-xs text-[var(--color-text-muted)]">{fightDetail.weight_class}</span>
              )}
              {predItem?.event_name && (
                <span className="text-xs text-[var(--color-text-muted)]">
                  · {predItem.event_name}
                  {predItem.event_date ? ` · ${formatDate(predItem.event_date)}` : ''}
                </span>
              )}
            </div>
          </div>

          {/* Prediction card */}
          {hasPred && (
            <Card>
              <div className="flex items-center justify-between gap-4">
                <span className={`font-mono text-3xl font-bold tabular-nums ${predAWins ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                  {pct(predItem!.win_prob_a)}
                </span>
                <span className="text-xs text-[var(--color-text-muted)]">win prob</span>
                <span className={`font-mono text-3xl font-bold tabular-nums ${!predAWins ? 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
                  {pct(predItem!.win_prob_b)}
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
              {predItem!.confidence != null && (
                <div className="mt-2 text-center text-xs text-[var(--color-text-muted)]">
                  conviction{' '}
                  <span className="font-mono tabular-nums font-semibold">
                    {pct(predItem!.confidence)}
                  </span>
                </div>
              )}
            </Card>
          )}

          {/* Prediction provenance badge */}
          {predItem?.prediction_source && (
            <div className="flex justify-center">
              {predItem.prediction_source === 'pre_fight_archive' ? (
                <span
                  title="Prediction was frozen before this fight occurred — no post-fight data was used"
                  className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium bg-[var(--color-success)]/10 text-[var(--color-success-light)] dark:text-[var(--color-success)] border border-[var(--color-success)]/20"
                >
                  pre-fight prediction
                </span>
              ) : (
                <span
                  title="Prediction was computed retrospectively from historical data — may reflect post-fight stats"
                  className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium bg-[var(--color-warning)]/10 text-[var(--color-warning-light)] dark:text-[var(--color-warning)] border border-[var(--color-warning)]/20"
                >
                  legacy backfill
                </span>
              )}
            </div>
          )}

          {/* Actual result */}
          {winnerId && (
            <div className={`rounded-lg border p-4 ${resultBg}`}>
              <p className={`text-xs font-semibold uppercase tracking-wide mb-2 ${resultBadgeCls}`}>{resultBadge}</p>
              <div className="flex items-center justify-between text-sm">
                <span className="font-semibold">{actualWinnerName}</span>
                <span className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                  {fightDetail.method ?? '—'}
                  {fightDetail.round != null ? ` · R${fightDetail.round}` : ''}
                </span>
              </div>
            </div>
          )}

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
          {(faId || fbId) && (
            <Card header={<span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Recent Fights</span>}>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <p className="mb-3 text-xs font-semibold text-[var(--color-text-muted)]">{nameA}</p>
                  {!faId ? (
                    <p className="text-xs text-[var(--color-text-muted)]">No history</p>
                  ) : !fightsA ? (
                    <LoadingSkeleton lines={3} />
                  ) : fightsA.data.length === 0 ? (
                    <p className="text-xs text-[var(--color-text-muted)]">No history</p>
                  ) : (
                    <RecentFightMini fights={fightsA.data} viewingFighterId={faId} />
                  )}
                </div>
                <div>
                  <p className="mb-3 text-xs font-semibold text-[var(--color-text-muted)]">{nameB}</p>
                  {!fbId ? (
                    <p className="text-xs text-[var(--color-text-muted)]">No history</p>
                  ) : !fightsB ? (
                    <LoadingSkeleton lines={3} />
                  ) : fightsB.data.length === 0 ? (
                    <p className="text-xs text-[var(--color-text-muted)]">No history</p>
                  ) : (
                    <RecentFightMini fights={fightsB.data} viewingFighterId={fbId} />
                  )}
                </div>
              </div>
            </Card>
          )}

          {/* Model Breakdown — only when prediction + features available */}
          {predItem?.features_json && (() => {
            const { favA, favB } = splitFavoredFeatures(predItem.features_json)
            const total = favA.length + favB.length
            if (total === 0) return null
            const winnerLastName = (predAWins ? nameA : nameB).split(' ').pop()
            const winnerCount = predAWins ? favA.length : favB.length
            return (
              <Card header={<span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Model Breakdown</span>}>
                <p className="mb-4 text-center text-sm text-[var(--color-text-muted)]">
                  <span className="font-semibold">{winnerCount} of {total}</span>
                  {' metrics favored '}
                  <span className="font-semibold">{winnerLastName}</span>
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
                      Favored {nameA.split(' ').pop()}
                    </h3>
                    {favA.length === 0 ? (
                      <p className="text-xs text-[var(--color-text-muted)]">No clear advantages</p>
                    ) : favA.slice(0, 8).map(({ label, display }) => (
                      <div key={label} className="mb-2">
                        <div className="text-xs font-semibold text-[var(--color-primary)]">+{display}</div>
                        <div className="text-[11px] leading-snug text-[var(--color-text-muted)]">{label}</div>
                      </div>
                    ))}
                  </div>
                  <div>
                    <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
                      Favored {nameB.split(' ').pop()}
                    </h3>
                    {favB.length === 0 ? (
                      <p className="text-xs text-[var(--color-text-muted)]">No clear advantages</p>
                    ) : favB.slice(0, 8).map(({ label, display }) => (
                      <div key={label} className="mb-2">
                        <div className="text-xs font-semibold text-[var(--color-primary)]">+{display}</div>
                        <div className="text-[11px] leading-snug text-[var(--color-text-muted)]">{label}</div>
                      </div>
                    ))}
                  </div>
                </div>
                <p className="mt-4 text-center text-[10px] text-[var(--color-text-muted)]">
                  Values are per-fight averages (Fighter A − Fighter B), sorted by magnitude. Model: {predItem.model_version ?? 'win_loss_v1'}.{' '}
                  The metric count shows how many of the model's input features point in the predicted winner's favor — a higher share means the prediction is backed by broader evidence, not just one or two stats.
                </p>
              </Card>
            )
          })()}
        </div>
      )}
    </div>
  )
}
