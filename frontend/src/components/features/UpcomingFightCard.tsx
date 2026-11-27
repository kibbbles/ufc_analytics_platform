import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { UpcomingFight } from '@t/api'
import { Badge } from '@components/common'
import { EMPTY } from '@utils/format'

/** The live method pick's record and its always-Decision baseline. */
export interface MethodRecord {
  total: number
  correct: number
  decisions: number
}

interface Props {
  fight: UpcomingFight
  methodRecord: MethodRecord | null
}

function pct(value: number | null): string {
  if (value == null) return EMPTY
  return `${(value * 100).toFixed(1)}%`
}

function fmtOdds(o: number | null): string {
  if (o == null) return EMPTY
  return o > 0 ? `+${o}` : `${o}`
}

/** Keeps the Vegas label inside the bar: anchored left near 0%, right near 100%. */
function labelShift(p: number): string {
  if (p > 0.85) return '-translate-x-full'
  if (p < 0.15) return 'translate-x-0'
  return '-translate-x-1/2'
}

const PRIMARY_TEXT = 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
const SECONDARY_TEXT = 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]'
const MUTED_TEXT = 'text-[var(--color-text-muted)]'
const ACCENT_TEXT = 'text-[var(--color-accent-light)] dark:text-[var(--color-accent)]'

export function MethodRecordLine({ record }: { record: MethodRecord }) {
  return (
    <>
      Method picks so far:{' '}
      <span className="font-mono tabular-nums">{pct(record.correct / record.total)}</span> right (
      <span className="font-mono tabular-nums">
        {record.correct} of {record.total}
      </span>{' '}
      live fights) vs <span className="font-mono tabular-nums">{pct(record.decisions / record.total)}</span> for
      always guessing Decision.
    </>
  )
}

