import type { BettingFightRow } from '@t/api'
import {
  evaluateStrategy, splitAtCutoff, plOf, N_CONCLUSIVE, CONFIRMATION_CUTOFF,
  type PlSource, type StrategyEval,
} from '@utils/strategyStats'

const MUTED = 'text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted)]'
const PRIMARY = 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
const SECONDARY = 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]'
const SUCCESS = 'text-[var(--color-success-light)] dark:text-[var(--color-success)]'
const ERROR = 'text-[var(--color-error-light)] dark:text-[var(--color-error)]'
const WARN = 'text-[var(--color-warning-light)] dark:text-[var(--color-warning)]'

const roiStr = (x: number) => `${x >= 0 ? '+' : ''}${(x * 100).toFixed(1)}%`
const pctStr = (x: number) => `${(x * 100).toFixed(0)}%`

function winRate(fights: BettingFightRow[], src: PlSource): number {
  const p = fights.map(f => plOf(f, src)).filter((x): x is number => x != null)
  return p.length ? p.filter(x => x > 0).length / p.length : 0
}

const usableCount = (fights: BettingFightRow[], src: PlSource) =>
  fights.filter(f => plOf(f, src) != null).length

function MetricRow({ label, roi, win, n, tone, base }: {
  label: string; roi: number; win: number; n: number
  tone: 'pos' | 'neg' | 'muted'; base?: boolean
}) {
  const roiCls = tone === 'pos' ? SUCCESS : tone === 'neg' ? ERROR : MUTED
  return (
    <div className="grid grid-cols-[1fr_auto_auto_auto] items-baseline gap-x-3 border-t border-[var(--color-border)] py-2 first:border-t-0">
      <span className={`text-sm ${base ? SECONDARY : ''}`}>{label}</span>
      <span className={`w-16 text-right font-mono text-sm font-semibold tabular-nums ${roiCls}`}>{roiStr(roi)}</span>
      <span className={`w-10 text-right font-mono text-xs tabular-nums ${MUTED}`}>{pctStr(win)}</span>
      <span className={`w-8 text-right font-mono text-xs tabular-nums ${PRIMARY}`}>{n}</span>
    </div>
  )
}

function Verdict({ ev }: { ev: StrategyEval }) {
  if (ev.kind === 'is-baseline') {
    return <p className={`border-t border-[var(--color-border)] pt-2.5 text-xs ${MUTED}`}>This strategy is the favorite baseline - there is nothing to compare it against.</p>
  }

  const ciLine = ev.ci && (
    <p className={`font-mono text-xs tabular-nums ${MUTED}`}>
      95% CI on strategy ROI: {roiStr(ev.ci.lo)} … {roiStr(ev.ci.hi)}
    </p>
  )
  const vigLine = ev.ci && !ev.clearsVig && (ev.kind === 'tie' || ev.kind === 'beats') && (
    <p className={`text-xs ${MUTED}`}>Even the top of that range doesn&apos;t clear the ~4.5% sportsbook vig.</p>
  )
  const mag = Math.abs(ev.deltaPts).toFixed(1)

  if (ev.kind === 'inconclusive') {
    return (
      <div className="border-t border-[var(--color-border)] pt-2.5">
        <p className={`flex items-baseline gap-2 text-sm font-semibold ${MUTED}`}>
          <span aria-hidden="true">—</span> No verdict: sample too small to compare
        </p>
        <p className={`mt-1 text-xs ${SECONDARY}`}>Widen the filters to reach a conclusive sample (≥&nbsp;{N_CONCLUSIVE}).</p>
      </div>
    )
  }

  const line =
    ev.kind === 'beats' ? { cls: SUCCESS, glyph: '✓', text: `Beats the favorite by ${mag} pts of ROI` }
    : ev.kind === 'loses' ? { cls: ERROR, glyph: '✗', text: `Loses to the favorite by ${mag} pts of ROI` }
    : { cls: PRIMARY, glyph: '=', text: 'Indistinguishable from the favorite baseline' }

  return (
    <div className="border-t border-[var(--color-border)] pt-2.5 space-y-1">
      <p className={`flex items-baseline gap-2 text-sm font-semibold ${line.cls}`}>
        <span aria-hidden="true">{line.glyph}</span> {line.text}
      </p>
      {ciLine}
      {vigLine}
    </div>
  )
}

