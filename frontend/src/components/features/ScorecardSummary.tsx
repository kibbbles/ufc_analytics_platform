import type { PastPredictionSummary } from '@t/api'
import type { ScorecardModalMode } from './ScorecardModal'

interface Props {
  summary: PastPredictionSummary
  onOpen: (mode: ScorecardModalMode) => void
}

function formatPct(v: number): string {
  return (v * 100).toFixed(1) + '%'
}

const PRIMARY_TEXT = 'text-[var(--color-text-primary-light)] dark:text-[var(--color-text-primary)]'
const SECONDARY_TEXT = 'text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]'
const MUTED_TEXT = 'text-[var(--color-text-muted)]'
const CARD =
  'rounded-lg border border-[var(--color-border-light)] bg-[var(--color-surface-light)] dark:border-[var(--color-border)] dark:bg-[var(--color-surface)]'
const LINK_BUTTON =
  'underline decoration-dotted underline-offset-2 hover:text-[var(--color-primary)] active:text-[var(--color-primary)]'
const MONO = 'font-mono tabular-nums'

function BaselineRow({ label, value, correct, total, barClass }: {
  label: string
  value: number
  correct: number
  total: number
  barClass: string
}) {
  return (
    // Phones: label and value on one line, the bar full width under them.
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 sm:grid-cols-[240px_minmax(0,1fr)_104px]">
      <span className={`text-sm ${PRIMARY_TEXT}`}>{label}</span>
      <div className="relative col-span-2 row-start-2 h-6 rounded-[3px] bg-[var(--color-surface-high-light)] dark:bg-[var(--color-surface-high)] sm:col-span-1 sm:col-start-2 sm:row-start-1">
        <div className={`absolute inset-y-0 left-0 rounded-[3px] ${barClass}`} style={{ width: `${value * 100}%` }} />
        <div className="absolute -top-1.5 -bottom-1.5 left-1/2 border-l border-dashed border-[var(--color-text-muted)]" />
      </div>
      <span className="flex flex-col items-end gap-0.5 sm:col-start-3 sm:row-start-1">
        <span className={`${MONO} text-[15px] ${PRIMARY_TEXT}`}>{formatPct(value)}</span>
        <span className={`${MONO} text-xs ${MUTED_TEXT}`}>
          {correct} of {total}
        </span>
      </span>
    </div>
  )
}

