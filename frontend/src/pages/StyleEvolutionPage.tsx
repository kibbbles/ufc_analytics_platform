import { useState } from 'react'
import { analyticsService } from '@services/analyticsService'
import { useApi } from '@hooks/useApi'
import WeightClassFilter from '@components/features/WeightClassFilter'
import FinishRateChart from '@components/features/FinishRateChart'
import FighterOutputChart from '@components/features/FighterOutputChart'
import RoundDistributionChart from '@components/features/RoundDistributionChart'
import WeightClassHeatmap from '@components/features/WeightClassHeatmap'
import PhysicalStatsChart from '@components/features/PhysicalStatsChart'
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

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-12">

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">How the UFC Has Changed</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
          Finish rates, fighter outputs, and athletic profiles over time
        </p>
      </div>

      {/* Weight class filter — applies to sections 1–3 */}
      <WeightClassFilter value={weightClass} onChange={setWeightClass} />

      {loading && (
        <div className="flex justify-center py-16">
          <LoadingSpinner />
        </div>
      )}

      {error && (
        <p className="text-sm text-red-500">Failed to load data. Try refreshing.</p>
      )}

      {!loading && !error && data && (
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
                Average height and reach across all fighters active in each weight class
                (most recent available data, minimum 5 fighters). Heavier classes skew
                taller, and reach typically exceeds height at every level. Weight class
                filter does not apply here.
              </p>
            </div>

            {physicalData.length > 0 ? (
              <PhysicalStatsChart data={physicalData} />
            ) : (
              <p className="text-sm text-[var(--color-text-muted)]">No physical stats available.</p>
            )}
          </section>
        </>
      )}
    </div>
  )
}
