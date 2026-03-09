export default function AboutPage() {
  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-3xl font-bold">About</h1>

      <div className="space-y-4 text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] leading-relaxed">
        <p>
          Hi, I'm Kabe.
        </p>
        <p>
          This project scrapes UFC fight data directly from UFCStats.com — no third-party APIs.
          The data covers every UFC event since 1994, updated weekly after each event.
        </p>
        <p>
          Machine learning models (XGBoost, Random Forest) trained on historical fight data generate
          the predictions. Each upcoming card shows win probability, method prediction (KO/TKO,
          Submission, Decision), and the key stats driving each pick.
        </p>
        <p>
          Built with FastAPI, React, and PostgreSQL (Supabase), hosted on Render and Vercel.
        </p>
        <p>
          Built for fun and to sharpen data science and engineering skills. Open to feedback.
        </p>
      </div>
    </div>
  )
}
