interface FighterSearchBarProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export default function FighterSearchBar({
  value,
  onChange,
  placeholder = 'Search by fighter name…',
}: FighterSearchBarProps) {
  return (
    <div className="relative">
      <svg
        className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] pointer-events-none"
        aria-hidden="true"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z"
        />
      </svg>
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label="Search fighters"
        className={[
          'w-full rounded-lg border border-[var(--color-border)]',
          'bg-white dark:bg-[var(--color-surface)]',
          'pl-9 pr-4 py-2.5 text-sm',
          'placeholder:text-[var(--color-text-secondary-light)] dark:placeholder:text-[var(--color-text-secondary)]',
          'focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent',
          'transition-shadow',
        ].join(' ')}
      />
    </div>
  )
}
