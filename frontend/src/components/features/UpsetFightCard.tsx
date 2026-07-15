import type { UpsetFightCard as UpsetFightCardData } from '@t/api'
import { formatEventDate, formatOdds, EMPTY } from '@utils/format'

export default function UpsetFightCard({ f }: { f: UpsetFightCardData }) {
  return (
    <div className="relative rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] px-4 py-3 text-sm">
      {/* Upset badge */}
      <div className="absolute top-0 right-0 rounded-bl-lg rounded-tr-lg px-2 py-0.5 text-xs font-semibold bg-[var(--color-error)]/15 text-[var(--color-error-light)] dark:text-[var(--color-error)]">
        Upset
      </div>

      {/* Matchup */}
      <p className="font-semibold pr-14">
        {f.fighter_a_name ?? EMPTY}<span className="text-[var(--color-text-muted)] font-normal"> vs </span>{f.fighter_b_name ?? EMPTY}
      </p>

      {/* Actual result */}
      <p className="mt-0.5 text-[var(--color-warning-light)] dark:text-[var(--color-warning)]">
        {f.winner_name ? `${f.winner_name} wins${f.method ? ` · ${f.method}` : ''}` : EMPTY}
      </p>

      {/* Meta */}
      <p className="mt-0.5 text-xs uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>
        {[f.event_name ?? f.event_id, formatEventDate(f.event_date), f.weight_class]
          .filter(Boolean).join(' · ') || EMPTY}
      </p>

      {/* Model row */}
      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs">
        <span className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]" style={{ letterSpacing: '0.04em' }}>MODEL</span>
        <span className="rounded px-1.5 py-0.5 text-xs font-semibold bg-[var(--color-error)]/15 text-[var(--color-error-light)] dark:text-[var(--color-error)]">
          ✗ {f.model_pick_name ?? EMPTY}
        </span>
        <span className="font-mono text-[var(--color-accent)]">
          {(f.conviction * 100).toFixed(0)}pp conviction
        </span>
        <span className="font-mono text-[var(--color-text-muted)]">
          {f.model_pick_odds != null ? `odds ${formatOdds(f.model_pick_odds)} · loss $100` : 'no line'}
        </span>
      </div>
    </div>
  )
}
