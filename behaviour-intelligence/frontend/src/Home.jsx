import React from 'react';

const COMPONENTS = [
  {
    name: 'Behaviour Intelligence',
    owner: 'Thanujan',
    text: 'Turns 15-minute load data into daily demand profiles, groups days into demand patterns, flags abnormal days and labels each day as Normal, Low, Peak or Abnormal demand.',
  },
  {
    name: 'Demand Forecasting',
    owner: 'Dewmini',
    text: 'Forecasts upcoming electricity demand from historical load, so planners can see the expected load before it happens.',
  },
  {
    name: 'Explainable AI',
    owner: 'Madushani',
    text: 'Explains model results with LIME: which factors, such as temperature or solar irradiance, pushed demand up or down on a given day.',
  },
  {
    name: 'Adaptive Forecasting',
    owner: 'Janahan',
    text: 'Neural-network forecasting that adapts to changing demand patterns as new data arrives.',
  },
];

const STEPS = [
  { title: 'Collect', text: '15-minute electricity load readings for the grid.' },
  { title: 'Prepare', text: 'Clean the data and build one 96-point demand profile per day.' },
  { title: 'Analyse', text: 'Machine learning finds demand patterns, abnormal days and future demand.' },
  { title: 'Explain & act', text: 'Dashboards, explanations and reports support planning decisions.' },
];

const AUDIENCE = [
  { title: 'Grid planners', text: 'See demand patterns and peak days to plan generation and maintenance.' },
  { title: 'System control engineers', text: 'Spot abnormal demand days early and check what caused them.' },
  { title: 'Energy analysts', text: 'Compare models, download reports and study demand behaviour over time.' },
  { title: 'Researchers', text: 'Inspect how every model was tuned and validated, with full evidence.' },
];

export default function Home({ navigate, authEnabled, user, onLogout }) {
  const go = (to) => (e) => { e.preventDefault(); navigate(to); };
  const canEnter = !authEnabled || !!user;

  return (
    <div className="home">
      <header className="home-nav">
        <div className="home-container home-nav-inner">
          <a href="/" className="home-logo" onClick={go('/')}>
            <span className="home-logo-mark">⚡</span>
            <span>Electricity Demand Intelligence System</span>
          </a>
          <nav className="home-nav-links">
            <a href="#features" className="home-nav-link">Features</a>
            <a href="#how" className="home-nav-link">How it works</a>
            <a href="#who" className="home-nav-link">Who it is for</a>
            {authEnabled && !user && (
              <>
                <a href="/login" className="home-btn home-btn-ghost" onClick={go('/login')}>Log in</a>
                <a href="/signup" className="home-btn home-btn-primary" onClick={go('/signup')}>Sign up</a>
              </>
            )}
            {authEnabled && user && (
              <button className="home-btn home-btn-ghost" onClick={onLogout}>Logout</button>
            )}
          </nav>
        </div>
      </header>

      <section className="home-hero">
        <div className="home-container">
          <p className="home-eyebrow">For Sri Lanka grid planners · CEB engineers · energy analysts</p>
          <h1 className="home-hero-title">Understand, forecast and explain electricity demand.</h1>
          <p className="home-hero-text">
            One system that learns how Sri Lanka's electricity demand behaves day by day, forecasts what comes next,
            and explains why, so planning decisions rest on clear evidence.
          </p>
          <div className="home-hero-actions">
            <a href="/dashboard" className="home-btn home-btn-primary home-btn-lg" onClick={go('/dashboard')}>
              Open dashboard
            </a>
            {authEnabled && !user && (
              <>
                <a href="/login" className="home-btn home-btn-light home-btn-lg" onClick={go('/login')}>Log in</a>
                <a href="/signup" className="home-btn home-btn-outline home-btn-lg" onClick={go('/signup')}>Sign up</a>
              </>
            )}
          </div>
          {user && <p className="home-hero-user">Logged in as {user.name} · {user.role}</p>}
          {!canEnter && <p className="home-hero-note">Log in or create an account to open the dashboard.</p>}
        </div>
      </section>

      <section className="home-section" id="features">
        <div className="home-container">
          <h2 className="home-section-title">What the system does</h2>
          <p className="home-section-sub">Four research components, one dashboard.</p>
          <div className="home-grid home-grid-4">
            {COMPONENTS.map((c) => (
              <article key={c.name} className="home-card">
                <h3 className="home-card-title">{c.name}</h3>
                <p className="home-card-text">{c.text}</p>
                <p className="home-card-owner">Component by {c.owner}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="home-section home-section-alt" id="how">
        <div className="home-container">
          <h2 className="home-section-title">How it works</h2>
          <ol className="home-steps">
            {STEPS.map((s, i) => (
              <li key={s.title} className="home-step">
                <span className="home-step-num">{i + 1}</span>
                <h3 className="home-step-title">{s.title}</h3>
                <p className="home-step-text">{s.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="home-section" id="who">
        <div className="home-container">
          <h2 className="home-section-title">Who it is for</h2>
          <div className="home-grid home-grid-4">
            {AUDIENCE.map((a) => (
              <article key={a.title} className="home-card home-card-plain">
                <h3 className="home-card-title">{a.title}</h3>
                <p className="home-card-text">{a.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <footer className="home-footer">
        <div className="home-container home-footer-inner">
          <div>
            <p className="home-footer-title">Electricity Demand Intelligence System</p>
            <p>SLIIT research project 2026 · R26-IT-010</p>
          </div>
          <div className="home-footer-team">
            <p className="home-footer-label">Team</p>
            <p>Thanujan · Dewmini · Madushani · Janahan</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
