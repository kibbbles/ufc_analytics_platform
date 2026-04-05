import { useState } from 'react'
import { analyticsService } from '@services/analyticsService'
import { useApi } from '@hooks/useApi'
import WeightClassFilter from '@components/features/WeightClassFilter'
import FinishRateChart from '@components/features/FinishRateChart'
import FighterOutputChart from '@components/features/FighterOutputChart'
import RoundDistributionChart from '@components/features/RoundDistributionChart'
import WeightClassHeatmap from '@components/features/WeightClassHeatmap'
import PhysicalStatsChart from '@components/features/PhysicalStatsChart'
import AgeByWeightClassChart from '@components/features/AgeByWeightClassChart'
import FighterStatsByWeightClassTable from '@components/features/FighterStatsByWeightClassTable'
import LoadingSpinner from '@components/common/LoadingSpinner'

export default function StyleEvolutionPage() {
  const [weightClass, setWeightClass] = useState<string | null>(null)
  const [showBreakdown, setShowBreakdown] = useState(false)

  const { data, loading, error } = useApi(
    () => analyticsService.getStyleEvolution(weightClass ?? undefined),
    [weightClass],
  )

  const finishData       = data?.data              ?? []
  const outputData       = data?.fighter_outputs   ?? []
  const roundData        = data?.round_distribution ?? []
  const heatmapData      = data?.heatmap_data      ?? []
  const physicalData     = data?.physical_stats    ?? []
  const ageData          = data?.age_data          ?? []
  const fighterStatsData = data?.fighter_stats     ?? []

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-12">

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">How the UFC Has Changed</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
          Finish rates, fighter outputs, and athletic profiles over time
        </p>
      </div>

      {/* Weight class filter — sticky below header so it stays visible while scrolling */}
      <div className="sticky top-14 z-40 -mx-4 px-4 py-2 bg-[var(--color-surface-light)]/95 dark:bg-[var(--color-surface)]/95 backdrop-blur-sm border-b border-[var(--color-border-light)] dark:border-[var(--color-border)]">
        <div className="flex items-center gap-3">
          <WeightClassFilter value={weightClass} onChange={setWeightClass} />
          {/* Subtle refresh indicator — only shown on subsequent fetches (data already visible) */}
          {loading && data && (
            <div className="size-4 shrink-0 rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-primary)] animate-spin opacity-60" />
          )}
        </div>
      </div>

      {/* Initial load — no data yet */}
      {loading && !data && (
        <div className="flex justify-center py-16">
          <LoadingSpinner />
        </div>
      )}

      {error && !data && (
        <p className="text-sm text-red-500">Failed to load data. Try refreshing.</p>
      )}

      {data && (
        <>
          {/* ── Section 1: How fights end ─────────────────────────────────── */}
          <section className="space-y-4">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <h2 className="text-lg font-semibold">How fights end</h2>
                <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] max-w-2xl">
                  The UFC has become a decision-heavy sport. In the early 2000s, nearly 7 in 10
                  fights ended before the final bell. By 2024, that number had flipped — over half
                  of all fights go to the judges.
                </p>
              </div>

              {/* Combined / Breakdown toggle */}
              <div className="flex rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] overflow-hidden shrink-0">
                {(['Combined', 'Breakdown'] as const).map((mode) => {
                  const active = mode === 'Breakdown' ? showBreakdown : !showBreakdown
                  return (
                    <button
                      key={mode}
                      onClick={() => setShowBreakdown(mode === 'Breakdown')}
                      className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                        active
                          ? 'bg-[var(--color-primary)] text-white'
                          : 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-high-light)] dark:hover:bg-[var(--color-surface-high)]'
                      }`}
                    >
                      {mode}
                    </button>
                  )
                })}
              </div>
            </div>

            {finishData.length > 0 ? (
              <FinishRateChart
                data={finishData}
                config={showBreakdown
                  ? { showFinishRate: false, showKoTko: true, showSubmission: true, showDecision: true }
                  : {}
                }
              />
            ) : (
              <p className="text-sm text-[var(--color-text-muted)]">No data for this weight class.</p>
            )}

            {/* Era annotation key */}
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
              <span><span className="font-semibold text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">Unified Rules (2001)</span> — Standardised scoring, prohibited strikes, and referee stoppages across all states.</span>
              <span><span className="font-semibold text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">USADA begins (2015)</span> — UFC's anti-doping programme launched; widely associated with a drop in KO stoppages.</span>
              <span><span className="font-semibold text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">Judging update (2017)</span> — Nevada adopted 10-point must with greater emphasis on effective aggression; more fights going to decision.</span>
              <span><span className="font-semibold text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">COVID era (2020–21)</span> — Shaded region. Fight Island / empty arenas; condensed schedule with limited fighter preparation time.</span>
            </div>
          </section>

          {/* ── Section 2: When finishes happen ──────────────────────────── */}
          <section className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">When finishes happen</h2>
              <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] max-w-2xl">
                Of finishes that do occur, Round 1 has historically produced the most stoppages.
                Dashed bars indicate the current partial year.
              </p>
            </div>

            {roundData.length > 0 ? (
              <RoundDistributionChart data={roundData} />
            ) : (
              <p className="text-sm text-[var(--color-text-muted)]">No data for this weight class.</p>
            )}
          </section>

          {/* ── Section 3: How fighters fight ────────────────────────────── */}
          <section className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">How fighters fight</h2>
              <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] max-w-2xl">
                Average outputs per fighter per fight since 2015 — striking volume, takedown
                aggression, and control time. Faded bars indicate the current partial year.
              </p>
            </div>

            {outputData.length > 0 ? (
              <FighterOutputChart data={outputData} />
            ) : (
              <p className="text-sm text-[var(--color-text-muted)]">
                No detailed stats available for this weight class.
              </p>
            )}
          </section>

          {/* ── Section 4: Finish rate by weight class (heatmap) ──────────── */}
          <section className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">Finish rate by weight class</h2>
              <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] max-w-2xl">
                Heavier weight classes consistently finish more fights. Lighter women's
                divisions — added later — tend to go to the judges more often. Hover a cell
                for the exact rate and fight count. Weight class filter does not apply here.
              </p>
            </div>

            {heatmapData.length > 0 ? (
              <WeightClassHeatmap data={heatmapData} />
            ) : (
              <p className="text-sm text-[var(--color-text-muted)]">No heatmap data available.</p>
            )}
          </section>

          {/* ── Section 5: Athlete body sizes ─────────────────────────────── */}
          <section className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">Athlete body sizes by weight class</h2>
              <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] max-w-2xl">
                {weightClass
                  ? `Average height and reach for ${weightClass} fighters over time (minimum 5 fighters per year). Select a different weight class above to compare.`
                  : 'Average height and reach per weight class (most recent data, minimum 5 fighters). Select a weight class above to see how athlete sizes have changed over time.'}
              </p>
            </div>

            {physicalData.length > 0 ? (
              <PhysicalStatsChart data={physicalData} weightClass={weightClass} />
            ) : (
              <p className="text-sm text-[var(--color-text-muted)]">No physical stats available.</p>
            )}
          </section>

          {/* ── Section 6: Fighter age by weight class ────────────────────── */}
          <section className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">Fighter age by weight class</h2>
              <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] max-w-2xl">
                {weightClass
                  ? `Average age of ${weightClass} fighters at fight time over the years. Shows whether the division is getting younger or older.`
                  : 'Average age of fighters at the time of their fight, per weight class (most recent data). Select a weight class above to see the trend over time.'}
              </p>
            </div>

            {ageData.length > 0 ? (
              <AgeByWeightClassChart data={ageData} weightClass={weightClass} />
            ) : (
              <p className="text-sm text-[var(--color-text-muted)]">No age data available.</p>
            )}
          </section>

          {/* ── Section 7: Fighter stats by weight class ──────────────────── */}
          <section className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">Fighting style by weight class</h2>
              <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] max-w-2xl">
                Average career stats for fighters in each division — striking output,
                defence, takedown aggression, and submission attempts. Darker cells
                indicate higher values relative to other divisions in the same column.
                Weight class filter does not apply here.
              </p>
            </div>

            {fighterStatsData.length > 0 ? (
              <FighterStatsByWeightClassTable data={fighterStatsData} />
            ) : (
              <p className="text-sm text-[var(--color-text-muted)]">No stats available.</p>
            )}
          </section>
        </>
      )}
    </div>
  )
}
