import { useState, useEffect } from 'react'

interface Props {
  nameA: string
  nameB: string
  modelProbA: number | null
  modelProbB: number | null
  initialOddsA?: number | null
  initialOddsB?: number | null
}

// ── Math helpers ──────────────────────────────────────────────────────────────

/** American odds → implied win probability (vig-inclusive) */
function americanToImplied(odds: number): number {
  if (odds > 0) return 100 / (odds + 100)
  return (-odds) / (-odds + 100)
}

/** Profit on a winning bet at these American odds */
function americanToPayout(odds: number, stake: number): number {
  if (odds > 0) return (stake * odds) / 100
  return (stake * 100) / -odds
}

/** Expected value of a single bet */
function ev(modelProb: number, odds: number, stake: number): number {
  return modelProb * americanToPayout(odds, stake) - (1 - modelProb) * stake
}

/** Parse a raw odds string — must be ≥ +100 or ≤ -100 to be valid */
function parseOdds(raw: string): number | null {
  const n = Number(raw.replace(/\s/g, ''))
  if (!Number.isFinite(n) || n === 0) return null
  if (n > 0 && n < 100) return null   // e.g. "50" is not valid American odds
  if (n < 0 && n > -100) return null  // e.g. "-50" is not valid
  return n
}

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
  const [betStr, setBetStr] = useState('25')

  // Pre-fill from DB odds once available (don't overwrite user edits)
  useEffect(() => {
    if (initialOddsA != null && oddsAStr === '')
      setOddsAStr(String(initialOddsA))
  }, [initialOddsA]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (initialOddsB != null && oddsBStr === '')
      setOddsBStr(String(initialOddsB))
  }, [initialOddsB]) // eslint-disable-line react-hooks/exhaustive-deps

  const oddsA  = parseOdds(oddsAStr)
  const oddsB  = parseOdds(oddsBStr)
  const stake  = Math.max(1, parseFloat(betStr) || 25)

  // Per-fighter calculated row
  function calcRow(odds: number | null, modelProb: number | null) {
    if (odds == null || modelProb == null) return null
    const implied = americanToImplied(odds)
    const edge    = modelProb - implied
    const evVal   = ev(modelProb, odds, stake)
    return { implied, edge, ev: evVal }
  }

  const rowA = calcRow(oddsA, modelProbA)
  const rowB = calcRow(oddsB, modelProbB)

  // Verdict logic: need >2% edge to call it "value"
  const EDGE_THRESHOLD = 0.02
  let verdict: string | null = null
  let verdictGood = false

  const lastA = nameA.split(' ').pop() ?? 'A'
  const lastB = nameB.split(' ').pop() ?? 'B'

  if (rowA || rowB) {
    const edgeA = rowA?.edge ?? -Infinity
    const edgeB = rowB?.edge ?? -Infinity
    const best  = edgeA >= edgeB ? { name: lastA, edge: edgeA, row: rowA } : { name: lastB, edge: edgeB, row: rowB }

    if (best.edge > EDGE_THRESHOLD) {
      verdict = `Value on ${best.name}`
      verdictGood = true
    } else if (best.edge > 0) {
      verdict = 'Thin edge — use caution'
    } else {
      verdict = 'No edge found'
    }
  }

  // Dot color for collapsed button
  const dotColor = !verdict ? null
    : verdictGood ? 'bg-green-500'
    : verdict.startsWith('No') ? 'bg-red-500'
    : 'bg-yellow-500'

  return (
    <div className="fixed bottom-4 left-4 z-40 flex flex-col items-start">
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
              aria-label="Close calculator"
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
                placeholder="25"
              />
            </div>

            {/* Fighter rows */}
            {(
              [
                { label: lastA, oddsStr: oddsAStr, setOdds: setOddsAStr, result: rowA, modelProb: modelProbA },
                { label: lastB, oddsStr: oddsBStr, setOdds: setOddsBStr, result: rowB, modelProb: modelProbB },
              ] as const
            ).map(({ label, oddsStr, setOdds, result, modelProb }) => (
              <div key={label} className="rounded-lg border border-[var(--color-border)] p-3">
                {/* Name + odds input */}
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
                    {/* Stats grid */}
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
                        <div
                          className={`font-mono text-xs font-semibold tabular-nums ${
                            result.edge > EDGE_THRESHOLD
                              ? 'text-green-500'
                              : result.edge > 0
                              ? 'text-yellow-500'
                              : 'text-red-500'
                          }`}
                        >
                          {result.edge >= 0 ? '+' : ''}{(result.edge * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>

                    {/* EV line */}
                    <div className="mt-2 border-t border-[var(--color-border)] pt-2 text-center">
                      <span className="text-[10px] text-[var(--color-text-muted)]">EV </span>
                      <span
                        className={`font-mono text-sm font-bold tabular-nums ${
                          result.ev > 0 ? 'text-green-500' : 'text-red-500'
                        }`}
                      >
                        {result.ev >= 0 ? '+' : ''}${result.ev.toFixed(2)}
                      </span>
                      <span className="text-[10px] text-[var(--color-text-muted)]">
                        {' '}on ${stake.toFixed(0)}
                      </span>
                    </div>
                  </>
                ) : (
                  <p className="text-center text-[10px] text-[var(--color-text-muted)]">
                    Enter odds above
                  </p>
                )}
              </div>
            ))}

            {/* Verdict */}
            {verdict && (
              <div
                className={`rounded-lg px-3 py-2 text-center text-xs font-semibold ${
                  verdictGood
                    ? 'bg-green-500/10 text-green-600 dark:text-green-400'
                    : verdict.startsWith('No')
                    ? 'bg-red-500/10 text-red-600 dark:text-red-400'
                    : 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400'
                }`}
              >
                {verdict}
              </div>
            )}

            <p className="text-center text-[10px] text-[var(--color-text-muted)]">
              Edge = model prob − Vegas implied prob
            </p>
          </div>
        </div>
      )}

      {/* ── Toggle pill ── */}
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 rounded-full border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-3 py-2 text-xs font-semibold shadow-lg transition-colors hover:border-[var(--color-primary)] text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]"
        aria-label="Toggle EV calculator"
      >
        {dotColor && (
          <span className={`h-2 w-2 rounded-full ${dotColor}`} />
        )}
        <span>EV Calc</span>
      </button>
    </div>
  )
}
