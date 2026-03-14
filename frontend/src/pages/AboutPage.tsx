export default function AboutPage() {
  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-3xl font-bold">About</h1>

      <div className="space-y-4 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] leading-relaxed">
        <p>
          Hi, I'm Kabe (pronounced kay-bee).
        </p>
        <p>
          This project scrapes UFC fight data directly from UFCStats.com — no third-party APIs.
          The data covers every UFC event since 1994, updated automatically after each event.
        </p>
        <p>
          A Random Forest model trained on historical fight data generates the predictions.
          Features are built from fighter differentials — striking accuracy, takedown rate,
          reach, age, experience, and more. Each upcoming card shows win probability, method
          prediction (KO/TKO, Submission, Decision), and the key stats driving each pick.
        </p>
        <p>
          The model scorecard shows past prediction accuracy. Fights predicted live before
          the event are marked as pre-fight predictions and are frozen — they won't change
          when the model retrains. Older historical fights are retroactive estimates.
        </p>
        <p>
          Built with FastAPI, React, and PostgreSQL (Supabase), hosted on Google Cloud Run
          and Vercel.
        </p>
        <p>
          Built for fun and to sharpen data science and engineering skills. Open to feedback.
        </p>
      </div>
    </div>
  )
}
