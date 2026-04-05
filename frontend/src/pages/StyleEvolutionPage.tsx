import { useState } from 'react'
import { analyticsService } from '@services/analyticsService'
import { useApi } from '@hooks/useApi'
import WeightClassFilter from '@components/features/WeightClassFilter'
import FinishRateChart from '@components/features/FinishRateChart'
import FighterOutputChart from '@components/features/FighterOutputChart'
import LoadingSpinner from '@components/common/LoadingSpinner'

export default function StyleEvolutionPage() {
  const [weightClass, setWeightClass] = useState<string | null>(null)

  const { data, loading, error } = useApi(
    () => analyticsService.getStyleEvolution(weightClass ?? undefined),
    [weightClass],
  )

  const finishData = data?.data ?? []
  const outputData = data?.fighter_outputs ?? []

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-12">

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">How the UFC Has Changed</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
          Finish rates and fighter outputs over time
        </p>
      </div>

      {/* Weight class filter — applies to both sections */}
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
            <div>
              <h2 className="text-lg font-semibold">How fights end</h2>
              <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] max-w-2xl">
                The UFC has become a decision-heavy sport. In 2001, nearly 7 in 10 fights ended
                before the final bell. By 2024, that number had flipped — over half of all fights
                go to the judges.
              </p>
            </div>

            {finishData.length > 0 ? (
              <FinishRateChart data={finishData} />
            ) : (
              <p className="text-sm text-[var(--color-text-muted)]">No data for this weight class.</p>
            )}
          </section>

          {/* ── Section 2: How fighters fight ────────────────────────────── */}
          <section className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">How fighters fight</h2>
              <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] max-w-2xl">
                Average outputs per fighter per fight since 2015 — striking volume, takedown
                aggression, and control time. Dashed bars indicate the current partial year.
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
        </>
      )}
    </div>
  )
}
