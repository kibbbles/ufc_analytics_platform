import type { FighterResponse } from '@t/api'
import { Badge } from '@components/common'
import { inchesToFeet, ageFromDob, formatDate } from '@utils/format'

interface FighterProfileHeaderProps {
  fighter: FighterResponse
}

interface StatItemProps {
  label: string
  value: string | number | null | undefined
}

function StatItem({ label, value }: StatItemProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] uppercase tracking-wide">
        {label}
      </span>
      <span className="text-sm font-medium">{value ?? '—'}</span>
    </div>
  )
}

export default function FighterProfileHeader({ fighter }: FighterProfileHeaderProps) {
  const name = [fighter.first_name, fighter.last_name].filter(Boolean).join(' ') || 'Unknown Fighter'

  const wins = fighter.wins ?? 0
  const losses = fighter.losses ?? 0
  const draws = fighter.draws ?? 0
  const nc = fighter.no_contests ?? 0

  return (
    <div className="space-y-6">
      {/* Name + record */}
      <div>
        <h1 className="text-3xl font-bold">{name}</h1>
        {fighter.nickname && (
          <p className="mt-1 text-lg text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] italic">
            "{fighter.nickname}"
          </p>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Badge variant="success" className="text-sm px-3 py-1">{wins} Wins</Badge>
          <Badge variant="danger" className="text-sm px-3 py-1">{losses} Losses</Badge>
          {draws > 0 && <Badge variant="default" className="text-sm px-3 py-1">{draws} Draws</Badge>}
          {nc > 0 && <Badge variant="default" className="text-sm px-3 py-1">{nc} NC</Badge>}
        </div>
      </div>

      {/* Physical stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] p-5">
        <StatItem
          label="Height"
          value={fighter.height_inches != null ? inchesToFeet(fighter.height_inches) : null}
        />
        <StatItem
          label="Weight"
          value={fighter.weight_lbs != null ? `${fighter.weight_lbs} lbs` : null}
        />
        <StatItem
          label="Reach"
          value={fighter.reach_inches != null ? `${fighter.reach_inches}"` : null}
        />
        <StatItem label="Stance" value={fighter.stance} />
        <StatItem
          label="DOB"
          value={fighter.dob_date ? formatDate(fighter.dob_date) : null}
        />
        <StatItem
          label="Age"
          value={fighter.dob_date ? ageFromDob(fighter.dob_date) : null}
        />
      </div>

      {/* Career averages */}
      {(fighter.slpm != null || fighter.td_avg != null) && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 rounded-lg border border-[var(--color-border)] bg-white dark:bg-[var(--color-surface)] p-5">
          <StatItem label="SLpM" value={fighter.slpm?.toFixed(2)} />
          <StatItem label="Str. Acc." value={fighter.str_acc} />
          <StatItem label="SApM" value={fighter.sapm?.toFixed(2)} />
          <StatItem label="Str. Def." value={fighter.str_def} />
          <StatItem label="TD Avg." value={fighter.td_avg?.toFixed(2)} />
          <StatItem label="TD Acc." value={fighter.td_acc} />
          <StatItem label="TD Def." value={fighter.td_def} />
          <StatItem label="Sub. Avg." value={fighter.sub_avg?.toFixed(2)} />
        </div>
      )}
    </div>
  )
}
