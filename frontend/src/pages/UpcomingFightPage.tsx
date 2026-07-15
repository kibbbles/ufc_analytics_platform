import { Link, useParams } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { upcomingService } from '@services/upcomingService'
import { fightersService } from '@services/fightersService'
import { fightsService } from '@services/fightsService'
import { Badge, Card, LoadingSkeleton } from '@components/common'
import OddsCalculator from '@components/features/OddsCalculator'
import TaleOfTape from '@components/features/TaleOfTape'
import RecentFightMini from '@components/features/RecentFightMini'
import { splitFavoredFeatures } from '@components/features/fightPrediction/featureMeta'
import type { UpcomingFight } from '@t/api'
import { formatPct as pct } from '@utils/format'

// -- Sub-components ------------------------------------------------------------

function FeatureBreakdown({ fight }: { fight: UpcomingFight }) {
  const features = fight.prediction?.features_json ?? null
  const nameA = fight.fighter_a_name?.split(' ').pop() ?? 'A'
  const nameB = fight.fighter_b_name?.split(' ').pop() ?? 'B'
  const aWins = (fight.prediction?.win_prob_a ?? 0) >= (fight.prediction?.win_prob_b ?? 0)

  if (!features) return null

  const { favA, favB } = splitFavoredFeatures(features)

  return (
    <>
      <p className="mb-4 text-center text-sm text-[var(--color-text-muted)]">
        <span className="font-semibold">{aWins ? favA.length : favB.length} of {favA.length + favB.length}</span>
        {' metrics favor '}
        <span className="font-semibold">{aWins ? nameA : nameB}</span>
      </p>
    <div className="grid grid-cols-2 gap-4">
      <div>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
          Favors {nameA}
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
          Favors {nameB}
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
    </>
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
        <div className="rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error)]/10 p-6 text-center text-sm text-[var(--color-error-light)] dark:text-[var(--color-error)]">
          {error}
        </div>
      )}

      {fight && (
        <OddsCalculator
          nameA={nameA}
          nameB={nameB}
          modelProbA={pred?.win_prob_a ?? null}
          modelProbB={pred?.win_prob_b ?? null}
          initialOddsA={fight.odds_a}
          initialOddsB={fight.odds_b}
        />
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
              <div className="mt-2 flex items-center justify-center gap-2">
                {fight.is_title_fight && !fight.is_interim_title && <Badge variant="warning">Title</Badge>}
                {fight.is_interim_title && <Badge variant="warning">Interim</Badge>}
                {fight.weight_class && (
                  <span className="text-xs text-[var(--color-text-muted)]">{fight.weight_class}</span>
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
                {(() => {
                  const confidence = (Math.max(pred.win_prob_a ?? 0, pred.win_prob_b ?? 0) - 0.5) * 2
                  return (
                    <div className="mt-2 text-center text-xs text-[var(--color-text-muted)]">
                      conviction{' '}
                      <span className="font-mono tabular-nums font-semibold">
                        {pct(confidence)}
                      </span>
                    </div>
                  )
                })()}
                {fight.implied_prob_a != null && fight.implied_prob_b != null && (
                  <div className="mt-1.5 text-center font-mono text-xs tabular-nums text-[var(--color-text-muted)]">
                    vegas {pct(fight.implied_prob_a)} / {pct(fight.implied_prob_b)}
                    {fight.odds_a != null && fight.odds_b != null && (
                      <span className="ml-1 opacity-60">
                        ({fight.odds_a > 0 ? '+' : ''}{fight.odds_a} / {fight.odds_b > 0 ? '+' : ''}{fight.odds_b})
                      </span>
                    )}
                  </div>
                )}
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
                Values are per-fight averages (Fighter A − Fighter B), sorted by magnitude. Model: {pred.model_version ?? 'win_loss_v1'}.{' '}
                The metric count shows how many of the model's input features point in the predicted winner's favor — a higher share means the prediction is backed by broader evidence, not just one or two stats.
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