function ConfirmationCell({ label, fights, src, dead }: {
  label: string; fights: BettingFightRow[]; src: PlSource; dead?: boolean
}) {
  const n = usableCount(fights, src)
  const ev = evaluateStrategy(fights, src)
  const canConfirm = n >= N_CONCLUSIVE
  const tone = n >= N_CONCLUSIVE ? (ev.strategyRoi >= 0 ? SUCCESS : ERROR) : MUTED
  return (
    <div className={`rounded-lg border p-3 ${dead && !canConfirm ? 'border-dashed border-[var(--color-border)] bg-transparent' : 'border-[var(--color-border)] bg-[var(--color-bg-light)] dark:bg-[var(--color-bg)]'}`}>
      <p className={`text-[0.65rem] uppercase tracking-wide ${MUTED}`}>{label}</p>
      {dead && !canConfirm ? (
        <>
          <p className={`mt-1 font-mono text-sm font-semibold ${MUTED}`}>Can&apos;t confirm</p>
          <p className={`mt-0.5 font-mono text-xs tabular-nums ${SECONDARY}`}>n&nbsp;=&nbsp;{n} · below the {N_CONCLUSIVE}-fight bar</p>
        </>
      ) : (
        <>
          <p className={`mt-1 font-mono text-lg font-semibold tabular-nums ${tone}`}>{roiStr(ev.strategyRoi)}</p>
          <p className={`mt-0.5 font-mono text-xs tabular-nums ${SECONDARY}`}>ROI · n&nbsp;=&nbsp;{n} · {dead ? 'out-of-sample' : 'where you hunt'}</p>
        </>
      )}
    </div>
  )
}

function ConfirmationPanel({ fights, src }: { fights: BettingFightRow[]; src: PlSource }) {
  const { exploration, confirmation } = splitAtCutoff(fights)
  return (
    <div className="rounded-lg border border-[var(--color-border)] overflow-hidden">
      <div className="flex items-center gap-2 border-b border-[var(--color-border)] bg-[var(--color-border)]/10 px-3 py-2">
        <span className="rounded bg-[var(--color-primary)] px-1.5 py-0.5 text-[0.6rem] font-bold uppercase tracking-wider text-white">Held-out confirmation</span>
        <span className={`font-mono text-xs tabular-nums ${MUTED}`}>temporal cutoff {CONFIRMATION_CUTOFF}</span>
      </div>
      <div className="grid grid-cols-1 gap-2 p-3 sm:grid-cols-2">
        <ConfirmationCell label={`Exploration · before ${CONFIRMATION_CUTOFF}`} fights={exploration} src={src} />
        <ConfirmationCell label={`Confirmation · ${CONFIRMATION_CUTOFF} onward`} fights={confirmation} src={src} dead />
      </div>
      <p className={`px-3 pb-3 text-xs ${SECONDARY}`}>
        Older fights explore, newer fights confirm, and the confirmation set grows as events land.
        A real edge survives out-of-sample; one found by hunting filters dies here. The confirmation
        set is held to the same {N_CONCLUSIVE}-fight bar - below it, it says so plainly rather than
        posing a number as authority.
      </p>
    </div>
  )
}

export default function StrategyResult({ fights, src }: { fights: BettingFightRow[]; src: PlSource }) {
  const ev = evaluateStrategy(fights, src)
  const conclusive = ev.kind !== 'inconclusive'
  const stratTone: 'pos' | 'neg' | 'muted' = !conclusive ? 'muted' : ev.strategyRoi >= 0 ? 'pos' : 'neg'
  const baseTone: 'pos' | 'neg' | 'muted' = !conclusive ? 'muted' : ev.baselineRoi >= 0 ? 'pos' : 'neg'
  const stratWin = winRate(fights, src)
  const baseWin = winRate(fights.filter(f => plOf(f, src) != null), 'fav')

  return (
    <div className="space-y-3">
      {!conclusive && (
        <div className={`flex items-start gap-2 rounded-lg border border-[var(--color-warning)]/40 bg-[var(--color-warning)]/10 px-3 py-2.5 ${WARN}`}>
          <span aria-hidden="true" className="mt-0.5 shrink-0">⚠</span>
          <p className="text-xs">
            <span className="font-semibold">Not conclusive · n&nbsp;=&nbsp;{ev.n}.</span>{' '}
            <span className={SECONDARY}>{ev.n} fights is below the {N_CONCLUSIVE}-fight bar. This can&apos;t be separated from luck. It is not a finding.</span>
          </p>
        </div>
      )}

      <div className="rounded-lg border border-[var(--color-border)] bg-white px-4 py-3 dark:bg-[var(--color-surface)]">
        <div className="grid grid-cols-[1fr_auto_auto_auto] gap-x-3 pb-0.5">
          <span className={`text-[0.6rem] uppercase tracking-wide ${MUTED}`}>Strategy vs baseline</span>
          <span className={`w-16 text-right text-[0.6rem] uppercase tracking-wide ${MUTED}`}>ROI</span>
          <span className={`w-10 text-right text-[0.6rem] uppercase tracking-wide ${MUTED}`}>Win</span>
          <span className={`w-8 text-right text-[0.6rem] uppercase tracking-wide ${MUTED}`}>n</span>
        </div>
        <MetricRow label="This strategy" roi={ev.strategyRoi} win={stratWin} n={ev.n} tone={stratTone} />
        {src !== 'fav' && (
          <MetricRow label="Always the favorite" roi={ev.baselineRoi} win={baseWin} n={ev.n} tone={baseTone} base />
        )}
        <Verdict ev={ev} />
      </div>

      {src !== 'fav' && ev.n > 0 && <ConfirmationPanel fights={fights} src={src} />}
    </div>
  )
}
