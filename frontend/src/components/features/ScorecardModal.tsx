import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { pastPredictionsService } from '@services/pastPredictionsService'
import { LoadingSkeleton } from '@components/common'
import { formatDate } from '@utils/format'
import type { PastPredictionModalStats, PastPredictionItem } from '@t/api'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPct(v: number): string {
  return (v * 100).toFixed(1) + '%'
}

function winnerName(item: PastPredictionItem, id: string | null | undefined): string {
  if (!id) return '—'
  if (id === item.fighter_a_id) return item.fighter_a_name ?? '—'
  if (id === item.fighter_b_id) return item.fighter_b_name ?? '—'
  return '—'
}

// ---------------------------------------------------------------------------
// Fight row (compact, used inside the modal list)
// ---------------------------------------------------------------------------

function ModalFightRow({ item }: { item: PastPredictionItem }) {
  const isUpset   = item.is_upset
  const isCorrect = item.is_correct

  let indicator: string
  let indicatorColor: string
  if (isUpset)        { indicator = '~'; indicatorColor = 'text-amber-500' }
  else if (isCorrect) { indicator = '✓'; indicatorColor = 'text-green-500' }
  else                { indicator = '✗'; indicatorColor = 'text-[var(--color-primary)]' }

  const rowBg = isUpset
    ? 'bg-amber-500/5'
    : ''

  return (
    <Link
      to={`/past-predictions/fights/${item.fight_id}`}
      className={`flex items-center gap-2 py-2.5 border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] last:border-0 ${rowBg}`}
    >
      <span className={`font-mono font-bold text-sm w-4 shrink-0 ${indicatorColor}`}>
        {indicator}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium leading-tight truncate">
          {item.fighter_a_name ?? '?'} vs {item.fighter_b_name ?? '?'}
        </p>
        <p className="text-[11px] text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] truncate">
          {item.event_name ?? '—'}
          {item.event_date ? ` · ${formatDate(item.event_date)}` : ''}
        </p>
      </div>
      <div className="shrink-0 text-right">
        {item.confidence != null && (
          <p className="font-mono text-xs tabular-nums text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
            {formatPct(item.confidence)}
          </p>
        )}
        <p className="text-[11px] text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
          {winnerName(item, item.predicted_winner_id)?.split(' ').pop() ?? '—'}
        </p>
      </div>
    </Link>
  )
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export type ScorecardModalMode = 'all' | 'pre_fight'

interface Props {
  mode: ScorecardModalMode
  onClose: () => void
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

export default function ScorecardModal({ mode, onClose }: Props) {
  const [stats, setStats]   = useState<PastPredictionModalStats | null>(null)
  const [fights, setFights] = useState<PastPredictionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState<string | null>(null)

  const title = mode === 'all' ? 'All Predictions' : 'Live Pre-Fight'

  // Keyboard + scroll lock
  useEffect(() => {
    function onKey(e: KeyboardEvent) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [onClose])

  // Fetch on open
  useEffect(() => {
    let cancelled = false
    const source = mode === 'pre_fight' ? 'pre_fight_archive' : undefined

    Promise.all([
      pastPredictionsService.getModalStats(),
      pastPredictionsService.searchFights({
        prediction_source: source,
        page: 1,
        page_size: 20,
      }),
    ])
      .then(([statsData, fightsData]) => {
        if (!cancelled) {
          setStats(statsData)
          setFights(fightsData.data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.message ?? 'Failed to load')
          setLoading(false)
        }
      })

    return () => { cancelled = true }
  }, [mode])

  const section = stats ? (mode === 'all' ? stats.all : stats.pre_fight) : null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60 p-4 flex items-center justify-center"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Centered modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`${title} details`}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
      >
        <div className="pointer-events-auto w-full max-w-lg flex flex-col rounded-xl border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] shadow-2xl max-h-[85vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 shrink-0 border-b border-[var(--color-border-light)] dark:border-[var(--color-border)]">
          <h2 className="font-bold text-base">{title}</h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]"
            aria-label="Close"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-5 pb-6">
          {loading ? (
            <LoadingSkeleton lines={8} />
          ) : error ? (
            <p className="text-sm text-red-500 text-center py-4">{error}</p>
          ) : (
            <>
              {/* Model performance — Brier + ROC-AUC */}
              {section && (section.brier_score != null || section.roc_auc != null) && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] px-3 py-2.5">
                    <p className="text-[11px] uppercase tracking-wide text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                      Brier Score
                    </p>
                    <p className="font-mono text-lg font-bold tabular-nums mt-0.5">
                      {section.brier_score != null ? section.brier_score.toFixed(3) : '—'}
                    </p>
                    <p className="text-[10px] text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] mt-0.5">
                      lower is better · 0.25 = random
                    </p>
                  </div>
                  <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] px-3 py-2.5">
                    <p className="text-[11px] uppercase tracking-wide text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                      ROC-AUC
                    </p>
                    <p className="font-mono text-lg font-bold tabular-nums mt-0.5">
                      {section.roc_auc != null ? section.roc_auc.toFixed(3) : '—'}
                    </p>
                    <p className="text-[10px] text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] mt-0.5">
                      higher is better · 0.5 = random
                    </p>
                  </div>
                </div>
              )}

              {/* Calibration callout */}
              {section && (
                section.avg_conf_correct != null || section.avg_conf_incorrect != null
              ) && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] px-3 py-2.5">
                    <p className="text-[11px] uppercase tracking-wide text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                      Avg conviction · correct
                    </p>
                    <p className="font-mono text-lg font-bold tabular-nums text-green-500 mt-0.5">
                      {section.avg_conf_correct != null ? formatPct(section.avg_conf_correct) : '—'}
                    </p>
                  </div>
                  <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] px-3 py-2.5">
                    <p className="text-[11px] uppercase tracking-wide text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">
                      Avg conviction · wrong
                    </p>
                    <p className="font-mono text-lg font-bold tabular-nums text-[var(--color-primary)] mt-0.5">
                      {section.avg_conf_incorrect != null ? formatPct(section.avg_conf_incorrect) : '—'}
                    </p>
                  </div>
                </div>
              )}

              {/* Confidence buckets */}
              {section && section.conf_buckets.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] mb-2">
                    By Conviction
                  </h3>
                  <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] overflow-hidden">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-border)]/10">
                          <th className="text-left px-3 py-2 font-medium text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">Range</th>
                          <th className="text-right px-3 py-2 font-medium text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">Fights</th>
                          <th className="text-right px-3 py-2 font-medium text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">Correct</th>
                          <th className="text-right px-3 py-2 font-medium text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">Accuracy</th>
                        </tr>
                      </thead>
                      <tbody>
                        {section.conf_buckets.map((b) => (
                          <tr
                            key={b.label}
                            className="border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] last:border-0"
                          >
                            <td className="px-3 py-2 font-mono tabular-nums">{b.label}</td>
                            <td className="px-3 py-2 font-mono tabular-nums text-right text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">{b.fights}</td>
                            <td className="px-3 py-2 font-mono tabular-nums text-right text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">{b.correct}</td>
                            <td className="px-3 py-2 font-mono tabular-nums text-right font-semibold">{formatPct(b.accuracy)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Weight class breakdown */}
              {section && section.weight_classes.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] mb-2">
                    By weight class
                  </h3>
                  <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] overflow-hidden">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-border)]/10">
                          <th className="text-left px-3 py-2 font-medium text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">Class</th>
                          <th className="text-right px-3 py-2 font-medium text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">Fights</th>
                          <th className="text-right px-3 py-2 font-medium text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">Accuracy</th>
                        </tr>
                      </thead>
                      <tbody>
                        {section.weight_classes.map((w) => (
                          <tr
                            key={w.weight_class}
                            className="border-b border-[var(--color-border-light)] dark:border-[var(--color-border)] last:border-0"
                          >
                            <td className="px-3 py-2 truncate max-w-[140px]">{w.weight_class}</td>
                            <td className="px-3 py-2 font-mono tabular-nums text-right text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]">{w.fights}</td>
                            <td className="px-3 py-2 font-mono tabular-nums text-right font-semibold">{formatPct(w.accuracy)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Recent fights */}
              {fights.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] mb-2">
                    Recent fights
                  </h3>
                  <div className="rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] px-3">
                    {fights.map((f) => (
                      <ModalFightRow key={f.fight_id} item={f} />
                    ))}
                  </div>
                </div>
              )}

              {fights.length === 0 && section && section.conf_buckets.length === 0 && (
                <p className="text-center text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)] py-8">
                  No fights recorded yet.
                </p>
              )}
            </>
          )}
        </div>
        </div>{/* inner card */}
      </div>{/* centering shell */}
    </>
  )
}
