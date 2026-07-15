import { useState, useEffect, useCallback } from 'react'
import { analyticsService } from '@services/analyticsService'
import type { UpsetFightCard as UpsetFightCardData } from '@t/api'
import Pagination from '@components/common/Pagination'
import UpsetFightCard from './UpsetFightCard'

const WEIGHT_CLASSES_ORDERED = [
  "Women's Strawweight", "Women's Flyweight", "Women's Bantamweight", "Women's Featherweight",
  'Flyweight', 'Bantamweight', 'Featherweight', 'Lightweight',
  'Welterweight', 'Middleweight', 'Light Heavyweight', 'Heavyweight',
]

const CONVICTION_OPTIONS = [
  { value: 0.20, label: 'Any ≥20pp' },
  { value: 0.30, label: 'High ≥30pp' },
  { value: 0.40, label: 'Very high ≥40pp' },
]

const PAGE_SIZE = 10

export function UpsetFightCards() {
  const [weightClass, setWeightClass] = useState<string>('')
  const [convictionMin, setConvictionMin] = useState<number>(0.20)
  const [fights, setFights] = useState<UpsetFightCardData[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)

  const load = useCallback(async (wc: string, conv: number) => {
    setLoading(true)
    try {
      const res = await analyticsService.getBettingUpsets({
        weight_class: wc || null,
        conviction_min: conv,
      })
      setFights(res.fights)
      setPage(1)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(weightClass, convictionMin) }, [weightClass, convictionMin, load])

  const totalPages = Math.ceil(fights.length / PAGE_SIZE)
  const visible    = fights.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div className="space-y-5">
      {/* Definition */}
      <p className="text-sm text-[var(--color-text-muted)]">
        <strong className="text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">"Upset" here</strong> means the model was wrong AND had ≥20pp conviction (model win prob ≥70%) on the losing pick. This is NOT the same as a Vegas underdog winning — it measures where the model gets confidently fooled. Includes all past predictions, not just Vegas-odds fights.
      </p>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={weightClass}
          onChange={(e) => setWeightClass(e.target.value)}
          className="rounded border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
        >
          <option value="">All divisions</option>
          {WEIGHT_CLASSES_ORDERED.map((wc) => (
            <option key={wc} value={wc}>{wc}</option>
          ))}
        </select>
        <select
          value={convictionMin}
          onChange={(e) => setConvictionMin(Number(e.target.value))}
          className="rounded border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
        >
          {CONVICTION_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg bg-[var(--color-border)]" />
          ))}
        </div>
      ) : fights.length === 0 ? (
        <p className="text-sm text-[var(--color-text-muted)]">No upsets match this filter.</p>
      ) : (
        <>
          <div className="space-y-2">
            {visible.map((f) => <UpsetFightCard key={f.fight_id} f={f} />)}
          </div>
          <Pagination
            page={page}
            totalPages={totalPages}
            onPrev={() => setPage(p => p - 1)}
            onNext={() => setPage(p => p + 1)}
            total={fights.length}
            pageSize={PAGE_SIZE}
          />
        </>
      )}
    </div>
  )
}
