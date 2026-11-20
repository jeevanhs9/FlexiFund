import { useEffect, useMemo, useState } from "react";
import {
  fetchDashboard,
  fetchExpenseCategories,
  fetchExpenses,
  fetchIncome,
  fetchMonthlySummary,
  fetchRiderDemo,
} from "./api.js";

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

function formatPeriod(period) {
  if (!period?.month || !period?.year) return "All periods";
  return new Intl.DateTimeFormat("en-IN", { month: "long", year: "numeric" }).format(
    new Date(period.year, period.month - 1, 1),
  );
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
      <p className="chart-caption">Weekly values from Ravi’s synthetic history. Gross income and household essentials remain separate.</p>
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
      {error && <div className="setup-hint">Start the SQLite backend, run <code>python -m app.seed</code>, then try again.</div>}
    </div>
  );
}

export default function App() {
  const [active, setActive] = useState("overview");
  const [demo, setDemo] = useState(null);
  const [finance, setFinance] = useState(null);
  const [incomeRecords, setIncomeRecords] = useState([]);
  const [expenseRecords, setExpenseRecords] = useState([]);
  const [expenseCategories, setExpenseCategories] = useState({});
  const [monthlySummary, setMonthlySummary] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadDashboard() {
    setLoading(true);
    setError("");
    try {
      const [riderData, dashboardResponse] = await Promise.all([
        fetchRiderDemo(),
        fetchDashboard(),
      ]);
      const dashboard = dashboardResponse.data;
      const filters = {
        user_id: dashboard.user_id,
        month: dashboard.period.month,
        year: dashboard.period.year,
      };
      const [incomeResponse, expensesResponse, categoriesResponse, monthlyResponse] = await Promise.all([
        fetchIncome(filters),
        fetchExpenses(filters),
        fetchExpenseCategories(filters),
        fetchMonthlySummary({ user_id: dashboard.user_id, year: dashboard.period.year }),
      ]);
      setDemo(riderData);
      setFinance(dashboard);
      setIncomeRecords(incomeResponse.data);
      setExpenseRecords(expensesResponse.data);
      setExpenseCategories(categoriesResponse);
      setMonthlySummary(monthlyResponse);
    } catch {
      setDemo(null);
      setFinance(null);
      setError("The API or demo database is unavailable. Start the backend and seed the demo data, then try again.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadDashboard(); }, []);

  const history = demo?.history ?? [];
  const latest = history.at(-1);
  const categoryEntries = Object.entries(expenseCategories);
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
            <div className="profile-avatar">{finance?.user_name?.[0] ?? "F"}</div>
            <div className="profile-details">
              <div className="profile-name">{finance?.user_name ?? "FlexiFund Demo"}<span className="verified-badge" title="Synthetic demo account">✓</span></div>
              <div className="profile-meta">Sample finance account<span>·</span> {formatPeriod(finance?.period)}<span>·</span> All entries are synthetic</div>
            </div>
            <div className="synthetic-stamp"><span>✳</span> Fictional account<br /><small>For demonstration only</small></div>
          </section>

          {loading || error ? <EmptyState error={error} onRetry={loadDashboard} /> : (
            <>
              <section className="metrics-grid" aria-label="Monthly financial summary">
                <MetricCard label="Total income" value={formatMoney(finance.total_income)} detail={`${incomeRecords.length} entries · ${formatPeriod(finance.period)}`} icon="income" tone="green" />
                <MetricCard label="Total expenses" value={formatMoney(finance.total_expenses)} detail={`${expenseRecords.length} entries · ${finance.essential_expense_ratio}% essential`} icon="costs" tone="lavender" />
                <MetricCard label="Monthly surplus" value={formatMoney(finance.surplus)} detail={finance.financial_status} icon="calendar" tone={finance.surplus < 0 ? "sand" : "green"} />
                <MetricCard label="Savings rate" value={`${finance.savings_rate}%`} detail={`Expense ratio · ${finance.expense_ratio}%`} icon="overview" tone="blue" />
              </section>

              <section className="monthly-summary-panel" aria-label="Monthly summary from the API">
                <div className="monthly-summary-title"><div className="panel-kicker">MONTH BY MONTH</div><strong>Monthly snapshot</strong></div>
                <div className="monthly-summary-list">
                  {monthlySummary.map((item) => (
                    <div className="monthly-summary-row" key={`${item.year}-${item.month}`}>
                      <strong>{item.month} {item.year}</strong>
                      <span>Income <b>{formatMoney(item.income)}</b></span>
                      <span>Expenses <b>{formatMoney(item.expenses)}</b></span>
                      <span>Surplus <b>{formatMoney(item.surplus)}</b></span>
                    </div>
                  ))}
                  {monthlySummary.length === 0 && <span className="monthly-summary-empty">No monthly records yet.</span>}
                </div>
              </section>

              <section className="content-grid">
                <article className="panel income-panel" id="income">
                  <div className="panel-heading">
                    <div><div className="panel-kicker">RAVI · SYNTHETIC DELIVERY HISTORY</div><h2>Week by week</h2></div>
                    <div className="panel-range">{history.length ? `${formatWeek(history[0].date)} — ${formatWeek(latest.date)}` : ""}</div>
                  </div>
                  <IncomeChart history={history} />
                </article>

                <article className="panel cost-panel" id="costs">
                  <div className="panel-heading">
                    <div><div className="panel-kicker">{formatPeriod(finance.period).toUpperCase()}</div><h2>Expense categories</h2></div>
                    <div className="cost-date">{expenseRecords.length} entries</div>
                  </div>
                  <div className="cost-list">
                    {categoryEntries.map(([category, amount], index) => (
                      <div className="cost-row" key={category}>
                        <span className={`cost-marker marker-${index % 4}`} />
                        <span className="cost-name">{category}</span>
                        <span className="cost-value">{formatMoney(amount)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="separation-note"><span className="note-icon">i</span><span>Categories are returned by the Flask expense summary API.</span></div>
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
                  {featuredPatterns.length === 0 && <p className="no-patterns">No highlighted demo weeks in this history.</p>}
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
              <footer className="page-footer">FlexiFund demo · All finance and rider history shown here is synthetic and not real-world verified.</footer>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
