import { Link } from 'react-router-dom'
import type { UpcomingFight } from '@t/api'
import { Badge } from '@components/common'
import { EMPTY } from '@utils/format'

interface Props {
  fight: UpcomingFight
}

function pct(value: number | null): string {
  if (value == null) return EMPTY
  return `${(value * 100).toFixed(1)}%`
}

type Method = { label: string; value: number | null }

function topMethodLabel(methods: Method[]): string {
  return methods.reduce((a, b) => ((a.value ?? 0) > (b.value ?? 0) ? a : b)).label
}

function fmtOdds(o: number | null): string {
  if (o == null) return EMPTY
  return o > 0 ? `+${o}` : `${o}`
}

// Emphasis for a name/prob: bold+primary for the model's pick, muted otherwise.
const PICK = 'font-bold text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
const MUTED = 'font-medium text-[var(--color-text-muted)]'
const PLAIN = 'font-medium text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'

export default function UpcomingFightCard({ fight }: Props) {
  const { fighter_a_name, fighter_b_name, weight_class, is_title_fight, is_interim_title,
          prediction, implied_prob_a, implied_prob_b, odds_a, odds_b } = fight

  const hasPrediction =
    prediction !== null &&
    prediction.win_prob_a !== null &&
    prediction.win_prob_b !== null

  const aWins = hasPrediction && prediction!.win_prob_a! >= prediction!.win_prob_b!
  // Always three method rows; values are `—` when there is no prediction.
  const methods: Method[] = [
    { label: 'KO/TKO', value: prediction?.method_ko_tko ?? null },
    { label: 'Sub', value: prediction?.method_sub ?? null },
    { label: 'Dec', value: prediction?.method_dec ?? null },
  ]
  const topLabel = hasPrediction ? topMethodLabel(methods) : ''
  const confidence = hasPrediction
    ? (Math.max(prediction!.win_prob_a ?? 0, prediction!.win_prob_b ?? 0) - 0.5) * 2
    : null
  const hasLine = implied_prob_a != null && implied_prob_b != null

  return (
    <Link
      to={`/upcoming/fights/${fight.id}`}
      className="block border-t border-[var(--color-border)] py-3 px-1 hover:bg-[var(--color-border)]/20 transition-colors rounded-sm"
    >
      {/* Weight class + title badge */}
      <div className="mb-1.5 flex items-center justify-center gap-2">
        {is_title_fight && !is_interim_title && <Badge variant="warning">Title</Badge>}
        {is_interim_title && <Badge variant="warning">Interim</Badge>}
        <span className="text-xs text-[var(--color-text-muted)]">
          {weight_class ?? EMPTY}
        </span>
      </div>

      {/* Fighter names + probabilities */}
      <div className="flex items-center justify-between gap-2">
        {/* Fighter A */}
        <div className="flex min-w-0 flex-1 flex-col">
          <span className={`truncate text-sm ${hasPrediction ? (aWins ? PICK : MUTED) : PLAIN}`}>
            {fighter_a_name ?? EMPTY}
          </span>
          <span className={`font-mono text-lg tabular-nums ${hasPrediction && aWins ? PICK : MUTED}`}>
            {pct(prediction?.win_prob_a ?? null)}
          </span>
        </div>

        {/* Centre separator */}
        <span className="shrink-0 text-xs text-[var(--color-text-muted)]">vs</span>

        {/* Fighter B */}
        <div className="flex min-w-0 flex-1 flex-col items-end">
          <span className={`truncate text-sm ${hasPrediction ? (!aWins ? PICK : MUTED) : PLAIN}`}>
            {fighter_b_name ?? EMPTY}
          </span>
          <span className={`font-mono text-lg tabular-nums ${hasPrediction && !aWins ? PICK : MUTED}`}>
            {pct(prediction?.win_prob_b ?? null)}
          </span>
        </div>
      </div>

      {/* Method breakdown */}
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

      {/* Conviction */}
      <div className="mt-1 text-center">
        <span className="text-xs text-[var(--color-text-muted)]">conviction </span>
        <span className="font-mono text-xs font-semibold tabular-nums">{pct(confidence)}</span>
      </div>

      {/* Vegas line */}
      <div className="mt-1 text-center font-mono text-xs tabular-nums text-[var(--color-text-muted)]">
        {hasLine ? (
          <>
            vegas {pct(implied_prob_a)} / {pct(implied_prob_b)}
            <span className="ml-1 opacity-60">({fmtOdds(odds_a)} / {fmtOdds(odds_b)})</span>
          </>
        ) : (
          `vegas ${EMPTY} no line`
        )}
      </div>
    </Link>
  )
}
