import type { UpcomingFight } from '@t/api'

interface Props {
  fight: UpcomingFight
}

function pct(value: number | null): string {
  if (value == null) return '—'
  return `${Math.round(value * 100)}%`
}

function topMethod(pred: NonNullable<UpcomingFight['prediction']>): string {
  const methods = [
    { label: 'KO/TKO', value: pred.method_ko_tko },
    { label: 'Sub', value: pred.method_sub },
    { label: 'Dec', value: pred.method_dec },
  ]
  const top = methods.reduce((a, b) =>
    (a.value ?? 0) > (b.value ?? 0) ? a : b,
  )
  return `${top.label} ${pct(top.value)}`
}

export default function UpcomingFightRow({ fight }: Props) {
  const { fighter_a_name, fighter_b_name, weight_class, is_title_fight, prediction } = fight

  const hasPrediction =
    prediction !== null &&
    prediction.win_prob_a !== null &&
    prediction.win_prob_b !== null

  const aWins = hasPrediction && prediction.win_prob_a! >= prediction.win_prob_b!

  return (
    <div className="border-t border-[var(--color-border)] py-3 px-1">
      {/* Weight class + title badge */}
      <div className="mb-1.5 flex items-center gap-2">
        {weight_class && (
          <span className="text-xs text-[var(--color-text-muted)] dark:text-[var(--color-text-muted)]">
            {weight_class}
          </span>
        )}
        {is_title_fight && (
          <span className="rounded-sm bg-[var(--color-primary)] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
            Title
          </span>
        )}
      </div>

      {/* Fighter names + probabilities */}
      <div className="flex items-center justify-between gap-2">
        {/* Fighter A */}
        <div className="flex min-w-0 flex-1 flex-col">
          <span
            className={`truncate text-sm font-medium ${
              hasPrediction && aWins
                ? 'text-[var(--color-primary)]'
                : 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
            }`}
          >
            {fighter_a_name ?? '—'}
          </span>
          {hasPrediction && (
            <span
              className={`font-mono text-lg font-bold tabular-nums ${
                aWins
                  ? 'text-[var(--color-primary)]'
                  : 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]'
              }`}
            >
              {pct(prediction.win_prob_a)}
            </span>
          )}
        </div>

        {/* Centre separator */}
        <span className="shrink-0 text-xs text-[var(--color-text-muted)]">vs</span>

        {/* Fighter B */}
        <div className="flex min-w-0 flex-1 flex-col items-end">
          <span
            className={`truncate text-sm font-medium ${
              hasPrediction && !aWins
                ? 'text-[var(--color-primary)]'
                : 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
            }`}
          >
            {fighter_b_name ?? '—'}
          </span>
          {hasPrediction && (
            <span
              className={`font-mono text-lg font-bold tabular-nums ${
                !aWins
                  ? 'text-[var(--color-primary)]'
                  : 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]'
              }`}
            >
              {pct(prediction.win_prob_b)}
            </span>
          )}
        </div>
      </div>

      {/* Method breakdown or no-prediction state */}
      {hasPrediction ? (
        <div className="mt-1.5 flex gap-3 font-mono text-xs tabular-nums text-[var(--color-text-muted)]">
          <span>KO/TKO {pct(prediction.method_ko_tko)}</span>
          <span>Sub {pct(prediction.method_sub)}</span>
          <span>Dec {pct(prediction.method_dec)}</span>
          <span className="ml-auto font-sans font-medium text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
            → {topMethod(prediction)}
          </span>
        </div>
      ) : (
        <p className="mt-1 text-xs text-[var(--color-text-muted)]">No prediction available</p>
      )}
    </div>
  )
}