export default function UpcomingFightCard({ fight, methodRecord }: Props) {
  const [open, setOpen] = useState(false)
  const { fighter_a_name, fighter_b_name, weight_class, is_title_fight, is_interim_title,
          prediction, implied_prob_a, odds_a, odds_b } = fight

  const probA = prediction?.win_prob_a ?? null
  const probB = prediction?.win_prob_b ?? null
  const hasPrediction = probA != null && probB != null
  const aWins = hasPrediction && probA >= probB
  const confidence = hasPrediction ? (Math.max(probA, probB) - 0.5) * 2 : null
  const hasLine = implied_prob_a != null
  const hasOdds = odds_a != null && odds_b != null

  // Each method stays on one line; a narrow screen wraps between them, not inside one.
  const methodParts = hasPrediction
    ? [`KO/TKO ${pct(prediction!.method_ko_tko)}`, `Sub ${pct(prediction!.method_sub)}`, `Dec ${pct(prediction!.method_dec)}`]
    : [EMPTY]
  const methodText = (
    <span className="inline-flex flex-wrap gap-x-1.5">
      {methodParts.map((part, i) => (
        <span key={part} className="whitespace-nowrap">
          {i > 0 && <span aria-hidden="true">· </span>}
          {part}
        </span>
      ))}
    </span>
  )

  const detailsId = `fight-details-${fight.id}`

  return (
    // On sm+ the whole row is the link (the Link's ::after stretches over it);
    // on phones the row holds a details toggle, so only the names and the
    // "Full breakdown" link navigate.
    <div className="border-t border-[var(--color-border-light)] dark:border-[var(--color-border)] px-1 pt-4 pb-1 sm:relative sm:pb-4 sm:transition-colors sm:hover:bg-[var(--color-border)]/20 sm:active:bg-[var(--color-border)]/30">
      {/* Weight class + title badge */}
      <div className="mb-2 flex items-center gap-2">
        {is_title_fight && !is_interim_title && <Badge variant="warning">Title</Badge>}
        {is_interim_title && <Badge variant="warning">Interim</Badge>}
        <span className={`text-xs ${MUTED_TEXT}`}>{weight_class ?? EMPTY}</span>
      </div>

      {/* Names + win probabilities. Both names stay full strength; the pick is shown by weight. */}
      <Link
        to={`/upcoming/fights/${fight.id}`}
        className={`grid grid-cols-2 gap-3 ${PRIMARY_TEXT} sm:flex sm:items-baseline sm:justify-between sm:gap-4 sm:after:absolute sm:after:inset-0 sm:after:content-['']`}
      >
        <span className="flex min-w-0 flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-3">
          <span className={`truncate text-[15px] sm:text-base ${aWins ? 'font-semibold' : 'font-normal'}`}>
            {fighter_a_name ?? EMPTY}
          </span>
          <span className="flex items-baseline gap-2">
            <span className={`font-mono text-[15px] tabular-nums sm:text-base ${aWins ? 'font-semibold' : 'font-normal'}`}>
              {pct(probA)}
            </span>
            {hasOdds && (
              <span className={`font-mono text-xs tabular-nums sm:hidden ${SECONDARY_TEXT}`}>{fmtOdds(odds_a)}</span>
            )}
          </span>
        </span>
        <span className="flex min-w-0 flex-col items-end gap-0.5 text-right sm:flex-row-reverse sm:items-baseline sm:gap-3">
          <span className={`truncate text-[15px] sm:text-base ${hasPrediction && !aWins ? 'font-semibold' : 'font-normal'}`}>
            {fighter_b_name ?? EMPTY}
          </span>
          <span className="flex items-baseline gap-2">
            {hasOdds && (
              <span className={`font-mono text-xs tabular-nums sm:hidden ${SECONDARY_TEXT}`}>{fmtOdds(odds_b)}</span>
            )}
            <span className={`font-mono text-[15px] tabular-nums sm:text-base ${hasPrediction && !aWins ? 'font-semibold' : 'font-normal'}`}>
              {pct(probB)}
            </span>
          </span>
        </span>
      </Link>

      {/* Probability bar with the Vegas tick */}
      {hasPrediction ? (
        <div
          className={`pointer-events-none relative mt-3 flex h-2.5 ${hasLine ? 'mb-7' : 'mb-2'}`}
          role="img"
          aria-label={`Model: ${pct(probA)} ${fighter_a_name ?? ''}, ${pct(probB)} ${fighter_b_name ?? ''}${hasLine ? `. Vegas: ${pct(implied_prob_a)} ${fighter_a_name ?? ''}` : ''}`}
        >
          <span
            className="rounded-l-[3px] bg-[var(--color-prob-a-light)] dark:bg-[var(--color-prob-a)]"
            style={{ width: `${probA * 100}%` }}
          />
          <span className="ml-0.5 flex-1 rounded-r-[3px] bg-[var(--color-prob-b-light)] dark:bg-[var(--color-prob-b)]" />
          {hasLine && (
            <>
              <span
                className="absolute -top-1 -bottom-1 border-l-2 border-[var(--color-accent-light)] dark:border-[var(--color-accent)]"
                style={{ left: `${implied_prob_a * 100}%` }}
              />
              <span
                className={`absolute top-4 whitespace-nowrap text-xs ${ACCENT_TEXT} ${labelShift(implied_prob_a)}`}
                style={{ left: `${implied_prob_a * 100}%` }}
              >
                Vegas <span className="font-mono tabular-nums">{pct(implied_prob_a)}</span>
              </span>
            </>
          )}
        </div>
      ) : (
        <p className={`mt-2 text-xs ${MUTED_TEXT}`}>No prediction for this bout yet.</p>
      )}

      {/* sm+: method, conviction and odds centred under the bar */}
      <div className={`hidden flex-wrap justify-center gap-x-8 gap-y-1 text-[13px] ${hasPrediction ? 'sm:flex' : ''} ${SECONDARY_TEXT}`}>
        <span>
          Method <span className={`font-mono tabular-nums ${PRIMARY_TEXT}`}>{methodText}</span>
        </span>
        <span>
          Conviction <span className={`font-mono tabular-nums ${PRIMARY_TEXT}`}>{pct(confidence)}</span>
        </span>
        <span>
          Odds{' '}
          <span className={`font-mono tabular-nums ${PRIMARY_TEXT}`}>
            {hasOdds ? `${fmtOdds(odds_a)} / ${fmtOdds(odds_b)}` : 'no line'}
          </span>
        </span>
      </div>

      {/* Phone: details on demand */}
      <div className="flex items-center justify-between sm:hidden">
        {hasPrediction ? (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            aria-controls={detailsId}
            className={`-ml-1 flex min-h-11 items-center gap-1.5 rounded px-1 text-[13px] ${SECONDARY_TEXT} active:bg-[var(--color-border)]/30`}
          >
            Method &amp; conviction
            <svg
              className={`h-4 w-4 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        ) : (
          <span />
        )}
        <Link
          to={`/upcoming/fights/${fight.id}`}
          className={`-mr-1 flex min-h-11 items-center rounded px-1 text-[13px] ${SECONDARY_TEXT} active:bg-[var(--color-border)]/30`}
        >
          Full breakdown
        </Link>
      </div>
      {open && hasPrediction && (
        <div id={detailsId} className={`grid grid-cols-[92px_minmax(0,1fr)] gap-y-1.5 pb-3 text-[13px] sm:hidden ${SECONDARY_TEXT}`}>
          <span>Method</span>
          <span className={`font-mono tabular-nums ${PRIMARY_TEXT}`}>{methodText}</span>
          <span>Conviction</span>
          <span className={`font-mono tabular-nums ${PRIMARY_TEXT}`}>{pct(confidence)}</span>
          {methodRecord && methodRecord.total > 0 && (
            <span className={`col-span-2 pt-1 ${MUTED_TEXT}`}>
              <MethodRecordLine record={methodRecord} />
            </span>
          )}
        </div>
      )}
    </div>
  )
}
