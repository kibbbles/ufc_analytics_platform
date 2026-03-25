import { useState, useEffect, useRef } from 'react'

interface Props {
  nameA: string
  nameB: string
  modelProbA: number | null
  modelProbB: number | null
  initialOddsA?: number | null
  initialOddsB?: number | null
}

// ── Math helpers ──────────────────────────────────────────────────────────────

function americanToImplied(odds: number): number {
  if (odds > 0) return 100 / (odds + 100)
  return (-odds) / (-odds + 100)
}

function americanToPayout(odds: number, stake: number): number {
  if (odds > 0) return (stake * odds) / 100
  return (stake * 100) / -odds
}

function ev(modelProb: number, odds: number, stake: number): number {
  return modelProb * americanToPayout(odds, stake) - (1 - modelProb) * stake
}

function parseOdds(raw: string): number | null {
  const n = Number(raw.replace(/\s/g, ''))
  if (!Number.isFinite(n) || n === 0) return null
  if (n > 0 && n < 100) return null
  if (n < 0 && n > -100) return null
  return n
}

const EDGE_THRESHOLD = 0.05

// ── Component ─────────────────────────────────────────────────────────────────

export default function OddsCalculator({
  nameA,
  nameB,
  modelProbA,
  modelProbB,
  initialOddsA,
  initialOddsB,
}: Props) {
  const [open, setOpen] = useState(false)
  const [oddsAStr, setOddsAStr] = useState('')
  const [oddsBStr, setOddsBStr] = useState('')
  const [betStr, setBetStr] = useState('100')
  const containerRef = useRef<HTMLDivElement>(null)

  // Pre-fill from DB odds once available (don't overwrite user edits)
  useEffect(() => {
    if (initialOddsA != null && oddsAStr === '') setOddsAStr(String(initialOddsA))
  }, [initialOddsA]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (initialOddsB != null && oddsBStr === '') setOddsBStr(String(initialOddsB))
  }, [initialOddsB]) // eslint-disable-line react-hooks/exhaustive-deps

  // Close on click outside
  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const oddsA = parseOdds(oddsAStr)
  const oddsB = parseOdds(oddsBStr)
  const stake = Math.max(1, parseFloat(betStr) || 100)

  function calcRow(odds: number | null, modelProb: number | null) {
    if (odds == null || modelProb == null) return null
    const implied = americanToImplied(odds)
    const edge    = modelProb - implied
    return { implied, edge, ev: ev(modelProb, odds, stake) }
  }

  const rowA = calcRow(oddsA, modelProbA)
  const rowB = calcRow(oddsB, modelProbB)

  const lastA = nameA.split(' ').pop() ?? 'A'
  const lastB = nameB.split(' ').pop() ?? 'B'

  let verdict: string | null = null
  let verdictGood = false

  if (rowA || rowB) {
    const edgeA = rowA?.edge ?? -Infinity
    const edgeB = rowB?.edge ?? -Infinity
    const best  = edgeA >= edgeB
      ? { name: lastA, edge: edgeA }
      : { name: lastB, edge: edgeB }

    if (best.edge > EDGE_THRESHOLD) {
      verdict = `Value on ${best.name}`
      verdictGood = true
    } else if (best.edge > 0) {
      verdict = 'Thin edge — use caution'
    } else {
      verdict = 'No edge found'
    }
  }

  return (
    <div ref={containerRef} className="fixed bottom-4 left-4 z-40 flex flex-col items-start">
      {/* ── Expanded panel ── */}
      {open && (
        <div className="mb-2 w-72 rounded-xl border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
            <span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
              EV Calculator
            </span>
            <button
              onClick={() => setOpen(false)}
              className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]"
              aria-label="Close"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-3 px-4 py-3">
            {/* Bet amount */}
            <div className="flex items-center gap-3">
              <span className="shrink-0 text-xs text-[var(--color-text-muted)]">Bet ($)</span>
              <input
                type="number"
                inputMode="decimal"
                value={betStr}
                onChange={e => setBetStr(e.target.value)}
                className="w-full rounded border border-[var(--color-border)] bg-transparent px-2 py-1 text-center text-sm font-mono tabular-nums text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)] focus:border-[var(--color-primary)] focus:outline-none"
                placeholder="100"
              />
            </div>

            {/* Fighter rows */}
            {([
              { label: lastA, oddsStr: oddsAStr, setOdds: setOddsAStr, result: rowA, modelProb: modelProbA, parsedOdds: oddsA },
              { label: lastB, oddsStr: oddsBStr, setOdds: setOddsBStr, result: rowB, modelProb: modelProbB, parsedOdds: oddsB },
            ] as const).map(({ label, oddsStr, setOdds, result, modelProb, parsedOdds }) => (
              <div key={label} className="rounded-lg border border-[var(--color-border)] p-3">
                <div className="mb-2 flex items-center gap-2">
                  <span className="w-16 shrink-0 truncate text-xs font-semibold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">
                    {label}
                  </span>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={oddsStr}
                    onChange={e => setOdds(e.target.value)}
                    className="w-full rounded border border-[var(--color-border)] bg-transparent px-2 py-1 text-center text-sm font-mono tabular-nums text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-primary)] focus:outline-none"
                    placeholder="-150 or +130"
                  />
                </div>

                {result ? (
                  <>
                    <div className="grid grid-cols-3 gap-x-1 text-center">
                      <div>
                        <div className="text-[10px] text-[var(--color-text-muted)]">Implied</div>
                        <div className="font-mono text-xs tabular-nums">
                          {(result.implied * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-[var(--color-text-muted)]">Model</div>
                        <div className="font-mono text-xs tabular-nums">
                          {modelProb != null ? `${(modelProb * 100).toFixed(1)}%` : '—'}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-[var(--color-text-muted)]">Edge</div>
                        <div className={`font-mono text-xs font-semibold tabular-nums ${
                          result.edge > EDGE_THRESHOLD ? 'text-green-500'
                          : result.edge > 0 ? 'text-yellow-500'
                          : 'text-red-500'
                        }`}>
                          {result.edge >= 0 ? '+' : ''}{(result.edge * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                    <div className="mt-2 border-t border-[var(--color-border)] pt-2 text-center">
                      <span className="text-[10px] text-[var(--color-text-muted)]">EV </span>
                      <span className={`font-mono text-sm font-bold tabular-nums ${result.ev > 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {result.ev >= 0 ? `+$${result.ev.toFixed(2)}` : `-$${Math.abs(result.ev).toFixed(2)}`}
                      </span>
                      <span className="text-[10px] text-[var(--color-text-muted)]"> on ${stake.toFixed(0)}</span>
                    </div>
                    <div className="text-center text-[10px] text-[var(--color-text-muted)] mt-1">
                      Collect <span className="font-mono tabular-nums text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]">${(stake + americanToPayout(parsedOdds!, stake)).toFixed(2)}</span> if correct
                    </div>
                  </>
                ) : (
                  <p className="text-center text-[10px] text-[var(--color-text-muted)]">Enter odds above</p>
                )}
              </div>
            ))}

            {verdict && (
              <div className={`rounded-lg px-3 py-2 text-center text-xs font-semibold ${
                verdictGood
                  ? 'bg-green-500/10 text-green-600 dark:text-green-400'
                  : verdict.startsWith('No')
                  ? 'bg-red-500/10 text-red-600 dark:text-red-400'
                  : 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400'
              }`}>
                {verdict}
              </div>
            )}

            <p className="text-center text-[10px] text-[var(--color-text-muted)]">
              &gt;5% edge = value, 0–5% = thin edge, negative = no value.
            </p>
          </div>
        </div>
      )}

      {/* ── Toggle button — calculator icon ── */}
      <button
        onClick={() => setOpen(o => !o)}
        className="flex h-10 w-10 items-center justify-center rounded-full border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] shadow-lg transition-colors hover:border-[var(--color-primary)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary-light)] dark:hover:text-[var(--color-text-primary)]"
        aria-label="Toggle EV calculator"
      >
        {/* Calculator SVG icon */}
        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
          <rect x="4" y="2" width="16" height="20" rx="2" />
          <rect x="7" y="5" width="10" height="4" rx="1" />
          <circle cx="8" cy="13" r="1" fill="currentColor" stroke="none" />
          <circle cx="12" cy="13" r="1" fill="currentColor" stroke="none" />
          <circle cx="16" cy="13" r="1" fill="currentColor" stroke="none" />
          <circle cx="8" cy="17" r="1" fill="currentColor" stroke="none" />
          <circle cx="12" cy="17" r="1" fill="currentColor" stroke="none" />
          <circle cx="16" cy="17" r="1" fill="currentColor" stroke="none" />
        </svg>
      </button>
    </div>
  )
}