export default function ScorecardSummary({ summary: s, onOpen }: Props) {
  const hasBaseline = s.baseline_sample > 0
  const modelVsVegas = s.baseline_model_accuracy - s.baseline_vegas_accuracy
  const headline =
    modelVsVegas > 0
      ? 'The model has beaten simply picking the Vegas favorite.'
      : modelVsVegas < 0
        ? 'The model has not beaten simply picking the Vegas favorite.'
        : 'The model has only matched simply picking the Vegas favorite.'
  const noOddsCount = s.pre_fight_total - s.baseline_sample
  const legacyCorrect = s.pre_fight_correct - s.pre_fight_corrected_correct

  return (
    <div className="mb-4 flex flex-col gap-5">
      {hasBaseline && (
        <div className="flex flex-col gap-2">
          <p className={`text-xl font-semibold leading-snug sm:text-[26px] sm:leading-tight ${PRIMARY_TEXT}`}>{headline}</p>
          <p className={`max-w-[820px] text-[15px] ${SECONDARY_TEXT}`}>
            On the {s.baseline_sample} live fights that had betting odds, always taking the favorite was right{' '}
            {modelVsVegas < 0 ? 'more often' : modelVsVegas > 0 ? 'less often' : 'just as often'}.
            {s.baseline_disagree_accuracy != null && (
              <>
                {' '}When the model disagreed with Vegas ({s.baseline_disagree_count} fights), it was right{' '}
                <span className={MONO}>{formatPct(s.baseline_disagree_accuracy)}</span> of the time.
              </>
            )}
          </p>
        </div>
      )}

      {hasBaseline && (
        <figure className={`${CARD} m-0 flex flex-col gap-5 px-4 py-5 sm:px-7 sm:py-6`}>
          <figcaption className={`text-[13px] ${MUTED_TEXT}`}>
            Share of fights picked correctly, same {s.baseline_sample} live fights with odds
          </figcaption>
          <BaselineRow
            label="Always pick the Vegas favorite"
            value={s.baseline_vegas_accuracy}
            correct={s.baseline_vegas_correct}
            total={s.baseline_sample}
            barClass="bg-[var(--color-text-secondary-light)] dark:bg-[var(--color-text-secondary)]"
          />
          <BaselineRow
            label="Kabe's Maybes model"
            value={s.baseline_model_accuracy}
            correct={s.baseline_model_correct}
            total={s.baseline_sample}
            barClass="bg-[var(--color-primary)]"
          />
          <div className="-mt-3 grid grid-cols-1 sm:grid-cols-[240px_minmax(0,1fr)_104px] sm:gap-x-4">
            <span className={`text-center text-xs sm:col-start-2 ${MUTED_TEXT}`}>50% coin flip</span>
          </div>
        </figure>
      )}

      {s.pre_fight_total > 0 ? (
        <button
          type="button"
          onClick={() => onOpen('pre_fight')}
          className={`${CARD} flex flex-wrap items-baseline gap-x-5 gap-y-1.5 px-5 py-4 text-left transition-colors hover:border-[var(--color-primary)]/50 active:border-[var(--color-primary)]/70`}
        >
          <span className={`text-[13px] ${MUTED_TEXT}`}>Live track record, all fights</span>
          <span className={`${MONO} text-xl font-semibold ${PRIMARY_TEXT}`}>{formatPct(s.pre_fight_accuracy)}</span>
          <span className={`${MONO} text-[13px] ${SECONDARY_TEXT}`}>
            {s.pre_fight_correct} of {s.pre_fight_total} fights
          </span>
          {hasBaseline && noOddsCount > 0 && (
            <span className={`basis-full text-[13px] ${MUTED_TEXT}`}>
              Includes the {noOddsCount} live {noOddsCount === 1 ? 'fight' : 'fights'} that had no betting odds, which
              is why it differs from the {formatPct(s.baseline_model_accuracy)} above.
            </span>
          )}
        </button>
      ) : (
        <div className={`${CARD} border-dashed px-5 py-4 text-center text-[13px] ${MUTED_TEXT}`}>
          The live track record accumulates over time.
        </div>
      )}

      <details className="group border-t border-[var(--color-border-light)] pt-2 dark:border-[var(--color-border)]">
        <summary className={`flex min-h-11 cursor-pointer list-none items-center gap-2 text-sm font-medium ${PRIMARY_TEXT} [&::-webkit-details-marker]:hidden`}>
          How this is measured
          <svg
            className="h-4 w-4 transition-transform duration-200 group-open:rotate-180"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </summary>
        <div className={`flex max-w-[860px] flex-col gap-2.5 pb-2 text-sm leading-relaxed ${SECONDARY_TEXT}`}>
          <p>
            The live track record is the model's real predictions, frozen once each fight starts and never rewritten,
            so it has no look-ahead.
          </p>
          {s.pre_fight_corrected_total > 0 && (
            <p>
              In July 2026 two model inputs were fixed: the win/loss streak, and the win-rate difference, which had been
              silently filled with the population average. Predictions made since then are right{' '}
              <span className={MONO}>{formatPct(s.pre_fight_corrected_accuracy)}</span> of the time (
              <span className={MONO}>
                {s.pre_fight_corrected_correct} of {s.pre_fight_corrected_total}
              </span>
              )
              {s.pre_fight_legacy_total > 0 && (
                <>
                  , against <span className={MONO}>{formatPct(legacyCorrect / s.pre_fight_legacy_total)}</span> (
                  <span className={MONO}>
                    {legacyCorrect} of {s.pre_fight_legacy_total}
                  </span>
                  ) before. The earlier predictions are kept unchanged
                </>
              )}
              .
            </p>
          )}
          {s.backtest_total > 0 && (
            <p>
              Run over {s.backtest_total} past fights after the fact, the current model scores{' '}
              <span className={MONO}>{formatPct(s.backtest_accuracy)}</span> (
              <span className={MONO}>
                {s.backtest_correct} of {s.backtest_total}
              </span>
              ). Its features were rebuilt after those fights happened, so it benefits from hindsight and is not a live
              record.{' '}
              <button type="button" onClick={() => onOpen('backtest')} className={LINK_BUTTON}>
                See the backtest
              </button>
              .
            </p>
          )}
          <p>
            {s.model_name ? `${s.model_name} model` : 'A model'} using{' '}
            {s.n_features > 0 ? `${s.n_features} ` : ''}features including physical differentials, career striking and
            grappling metrics, and recent fight history. It is pinned, chosen for best calibration from logistic
            regression, random forest, and gradient boosting rather than re-selected each retrain, which only added
            noise among three statistically tied models.
            {s.test_ece != null && (
              <>
                {' '}Expected calibration error on held-out test data:{' '}
                <span className={MONO}>{formatPct(s.test_ece)}</span>.
              </>
            )}{' '}
            <button type="button" onClick={() => onOpen('pre_fight')} className={LINK_BUTTON}>
              See calibration
            </button>
            .
          </p>
          <p>
            Conviction measures how far a prediction is from a coin flip, scaled to 0-100%. A 60/40 prediction is 20%
            conviction, 75/25 is 50%, and 85/15 is 70%. It is not a statistical confidence interval; it reflects how
            decisive the model is on a matchup.
          </p>
          <p>
            UFC 329 (2026-07-11) has no live prediction. The archive workflow was down after a credential failure, and a
            later recompute overwrote the snapshot before it could be frozen. Its results are included; its prediction
            is not.
          </p>
        </div>
      </details>
    </div>
  )
}
