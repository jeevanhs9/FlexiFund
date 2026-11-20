import { useEffect, useMemo, useState } from "react";

const money = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function formatMoney(value) {
  return money.format(Number(value));
}

function formatWeek(value, options = { day: "numeric", month: "short" }) {
  return new Intl.DateTimeFormat("en-IN", options).format(new Date(`${value}T00:00:00`));
}

function BrandMark() {
  return (
    <div className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 36 36" role="presentation">
        <path d="M7 25.5 14.2 9l5.2 11.2 3.2-6.6L29 25.5" />
        <path d="M8 28.5h20" />
      </svg>
    </div>
  );
}

function Icon({ name }) {
  const paths = {
    overview: <><rect x="3.5" y="3.5" width="8" height="8" rx="2" /><rect x="14.5" y="3.5" width="8" height="5" rx="2" /><rect x="14.5" y="11.5" width="8" height="8" rx="2" /><rect x="3.5" y="14.5" width="8" height="5" rx="2" /></>,
    income: <><path d="M4 17V7" /><path d="m4 13 5-5 4 3 7-7" /><path d="M15 4h5v5" /></>,
    costs: <><path d="M5 5h14v14H5z" /><path d="M8 9h8M8 13h5" /><path d="m15.5 17.5 2 2 4-4" /></>,
    arrow: <><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M7 3v4M17 3v4M3 10h18" /></>,
    refresh: <><path d="M20 7v5h-5" /><path d="M19 12a7 7 0 1 1-2-5l3 5" /></>,
  };

  return (
    <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

function Sidebar({ active, onNavigate }) {
  return (
    <aside className="sidebar">
      <a className="brand" href="#overview" onClick={() => onNavigate("overview")}>
        <BrandMark />
        <span>flexifund<span className="brand-period">.</span></span>
      </a>

      <div className="sidebar-label">WORKSPACE</div>
      <nav className="side-nav" aria-label="Main navigation">
        <a className={active === "overview" ? "nav-item active" : "nav-item"} href="#overview" onClick={() => onNavigate("overview")}>
          <Icon name="overview" /><span>Overview</span>
        </a>
        <a className={active === "income" ? "nav-item active" : "nav-item"} href="#income" onClick={() => onNavigate("income")}>
          <Icon name="income" /><span>Income history</span>
        </a>
        <a className={active === "costs" ? "nav-item active" : "nav-item"} href="#costs" onClick={() => onNavigate("costs")}>
          <Icon name="costs" /><span>Work costs</span>
        </a>
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-orbit" aria-hidden="true"><span>F</span></div>
        <p className="sidebar-bottom-title">A steadier view of money</p>
        <p className="sidebar-bottom-copy">Built for work that doesn’t pay the same every week.</p>
        <div className="sidebar-footer">FLEXIFUND · DEMO 01</div>
      </div>
    </aside>
  );
}

function MetricCard({ label, value, detail, icon, tone = "green" }) {
  return (
    <article className={`metric-card tone-${tone}`}>
      <div className="metric-topline">
        <span className="metric-label">{label}</span>
        <span className="metric-icon"><Icon name={icon} /></span>
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-detail">{detail}</div>
    </article>
  );
}

function IncomeChart({ history }) {
  const chart = useMemo(() => {
    if (!history.length) return null;
    const width = 740;
    const height = 250;
    const pad = { top: 18, right: 12, bottom: 35, left: 12 };
    const values = history.map((item) => Number(item.gross_income));
    const essentials = history.map((item) => Number(item.essential_expenses));
    const maxValue = Math.ceil(Math.max(...values, ...essentials) / 2000) * 2000;
    const plotWidth = width - pad.left - pad.right;
    const plotHeight = height - pad.top - pad.bottom;
    const getX = (index) => pad.left + (history.length === 1 ? plotWidth / 2 : (index / (history.length - 1)) * plotWidth);
    const getY = (value) => pad.top + (1 - value / maxValue) * plotHeight;
    const lineFor = (items) => items.map((item, index) => `${index ? "L" : "M"} ${getX(index).toFixed(2)} ${getY(Number(item)).toFixed(2)}`).join(" ");
    const grossLine = lineFor(history.map((item) => item.gross_income));
    const essentialsLine = lineFor(history.map((item) => item.essential_expenses));
    const first = history[0];
    const middle = history[Math.floor((history.length - 1) / 2)];
    const last = history[history.length - 1];
    const gridValues = [0, maxValue / 2, maxValue];

    return { width, height, pad, maxValue, plotHeight, getX, getY, grossLine, essentialsLine, first, middle, last, gridValues };
  }, [history]);

  if (!chart) return <div className="chart-empty">Weekly history will appear here after the demo data is seeded.</div>;

  return (
    <div className="chart-wrap">
      <div className="chart-legend">
        <span><i className="legend-dot income-dot" />Gross income</span>
        <span><i className="legend-dot expense-dot" />Household essentials</span>
      </div>
      <svg className="income-chart" viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Weekly gross income and household essentials across the synthetic history">
        {chart.gridValues.map((value) => {
          const y = chart.getY(value);
          return <g key={value}><line x1={chart.pad.left} x2={chart.width - chart.pad.right} y1={y} y2={y} className="chart-grid" /><text x={chart.pad.left} y={y - 6} className="chart-axis-label">{formatMoney(value)}</text></g>;
        })}
        <path d={chart.grossLine} className="chart-line gross-line" />
        <path d={chart.essentialsLine} className="chart-line essentials-line" />
        {history.map((item, index) => (
          <circle key={item.id} cx={chart.getX(index)} cy={chart.getY(Number(item.gross_income))} r="3" className="chart-point" />
        ))}
        <text x={chart.pad.left} y={chart.height - 8} className="chart-axis-label">{formatWeek(chart.first.date)}</text>
        <text x={chart.width / 2} y={chart.height - 8} textAnchor="middle" className="chart-axis-label">{formatWeek(chart.middle.date)}</text>
        <text x={chart.width - chart.pad.right} y={chart.height - 8} textAnchor="end" className="chart-axis-label">{formatWeek(chart.last.date)}</text>
      </svg>
      <p className="chart-caption">Weekly values from Ravi’s synthetic history. The lines show separate categories; no surplus or risk score is calculated.</p>
    </div>
  );
}

function EmptyState({ error, onRetry }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon"><Icon name="refresh" /></div>
      <h2>{error ? "Demo data isn’t connected" : "Loading synthetic demo data"}</h2>
      <p>{error || "Connecting to the FlexiFund API and reading Ravi’s weekly history."}</p>
      {error && <button className="retry-button" onClick={onRetry}><Icon name="refresh" /> Try again</button>}
      {error && <div className="setup-hint">Start PostgreSQL, run <code>python -m app.seed</code>, then start the backend.</div>}
    </div>
  );
}

export default function App() {
  const [active, setActive] = useState("overview");
  const [demo, setDemo] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadDemo() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/demo/rider");
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not load the demo profile.");
      setDemo(payload);
    } catch {
      setDemo(null);
      setError("The API or demo database is unavailable. Start the backend and seed Ravi’s data, then try again.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadDemo(); }, []);

  const rider = demo?.rider;
  const history = demo?.history ?? [];
  const latest = history.at(-1);
  const featuredPatterns = [
    history.find((item) => /festival demand spike/i.test(item.notes ?? "")),
    history.find((item) => /lean period begins/i.test(item.notes ?? "")),
    history.find((item) => /maintenance event/i.test(item.notes ?? "")),
  ].filter(Boolean);

  return (
    <div className="app-shell">
      <Sidebar active={active} onNavigate={setActive} />
      <main className="main-content" id="overview">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><span className="breadcrumb-slash">/</span><strong>Overview</strong></div>
          <div className="topbar-right">
            <div className="api-status"><span className={`status-dot ${error ? "offline" : loading ? "checking" : ""}`} />{error ? "API disconnected" : loading ? "Connecting" : "API connected"}</div>
            <div className="demo-chip"><span className="demo-chip-dot" />SYNTHETIC DEMO</div>
            <button className="avatar" aria-label="Ravi profile">R</button>
          </div>
        </header>

        <div className="page-content">
          <section className="welcome-row">
            <div>
              <div className="eyebrow"><span className="eyebrow-line" />FLEXIFUND · FINANCIAL SAFETY</div>
              <h1>Your money, in a <span>clearer light.</span></h1>
              <p className="page-subtitle">A weekly view built for income that changes.</p>
            </div>
            <div className="period-pill"><Icon name="calendar" /> 32-week history</div>
          </section>

          <section className="profile-banner" aria-label="Synthetic profile notice">
            <div className="profile-avatar">{rider?.name?.[0] ?? "R"}</div>
            <div className="profile-details">
              <div className="profile-name">{rider?.name ?? "Ravi"}<span className="verified-badge" title="Synthetic demo profile">✓</span></div>
              <div className="profile-meta">{rider?.city ?? "Bengaluru"}<span>·</span> Delivery rider<span>·</span> {rider?.platform ?? "Synthetic Delivery Platform"}</div>
            </div>
            <div className="synthetic-stamp"><span>✳</span> Fictional profile<br /><small>For demonstration only</small></div>
          </section>

          {loading || error ? <EmptyState error={error} onRetry={loadDemo} /> : (
            <>
              <section className="metrics-grid" aria-label="Latest week overview">
                <MetricCard label="Gross income" value={formatMoney(latest?.gross_income ?? 0)} detail={`Latest week · ${latest ? formatWeek(latest.date) : "—"}`} icon="income" tone="green" />
                <MetricCard label="Household essentials" value={formatMoney(latest?.essential_expenses ?? 0)} detail="Recorded separately from work costs" icon="costs" tone="lavender" />
                <MetricCard label="Working days" value={`${latest?.working_days ?? 0}`} detail="In the latest recorded week" icon="calendar" tone="sand" />
                <MetricCard label="History records" value={String(history.length)} detail="Weekly synthetic entries" icon="overview" tone="blue" />
              </section>

              <section className="content-grid">
                <article className="panel income-panel" id="income">
                  <div className="panel-heading">
                    <div><div className="panel-kicker">INCOME PATTERN</div><h2>Week by week</h2></div>
                    <div className="panel-range">{history.length ? `${formatWeek(history[0].date)} — ${formatWeek(latest.date)}` : ""}</div>
                  </div>
                  <IncomeChart history={history} />
                </article>

                <article className="panel cost-panel" id="costs">
                  <div className="panel-heading">
                    <div><div className="panel-kicker">LATEST WEEK</div><h2>Work costs</h2></div>
                    <div className="cost-date">{latest ? formatWeek(latest.date) : ""}</div>
                  </div>
                  <div className="cost-list">
                    {[
                      ["Fuel", latest?.fuel_cost, "fuel"],
                      ["Maintenance", latest?.maintenance_cost, "maintenance"],
                      ["Data", latest?.data_cost, "data"],
                      ["Other work costs", latest?.other_work_cost, "other"],
                    ].map(([label, value, key]) => (
                      <div className="cost-row" key={key}>
                        <span className={`cost-marker marker-${key}`} />
                        <span className="cost-name">{label}</span>
                        <span className="cost-value">{formatMoney(value ?? 0)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="separation-note"><span className="note-icon">i</span><span>Household essentials stay separate so work costs are easy to identify.</span></div>
                </article>
              </section>

              <section className="panel patterns-panel">
                <div className="panel-heading patterns-heading">
                  <div><div className="panel-kicker">IN THE HISTORY</div><h2>Weeks worth noticing</h2></div>
                  <span className="synthetic-tag">SYNTHETIC EXAMPLES</span>
                </div>
                <div className="pattern-list">
                  {featuredPatterns.map((item) => {
                    const note = item.notes ?? "Recorded variation";
                    const kind = /festival/i.test(note) ? "festival" : /maintenance event/i.test(note) ? "maintenance" : /lean/i.test(note) ? "lean" : "rain";
                    return (
                      <div className="pattern-row" key={item.id}>
                        <span className={`pattern-icon pattern-${kind}`}>{kind === "festival" ? "✦" : kind === "maintenance" ? "⚙" : kind === "lean" ? "↘" : "☂"}</span>
                        <span className="pattern-copy"><strong>{note}</strong><small>{formatWeek(item.date, { weekday: "short", day: "numeric", month: "short" })} · {item.working_days} working days</small></span>
                        <span className="pattern-income">{formatMoney(item.gross_income)}</span>
                      </div>
                    );
                  })}
                  {mostRecentPatterns.length === 0 && <p className="no-patterns">No highlighted demo weeks in this history.</p>}
                </div>
              </section>

              <section className="journey-strip" aria-label="FlexiFund approach">
                <div className="journey-intro"><span className="journey-spark">✳</span><div><strong>Made for income that moves</strong><small>FlexiFund’s approach</small></div></div>
                <div className="journey-step"><span className="step-number">01</span><div><strong>Predict</strong><small>Understand changing income</small></div></div>
                <span className="journey-arrow">→</span>
                <div className="journey-step"><span className="step-number">02</span><div><strong>Protect</strong><small>Plan for difficult weeks</small></div></div>
                <span className="journey-arrow">→</span>
                <div className="journey-step"><span className="step-number">03</span><div><strong>Prove</strong><small>Show the evidence clearly</small></div></div>
              </section>
              <footer className="page-footer">FlexiFund demo · All financial history shown here is synthetic and not real-world verified.</footer>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
