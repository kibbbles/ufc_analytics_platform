import { Link } from 'react-router-dom'

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">UFC Analytics</h1>
        <p className="mt-2 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
          ML-powered fight predictions and historical analysis
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { title: 'Upcoming Card', desc: 'Pre-computed predictions for this Saturday\'s event', to: '/upcoming' },
          { title: 'Fight Predictor', desc: 'Win probability + method breakdown for any matchup', to: '/predictions' },
          { title: 'Fighter Lookup', desc: 'Search any fighter — record, stats, fight history', to: '/fighters' },
        ].map(card => (
          <Link
            key={card.to}
            to={card.to}
            className="block p-5 rounded-lg border border-[var(--color-border-light)] dark:border-[var(--color-border)] bg-[var(--color-surface-light)] dark:bg-[var(--color-surface)] hover:border-[var(--color-primary)] transition-colors"
          >
            <h2 className="font-semibold">{card.title}</h2>
            <p className="mt-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">{card.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
