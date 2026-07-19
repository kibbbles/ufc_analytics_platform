import type { BettingFightRow } from '@t/api'
import InfoTooltip from '@components/common/InfoTooltip'
import { formatEventDate, EMPTY } from '@utils/format'

type PlSource = 'model' | 'fav' | 'dog' | 'younger'

export default function BettingFightCard({ f, mode }: { f: BettingFightRow; mode: PlSource }) {
  const inHotZone = f.edge_pp >= 5 && f.edge_pp <= 15
  const showPills = mode === 'model'

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4 py-3 text-sm">
      {/* Matchup + result badge */}
      <div className="flex items-start justify-between gap-3">
        <p className="font-semibold">
          <span>{f.pick ?? EMPTY}</span>
          <span className="text-[var(--color-text-muted)] font-normal"> vs </span>
          <span className="text-[var(--color-text-muted)] font-normal">{f.opponent ?? EMPTY}</span>
        </p>
        <span
          className={`shrink-0 text-xs font-semibold px-1.5 py-0.5 rounded ${
            f.is_correct
              ? 'bg-[var(--color-success)]/15 text-[var(--color-success-light)] dark:text-[var(--color-success)]'
              : 'bg-[var(--color-error)]/15 text-[var(--color-error-light)] dark:text-[var(--color-error)]'
          }`}
        >
          {f.is_correct ? '✓' : '✗'}
        </span>
      </div>

      {/* Actual result */}
      <p className="mt-0.5 text-[var(--color-warning-light)] dark:text-[var(--color-warning)]">
        {f.actual_winner_name
          ? `${f.actual_winner_name}${f.result_method ? ` · ${f.result_method}` : ''}`
          : EMPTY}
      </p>

      {/* Meta */}
      <p className="mt-0.5 text-xs uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>
        {[f.event_name, formatEventDate(f.event_date), f.weight_class, f.is_title ? 'Title fight' : null]
          .filter(Boolean).join(' · ') || EMPTY}
      </p>

      {/* Model row */}
      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs">
        <span className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>MODEL</span>
        <span className="font-mono">
          {f.fighter_a_name} {Math.round(f.win_prob_a * 100)}% / {f.fighter_b_name} {Math.round(f.win_prob_b * 100)}%
        </span>

        {showPills && (
          <>
            <span
              className={`rounded px-1.5 py-0.5 text-xs font-semibold ${
                f.is_correct
                  ? 'bg-[var(--color-success)]/15 text-[var(--color-success-light)] dark:text-[var(--color-success)]'
                  : 'bg-[var(--color-error)]/15 text-[var(--color-error-light)] dark:text-[var(--color-error)]'
              }`}
            >
              {f.is_correct ? '✓ pick' : '✗ pick'} · {(f.pick_prob * 100).toFixed(0)}%
            </span>
            <span className="font-mono text-[var(--color-accent)]">
              {f.conviction_pp.toFixed(0)}pp conv
            </span>
            <span
              className={`rounded px-1.5 py-0.5 text-xs font-mono ${
                inHotZone
                  ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent)]'
                  : 'border border-[var(--color-border)] text-[var(--color-text-muted)]'
              }`}
            >
              {f.edge_pp >= 0 ? '+' : ''}{f.edge_pp.toFixed(1)}pp vs Vegas
            </span>
            <InfoTooltip label="What does pp vs Vegas mean?">
              <strong className="font-semibold text-[var(--color-text-light)] dark:text-[var(--color-text)]">
                pp = percentage points.
              </strong>{' '}
              The gap between the model&apos;s win probability and the probability implied by the
              Vegas line. A positive edge means the model is more confident in this pick than the
              betting market.
            </InfoTooltip>
          </>
        )}
        {!showPills && (
          <span className="text-[var(--color-text-muted)] text-xs">
            {mode === 'fav'
              ? 'Vegas favorite strategy active'
              : mode === 'dog'
              ? 'Vegas underdog strategy active'
              : `Younger fighter: ${f.younger_name ?? EMPTY}${f.age_diff != null ? ` · ${f.age_diff}y gap` : ''}`}
          </span>
        )}
      </div>
    </div>
  )
}
