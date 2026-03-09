export default function HomePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Fight predictions, by the numbers</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { title: 'Fight Predictor', desc: 'Win probability + method breakdown for any matchup', href: '/predictions' },
          { title: 'Upcoming Card', desc: 'Pre-computed predictions for this Saturday\'s event', href: '/upcoming' },
          { title: 'Fighter Lookup', desc: 'Search any fighter — record, stats, fight history', href: '/fighters' },
        ].map(card => (
          <a
            key={card.href}
            href={card.href}
            className="block p-5 rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-surface-light)] dark:bg-[var(--color-surface)] hover:border-[var(--color-primary)] transition-colors"
          >
            <h2 className="font-semibold">{card.title}</h2>
            <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">{card.desc}</p>
          </a>
        ))}
      </div>
    </div>
  )
}
