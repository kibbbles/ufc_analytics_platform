import { useApi } from '@hooks/useApi'
import { analyticsService } from '@services/analyticsService'
import { StrategyLeaderboard } from '@components/features/StrategyLeaderboard'
import { VegasCalibrationChart } from '@components/features/VegasCalibrationChart'
import { UpsetRateChart } from '@components/features/UpsetRateChart'
import { ROIOverTimeChart } from '@components/features/ROIOverTimeChart'
import { StrategyBuilder } from '@components/features/StrategyBuilder'

export default function BettingInsightsPage() {
  const { data, loading, error } = useApi(() => analyticsService.getBettingInsights(), [])

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="h-8 w-48 rounded bg-[var(--color-border)] animate-pulse mb-2" />
        <div className="h-4 w-64 rounded bg-[var(--color-border)] animate-pulse" />
        <div className="mt-12 space-y-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-48 rounded-lg bg-[var(--color-border)] animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <p className="text-[var(--color-text-muted)]">Failed to load betting insights. Try refreshing.</p>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-14">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Betting Insights</h1>
        <p className="mt-1 text-[var(--color-text-muted)]">
          Model vs Vegas: strategy ROI, calibration, and upset patterns.{' '}
          <span className="font-mono tabular-nums">{data.sample_size}</span> fights with Vegas odds
          tracked so far — sample grows weekly.
        </p>
      </div>

      {/* Strategy Leaderboard */}
      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Strategy ROI Leaderboard</h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            Flat $1 unit per bet. Ranked by ROI.
          </p>
        </div>
        <StrategyLeaderboard strategies={data.strategies} />
      </section>

      {/* Vegas Calibration */}
      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Vegas Calibration</h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            Does Vegas implied probability match actual favourite win rates? Bars above the implied
            line mean Vegas underpriced the favourite.
          </p>
        </div>
        <VegasCalibrationChart data={data.calibration} />
      </section>

      {/* Upset Rate by Weight Class */}
      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Model Upset Rate by Weight Class</h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            Where does the model get caught out? An "upset" here means the model was wrong{' '}
            <em>and</em> had high conviction (≥30%). Uses all predictions, not just Vegas fights.
          </p>
        </div>
        <UpsetRateChart data={data.upset_rates} />
      </section>

      {/* ROI Over Time */}
      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">ROI Over Time (model-pick strategy)</h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            Cumulative P&L per event since Vegas odds tracking began. Upward trend = model has edge.
          </p>
        </div>
        <ROIOverTimeChart data={data.roi_over_time} />
      </section>

      {/* Strategy Builder */}
      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Build Your Own Strategy</h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            Combine filters to define a custom betting strategy. Results update live.
          </p>
        </div>
        <StrategyBuilder />
        <p className="text-xs text-[var(--color-text-muted)]">
          Note: edge filter is relative to Vegas implied probability on the selected bet side.
          Conviction = max(win prob) − 50%.
        </p>
      </section>
    </div>
  )
}
