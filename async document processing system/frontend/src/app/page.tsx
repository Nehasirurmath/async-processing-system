import Link from "next/link";

export default function HomePage() {
  return (
    <main className="landing-page">
      <section className="hero-card">
        <p className="eyebrow"> Data Operations</p>
        <h1>Async CSV Profiling Workflow System</h1>
        <p className="hero-copy">
          Upload client CSV files, trigger background profiling, and review
          quality, PII, correlation, and predictive power score insights from a
          single workspace.
        </p>

        <div className="hero-actions">
          <Link className="primary-button" href="/workspace">
            Get Started
          </Link>
          <span className="hero-note">
            Celery workers, Redis progress updates, JSON and CSV exports
          </span>
        </div>
      </section>
    </main>
  );
}
