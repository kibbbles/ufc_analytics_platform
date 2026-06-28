import { useState } from 'react'
import { useApi } from '@hooks/useApi'
import { analyticsService } from '@services/analyticsService'
import { StrategyTicker } from '@components/features/StrategyTicker'
import { BettingHero } from '@components/features/BettingHero'
import { BettingKPIRow } from '@components/features/BettingKPIRow'
import { OverviewTab } from '@components/features/OverviewTab'
import { StrategyLeaderboard } from '@components/features/StrategyLeaderboard'
import { VegasCalibrationChart } from '@components/features/VegasCalibrationChart'
import { UpsetFightCards } from '@components/features/UpsetFightCards'
import { StrategyBuilder } from '@components/features/StrategyBuilder'

const TABS = [
  { id: 'overview',    label: 'Overview' },
  { id: 'strategies',  label: 'Strategies' },
  { id: 'calibration', label: 'Calibration' },
  { id: 'upsets',      label: 'Upsets' },
  { id: 'builder',     label: 'Build a Strategy' },
] as const

type TabId = (typeof TABS)[number]['id']

export default function BettingInsightsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const { data, loading, error } = useApi(() => analyticsService.getBettingInsights(), [])

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-6">
        <div className="h-8 w-64 rounded bg-[var(--color-border)] animate-pulse mb-4" />
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 rounded-lg bg-[var(--color-border)] animate-pulse" />
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
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-0">
      {/* Ticker */}
      <StrategyTicker strategies={data.strategies} />

      {/* Hero */}
      <BettingHero data={data} />

      {/* KPI row */}
      <BettingKPIRow data={data} />

      {/* Tab bar */}
      <div
        className="flex border-b border-[var(--color-border)] overflow-x-auto"
        style={{ scrollbarWidth: 'none' }}
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`shrink-0 px-4 py-2.5 text-sm font-medium transition-colors whitespace-nowrap ${
              activeTab === tab.id
                ? 'border-b-2 border-[var(--color-text)] text-[var(--color-text)]'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
            }`}
            style={{ marginBottom: activeTab === tab.id ? '-1px' : 0 }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="pt-6 pb-12">
        {activeTab === 'overview' && <OverviewTab />}

        {activeTab === 'strategies' && <StrategyLeaderboard strategies={data.strategies} />}

        {activeTab === 'calibration' && <VegasCalibrationChart data={data.calibration} />}

        {activeTab === 'upsets' && <UpsetFightCards />}

        {activeTab === 'builder' && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-semibold">Build Your Own Strategy</h2>
              <p className="text-sm text-[var(--color-text-muted)]">
                Combine filters to define a custom betting strategy. Results update live.
              </p>
            </div>
            <StrategyBuilder />
          </div>
        )}
      </div>
    </div>
  )
}
