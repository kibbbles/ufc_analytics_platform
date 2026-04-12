// Weight class filter — pill buttons, horizontal scroll on mobile

const WEIGHT_CLASSES = [
  { label: 'All', value: null },
  { label: 'HW', value: 'Heavyweight' },
  { label: 'LHW', value: 'Light Heavyweight' },
  { label: 'MW', value: 'Middleweight' },
  { label: 'WW', value: 'Welterweight' },
  { label: 'LW', value: 'Lightweight' },
  { label: 'FW', value: 'Featherweight' },
  { label: 'BW', value: 'Bantamweight' },
  { label: 'FLW', value: 'Flyweight' },
  { label: "W's SW", value: "Women's Strawweight" },
  { label: "W's FLW", value: "Women's Flyweight" },
  { label: "W's BW", value: "Women's Bantamweight" },
]

interface Props {
  value: string | null
  onChange: (wc: string | null) => void
}

export default function WeightClassFilter({ value, onChange }: Props) {
  return (
    <div className="flex w-full justify-start md:justify-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
      {WEIGHT_CLASSES.map(({ label, value: wc }) => {
        const active = value === wc
        return (
          <button
            key={label}
            onClick={() => onChange(wc)}
            className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              active
                ? 'bg-[var(--color-primary)] text-white'
                : 'border border-[var(--color-border-light)] dark:border-[var(--color-border)] text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:border-[var(--color-primary)]/50'
            }`}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
