import { useNavigate } from 'react-router-dom'
import type { UpcomingFight } from '@t/api'
import { Badge } from '@components/common'

interface Props {
  fight: UpcomingFight
}

function pct(value: number | null): string {
  if (value == null) return '—'
  return `${(value * 100).toFixed(1)}%`
}

type Method = { label: string; value: number | null }

function getMethods(pred: NonNullable<UpcomingFight['prediction']>): Method[] {
  return [
    { label: 'KO/TKO', value: pred.method_ko_tko },
    { label: 'Sub', value: pred.method_sub },
    { label: 'Dec', value: pred.method_dec },
  ]
}

function topMethodLabel(methods: Method[]): string {
  return methods.reduce((a, b) => ((a.value ?? 0) > (b.value ?? 0) ? a : b)).label
}

function fmtOdds(o: number | null): string {
  if (o == null) return '—'
  return o > 0 ? `+${o}` : `${o}`
}

export default function UpcomingFightRow({ fight }: Props) {
  const navigate = useNavigate()
  const { fighter_a_name, fighter_b_name, weight_class, is_title_fight, is_interim_title,
          prediction, implied_prob_a, implied_prob_b, odds_a, odds_b } = fight

  const hasPrediction =
    prediction !== null &&
    prediction.win_prob_a !== null &&
    prediction.win_prob_b !== null

  const aWins = hasPrediction && prediction.win_prob_a! >= prediction.win_prob_b!
  const methods = hasPrediction ? getMethods(prediction!) : []
  const topLabel = hasPrediction ? topMethodLabel(methods) : ''
  const confidence = hasPrediction
    ? (Math.max(prediction!.win_prob_a ?? 0, prediction!.win_prob_b ?? 0) - 0.5) * 2
    : null

  return (
    <div
      className="border-t border-[var(--color-border)] py-3 px-1 cursor-pointer hover:bg-[var(--color-border)]/20 transition-colors rounded-sm"
      onClick={() => navigate(`/upcoming/fights/${fight.id}`)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') navigate(`/upcoming/fights/${fight.id}`) }}
    >
      {/* Weight class + title badge */}
      <div className="mb-1.5 flex items-center justify-center gap-2">
        {is_title_fight && !is_interim_title && <Badge variant="warning">Title</Badge>}
        {is_interim_title && <Badge variant="warning">Interim</Badge>}
        {weight_class && (
          <span className="text-xs text-[var(--color-text-muted)]">
            {weight_class}
          </span>
        )}
      </div>

      {/* Fighter names + probabilities */}
      <div className="flex items-center justify-between gap-2">
        {/* Fighter A */}
        <div className="flex min-w-0 flex-1 flex-col">
          <span
            className={`truncate text-sm ${
              hasPrediction && aWins
                ? 'font-bold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                : hasPrediction
                ? 'font-medium text-[var(--color-text-muted)]'
                : 'font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
            }`}
          >
            {fighter_a_name ?? '—'}
          </span>
          {hasPrediction && (
            <span
              className={`font-mono text-lg tabular-nums ${
                aWins
                  ? 'font-bold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                  : 'font-medium text-[var(--color-text-muted)]'
              }`}
            >
              {pct(prediction!.win_prob_a)}
            </span>
          )}
        </div>

        {/* Centre separator */}
        <span className="shrink-0 text-xs text-[var(--color-text-muted)]">vs</span>

        {/* Fighter B */}
        <div className="flex min-w-0 flex-1 flex-col items-end">
          <span
            className={`truncate text-sm ${
              hasPrediction && !aWins
                ? 'font-bold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                : hasPrediction
                ? 'font-medium text-[var(--color-text-muted)]'
                : 'font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
            }`}
          >
            {fighter_b_name ?? '—'}
          </span>
          {hasPrediction && (
            <span
              className={`font-mono text-lg tabular-nums ${
                !aWins
                  ? 'font-bold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                  : 'font-medium text-[var(--color-text-muted)]'
              }`}
            >
              {pct(prediction!.win_prob_b)}
            </span>
          )}
        </div>
      </div>

      {/* Method breakdown */}
      {hasPrediction ? (
        <>
          <div className="mt-1.5 flex justify-center gap-4 font-mono text-xs tabular-nums">
            {methods.map(({ label, value }) => (
              <span
                key={label}
                className={
                  label === topLabel
                    ? 'font-bold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
                    : 'text-[var(--color-text-muted)] opacity-50'
                }
              >
                {label} {pct(value)}
              </span>
            ))}
          </div>
          {confidence != null && (
            <div className="mt-1 text-center">
              <span className="text-xs text-[var(--color-text-muted)]">conviction </span>
              <span className="font-mono text-xs font-semibold tabular-nums">{pct(confidence)}</span>
            </div>
          )}
          {implied_prob_a != null && implied_prob_b != null && (
            <div className="mt-1 text-center font-mono text-xs tabular-nums text-[var(--color-text-muted)]">
              vegas {pct(implied_prob_a)} / {pct(implied_prob_b)}
              <span className="ml-1 opacity-60">({fmtOdds(odds_a)} / {fmtOdds(odds_b)})</span>
            </div>
          )}
        </>
      ) : (
        <p className="mt-1 text-center text-xs text-[var(--color-text-muted)]">No prediction available</p>
      )}
    </div>
  )
}
