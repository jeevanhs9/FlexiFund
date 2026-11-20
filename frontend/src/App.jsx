import { useCallback, useEffect, useMemo, useState } from "react";
import {
  addExpense,
  addIncome,
  fetchDashboard,
  fetchExpenseCategories,
  fetchExpenses,
  fetchIncome,
  fetchMonthlySummary,
  fetchRiderDemo,
} from "./api.js";
import {
  ExpenseComparison,
  ExpenseDonutChart,
  MonthlyTrendChart,
  SavingsTrendChart,
} from "./charts.jsx";
import {
  combineTransactions,
  formatDate,
  formatMoney,
  formatPeriod,
  getHealthMessage,
  todayLocalDate,
} from "./utils.js";

const INCOME_TYPES = ["Salary", "Freelance", "Business", "Investment", "Other"];
const EXPENSE_CATEGORIES = [
  "Food", "Rent", "Transportation", "Utilities", "Education", "Healthcare",
  "Entertainment", "Shopping", "EMI", "Insurance", "Other",
];
const EXPENSE_TYPES = ["Essential", "Non-Essential"];

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 36 36" role="presentation">
        <path d="M7 25.5 14.2 9l5.2 11.2 3.2-6.6L29 25.5" />
        <path d="M8 28.5h20" />
      </svg>
    </span>
  );
}

function Icon({ name }) {
  const paths = {
    dashboard: <><rect x="3.5" y="3.5" width="8" height="8" rx="2" /><rect x="14.5" y="3.5" width="8" height="5" rx="2" /><rect x="14.5" y="11.5" width="8" height="8" rx="2" /><rect x="3.5" y="14.5" width="8" height="5" rx="2" /></>,
    transactions: <><path d="M4 6h16M4 12h16M4 18h16" /><circle cx="7" cy="6" r=".7" /><circle cx="7" cy="12" r=".7" /><circle cx="7" cy="18" r=".7" /></>,
    income: <><path d="M4 17V7" /><path d="m4 13 5-5 4 3 7-7" /><path d="M15 4h5v5" /></>,
    expenses: <><path d="M5 5h14v14H5z" /><path d="M8 9h8M8 13h5" /><path d="m15.5 17.5 2 2 4-4" /></>,
    analytics: <><path d="M4 19V5M4 19h17" /><path d="m7 15 4-4 3 2 6-7" /></>,
    health: <><path d="M12 21s8-4 8-11V5l-8-3-8 3v5c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="m19.4 15 .1.1 1.1.9-1 1.8-1.4-.5a8 8 0 0 1-1.5.9l-.3 1.5h-2.1l-.3-1.5a8 8 0 0 1-1.5-.9l-1.4.5-1-1.8 1.1-.9a7 7 0 0 1 0-1.8l-1.1-.9 1-1.8 1.4.5a8 8 0 0 1 1.5-.9l.3-1.5h2.1l.3 1.5a8 8 0 0 1 1.5.9l1.4-.5 1 1.8-1.1.9a7 7 0 0 1 0 1.8Z" transform="translate(-1.5 -1.5) scale(.95)" /></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M7 3v4M17 3v4M3 10h18" /></>,
    refresh: <><path d="M20 7v5h-5" /><path d="M19 12a7 7 0 1 1-2-5l3 5" /></>,
    arrow: <><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>,
  };

  return (
    <svg className="p3-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
  { id: "transactions", label: "Transactions", icon: "transactions" },
  { id: "income", label: "Income", icon: "income" },
  { id: "expenses", label: "Expenses", icon: "expenses" },
  { id: "analytics", label: "Analytics", icon: "analytics" },
  { id: "health", label: "Financial Health", icon: "health" },
  { id: "settings", label: "Settings", icon: "settings" },
];

function Sidebar({ active, onNavigate, userName }) {
  return (
    <aside className="sidebar phase3-sidebar">
      <button className="brand" type="button" onClick={() => onNavigate("dashboard")} aria-label="FlexiFund dashboard">
        <BrandMark />
        <span>flexifund<span className="brand-period">.</span></span>
      </button>
      <div className="sidebar-label">WORKSPACE</div>
      <nav className="side-nav phase3-nav" aria-label="Main navigation">
        {NAV_ITEMS.map((item) => (
          <button
            className={`nav-item phase3-nav-item${active === item.id ? " active" : ""}`}
            type="button"
            key={item.id}
            onClick={() => onNavigate(item.id)}
            aria-current={active === item.id ? "page" : undefined}
            title={item.label}
          >
            <Icon name={item.icon} /><span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-bottom phase3-sidebar-bottom">
        <div className="sidebar-orbit" aria-hidden="true"><span>F</span></div>
        <p className="sidebar-bottom-title">A steadier view of money</p>
        <p className="sidebar-bottom-copy">Built for work and income that can change week to week.</p>
        <div className="sidebar-footer">{userName ? userName.toUpperCase() : "FLEXIFUND"} · DEMO</div>
      </div>
    </aside>
  );
}

function MetricCard({ label, value, detail, icon, tone = "green" }) {
  return (
    <article className={`metric-card phase3-metric tone-${tone}`}>
      <div className="metric-topline">
        <span className="metric-label">{label}</span>
        <span className="metric-icon"><Icon name={icon} /></span>
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-detail">{detail}</div>
    </article>
  );
}

function Panel({ title, kicker, action, children, className = "" }) {
  return (
    <section className={`panel p3-panel ${className}`}>
      <div className="panel-heading p3-panel-heading">
        <div>{kicker && <div className="panel-kicker">{kicker}</div>}<h2>{title}</h2></div>
        {action}
      </div>
      {children}
    </section>
  );
}

function PageTitle({ eyebrow, title, subtitle, action }) {
  return (
    <div className="p3-page-title">
      <div>
        {eyebrow && <div className="p3-eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

function HealthBadge({ status }) {
  const safeStatus = status || "Unknown";
  const className = safeStatus.toLowerCase().replaceAll(" ", "-");
  return <span className={`p3-health-badge status-${className}`}>{safeStatus}</span>;
}

function HealthSummary({ summary, onOpen }) {
  return (
    <section className={`p3-health-summary health-${String(summary.financial_status || "unknown").toLowerCase().replaceAll(" ", "-")}`}>
      <div className="p3-health-summary-main">
        <div className="p3-health-mark"><Icon name="health" /></div>
        <div>
          <div className="p3-eyebrow">FINANCIAL HEALTH · {formatPeriod(summary.period)}</div>
          <h2><HealthBadge status={summary.financial_status} /></h2>
          <p>{getHealthMessage(summary)}</p>
        </div>
      </div>
      <div className="p3-health-metrics">
        <div><span>Savings rate</span><strong>{Number(summary.savings_rate).toFixed(1)}%</strong></div>
        <div><span>Expense ratio</span><strong>{Number(summary.expense_ratio).toFixed(1)}%</strong></div>
        <div><span>Essential expenses</span><strong>{formatMoney(summary.essential_expenses)}</strong></div>
      </div>
      {onOpen && <button type="button" className="p3-text-button" onClick={onOpen}>View health details <Icon name="arrow" /></button>}
    </section>
  );
}

function LoadingState() {
  return (
    <div className="p3-loading-state" role="status" aria-live="polite">
      <span className="p3-spinner" aria-hidden="true" />
      <strong>Loading financial data…</strong>
      <p>Connecting to the FlexiFund API and preparing your dashboard.</p>
      <div className="p3-skeleton-grid" aria-hidden="true">{Array.from({ length: 5 }, (_, index) => <span key={index} />)}</div>
    </div>
  );
}

function ConnectionState({ onRetry }) {
  return (
    <div className="p3-connection-state" role="alert">
      <div className="p3-connection-icon"><Icon name="refresh" /></div>
      <h2>Unable to connect to FlexiFund server.</h2>
      <p>Please make sure the Flask backend is running and the demo data is seeded, then try again.</p>
      <button className="p3-primary-button" type="button" onClick={onRetry}><Icon name="refresh" /> Retry connection</button>
    </div>
  );
}

function TransactionsTable({ rows, emptyMessage = "No transactions found for these filters." }) {
  if (!rows.length) return <div className="p3-empty-list">{emptyMessage}</div>;
  return (
    <div className="p3-table-scroll">
      <table className="p3-table">
        <thead><tr><th scope="col">Date</th><th scope="col">Description</th><th scope="col">Source / category</th><th scope="col">Type</th><th scope="col" className="align-right">Amount</th></tr></thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.recordType}-${row.id}`}>
              <td className="p3-date-cell">{formatDate(row.date)}</td>
              <td><strong className="p3-row-title">{row.label}</strong></td>
              <td>{row.categoryLabel}</td>
              <td><span className={`p3-type-label ${row.recordType === "Income" ? "type-income" : "type-expense"}`}><span aria-hidden="true">{row.recordType === "Income" ? "↗" : "↘"}</span>{row.recordType} · {row.subtype}</span></td>
              <td className={`align-right p3-amount ${row.recordType === "Income" ? "amount-income" : "amount-expense"}`}>{row.recordType === "Income" ? "+" : "−"}{formatMoney(Math.abs(row.signedAmount))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RiderHistory({ demo }) {
  const history = demo?.history || [];
  if (!history.length) return null;
  const width = 760;
  const height = 170;
  const values = history.map((item) => Number(item.gross_income));
  const maxValue = Math.max(1, ...values);
  const left = 8;
  const right = width - 8;
  const top = 12;
  const bottom = height - 20;
  const xAt = (index) => left + (index / Math.max(1, history.length - 1)) * (right - left);
  const yAt = (value) => bottom - (value / maxValue) * (bottom - top);
  const line = values.map((value, index) => `${index === 0 ? "M" : "L"} ${xAt(index).toFixed(1)} ${yAt(value).toFixed(1)}`).join(" ");
  const start = history[0];
  const end = history[history.length - 1];

  return (
    <details className="p3-rider-history">
      <summary>Show synthetic rider history <span>32 weekly entries</span></summary>
      <div className="p3-rider-history-content">
        <p>Ravi’s original Phase 1 weekly gross income history remains available here. These records are fictional and separate from the finance demo account.</p>
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Synthetic rider weekly income history">
          <line x1={left} x2={right} y1={bottom} y2={bottom} className="p3-chart-grid" />
          <path d={line} className="p3-rider-line" />
          {history.map((item, index) => <circle key={item.id} cx={xAt(index)} cy={yAt(Number(item.gross_income))} r="2.8" className="p3-rider-dot"><title>{`${formatDate(item.date)}: ${formatMoney(item.gross_income)}`}</title></circle>)}
          <text x={left} y={height - 3} className="p3-chart-label">{formatDate(start.date)}</text>
          <text x={right} y={height - 3} textAnchor="end" className="p3-chart-label">{formatDate(end.date)}</text>
        </svg>
      </div>
    </details>
  );
}

function DashboardPage({ summary, monthly, categories, transactions, demo, onNavigate }) {
  return (
    <>
      <PageTitle eyebrow="FLEXIFUND · FINANCIAL OVERVIEW" title={`Welcome back${summary.user_name ? `, ${summary.user_name}` : ""}.`} subtitle={`Here is your financial picture for ${formatPeriod(summary.period)}.`} action={<span className="p3-period-pill"><Icon name="calendar" />{formatPeriod(summary.period)}</span>} />
      <section className="metrics-grid phase3-metrics-grid" aria-label="Financial overview">
        <MetricCard label="Total income" value={formatMoney(summary.total_income)} detail="For this month" icon="income" tone="green" />
        <MetricCard label="Total expenses" value={formatMoney(summary.total_expenses)} detail={`${Number(summary.essential_expense_ratio).toFixed(1)}% essential`} icon="expenses" tone="lavender" />
        <MetricCard label={Number(summary.surplus) < 0 ? "Monthly deficit" : "Monthly surplus"} value={formatMoney(Math.abs(Number(summary.surplus)))} detail={Number(summary.surplus) < 0 ? "Deficit" : "Remaining after expenses"} icon="calendar" tone={Number(summary.surplus) < 0 ? "sand" : "green"} />
        <MetricCard label="Savings rate" value={`${Number(summary.savings_rate).toFixed(1)}%`} detail={`Expense ratio · ${Number(summary.expense_ratio).toFixed(1)}%`} icon="analytics" tone="blue" />
        <MetricCard label="Financial health" value={<HealthBadge status={summary.financial_status} />} detail="Status from the FlexiFund API" icon="health" tone="mint" />
      </section>

      <HealthSummary summary={summary} onOpen={() => onNavigate("health")} />

      <section className="p3-dashboard-grid p3-chart-grid-main">
        <Panel title="Monthly financial trend" kicker="CASH FLOW" className="p3-trend-panel">
          <MonthlyTrendChart rows={monthly} />
        </Panel>
        <Panel title="Expense distribution" kicker="THIS MONTH" className="p3-donut-panel">
          <ExpenseDonutChart categories={categories} />
        </Panel>
      </section>

      <section className="p3-dashboard-grid p3-lower-grid">
        <Panel title="Essential vs non-essential" kicker="SPENDING MIX" className="p3-comparison-panel">
          <ExpenseComparison essential={summary.essential_expenses} nonEssential={summary.non_essential_expenses} />
        </Panel>
        <Panel title="Recent transactions" kicker="LATEST ACTIVITY" className="p3-recent-panel" action={<button type="button" className="p3-link-button" onClick={() => onNavigate("transactions")}>View all <Icon name="arrow" /></button>}>
          <TransactionsTable rows={transactions.slice(0, 5)} emptyMessage="No financial data available yet. Add your first income or expense to get started." />
        </Panel>
      </section>

      <RiderHistory demo={demo} />
      <footer className="p3-footer">FlexiFund demo · Financial records are synthetic examples for demonstration only.</footer>
    </>
  );
}

function useTransactionRows(incomeRecords, expenseRecords) {
  return useMemo(() => combineTransactions(incomeRecords, expenseRecords), [incomeRecords, expenseRecords]);
}

function validateCommonForm(values, amount) {
  if (!values.date) return "Choose a transaction date.";
  if (Number.isNaN(new Date(`${values.date}T00:00:00`).getTime())) return "Enter a valid date.";
  if (!values.amount || !Number.isFinite(amount) || amount <= 0) return "Amount must be greater than ₹0.";
  if (amount > 9999999999.99) return "Amount is above the supported limit.";
  return "";
}

function IncomeForm({ userId, onCreated }) {
  const [values, setValues] = useState({ source: "", amount: "", income_type: "Salary", date: todayLocalDate(), description: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
    setError("");
    setSuccess("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    const amount = Number(values.amount);
    const commonError = validateCommonForm(values, amount);
    if (!values.source.trim()) return setError("Enter an income source.");
    if (commonError) return setError(commonError);

    setSubmitting(true);
    try {
      await addIncome({ ...values, user_id: userId, amount });
      setSuccess("Income added successfully.");
      setValues({ source: "", amount: "", income_type: "Salary", date: todayLocalDate(), description: "" });
      await onCreated();
    } catch (requestError) {
      setError(requestError.message || "Unable to add income. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="p3-form" onSubmit={handleSubmit} noValidate>
      <label>Source <span aria-hidden="true">*</span><input value={values.source} onChange={(event) => update("source", event.target.value)} maxLength="120" required placeholder="e.g. Monthly salary" /></label>
      <label>Amount <span aria-hidden="true">*</span><div className="p3-input-prefix"><span>₹</span><input value={values.amount} onChange={(event) => update("amount", event.target.value)} type="number" min="0.01" max="9999999999.99" step="0.01" required placeholder="0.00" inputMode="decimal" /></div></label>
      <label>Income type <span aria-hidden="true">*</span><select value={values.income_type} onChange={(event) => update("income_type", event.target.value)} required>{INCOME_TYPES.map((type) => <option key={type}>{type}</option>)}</select></label>
      <label>Date <span aria-hidden="true">*</span><input value={values.date} onChange={(event) => update("date", event.target.value)} type="date" required /></label>
      <label className="p3-form-wide">Description <span className="p3-optional">Optional</span><textarea value={values.description} onChange={(event) => update("description", event.target.value)} maxLength="500" rows="3" placeholder="Add a short note" /></label>
      {error && <p className="p3-form-message form-error" role="alert">{error}</p>}
      {success && <p className="p3-form-message form-success" role="status">{success}</p>}
      <div className="p3-form-actions"><span className="p3-required-hint">* Required fields</span><button className="p3-primary-button" type="submit" disabled={submitting || !userId}>{submitting ? "Saving…" : "Add income"}<Icon name="arrow" /></button></div>
    </form>
  );
}

function ExpenseForm({ userId, onCreated }) {
  const [values, setValues] = useState({ category: "Food", amount: "", expense_type: "Essential", date: todayLocalDate(), description: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
    setError("");
    setSuccess("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    const amount = Number(values.amount);
    const commonError = validateCommonForm(values, amount);
    if (!values.category) return setError("Choose an expense category.");
    if (!values.expense_type) return setError("Choose an expense type.");
    if (commonError) return setError(commonError);

    setSubmitting(true);
    try {
      await addExpense({ ...values, user_id: userId, amount });
      setSuccess("Expense added successfully.");
      setValues({ category: "Food", amount: "", expense_type: "Essential", date: todayLocalDate(), description: "" });
      await onCreated();
    } catch (requestError) {
      setError(requestError.message || "Unable to add expense. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="p3-form" onSubmit={handleSubmit} noValidate>
      <label>Category <span aria-hidden="true">*</span><select value={values.category} onChange={(event) => update("category", event.target.value)} required>{EXPENSE_CATEGORIES.map((category) => <option key={category}>{category}</option>)}</select></label>
      <label>Amount <span aria-hidden="true">*</span><div className="p3-input-prefix"><span>₹</span><input value={values.amount} onChange={(event) => update("amount", event.target.value)} type="number" min="0.01" max="9999999999.99" step="0.01" required placeholder="0.00" inputMode="decimal" /></div></label>
      <label>Expense type <span aria-hidden="true">*</span><select value={values.expense_type} onChange={(event) => update("expense_type", event.target.value)} required>{EXPENSE_TYPES.map((type) => <option key={type}>{type}</option>)}</select></label>
      <label>Date <span aria-hidden="true">*</span><input value={values.date} onChange={(event) => update("date", event.target.value)} type="date" required /></label>
      <label className="p3-form-wide">Description <span className="p3-optional">Optional</span><textarea value={values.description} onChange={(event) => update("description", event.target.value)} maxLength="500" rows="3" placeholder="Add a short note" /></label>
      {error && <p className="p3-form-message form-error" role="alert">{error}</p>}
      {success && <p className="p3-form-message form-success" role="status">{success}</p>}
      <div className="p3-form-actions"><span className="p3-required-hint">* Required fields</span><button className="p3-primary-button" type="submit" disabled={submitting || !userId}>{submitting ? "Saving…" : "Add expense"}<Icon name="arrow" /></button></div>
    </form>
  );
}

function IncomePage({ userId, records, onCreated }) {
  const transactions = useTransactionRows(records, []);
  return (
    <>
      <PageTitle eyebrow="INCOME MANAGEMENT" title="Income" subtitle="Record income sources and review your history." />
      <section className="p3-dashboard-grid p3-management-grid">
        <Panel title="Add income" kicker="NEW RECORD"><IncomeForm userId={userId} onCreated={onCreated} /></Panel>
        <Panel title="Income history" kicker={`${records.length} RECORD${records.length === 1 ? "" : "S"}`} className="p3-management-list-panel"><TransactionsTable rows={transactions} emptyMessage="No income records yet. Add your first income above." /></Panel>
      </section>
    </>
  );
}

function ExpensesPage({ userId, records, onCreated }) {
  const transactions = useTransactionRows([], records);
  return (
    <>
      <PageTitle eyebrow="EXPENSE MANAGEMENT" title="Expenses" subtitle="Track spending by category and type." />
      <section className="p3-dashboard-grid p3-management-grid">
        <Panel title="Add expense" kicker="NEW RECORD"><ExpenseForm userId={userId} onCreated={onCreated} /></Panel>
        <Panel title="Expense history" kicker={`${records.length} RECORD${records.length === 1 ? "" : "S"}`} className="p3-management-list-panel"><TransactionsTable rows={transactions} emptyMessage="No expenses recorded yet. Add your first expense above." /></Panel>
      </section>
    </>
  );
}

function TransactionsPage({ rows, filters, onChange, loading, error }) {
  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 8 }, (_, index) => String(currentYear - index));
  return (
    <>
      <PageTitle eyebrow="TRANSACTION HISTORY" title="Transactions" subtitle="Search income and expenses using the filters supported by the API." />
      <Panel title="Filter records" kicker="REFINE YOUR VIEW" className="p3-filter-panel">
        <div className="p3-filters">
          <label>Record type<select value={filters.kind} onChange={(event) => onChange("kind", event.target.value)}><option value="all">All records</option><option value="income">Income</option><option value="expense">Expenses</option></select></label>
          <label>Category<select value={filters.category} onChange={(event) => onChange("category", event.target.value)} disabled={filters.kind === "income"}><option value="">All categories</option>{EXPENSE_CATEGORIES.map((category) => <option key={category}>{category}</option>)}</select></label>
          <label>Month<select value={filters.month} onChange={(event) => onChange("month", event.target.value)}><option value="">All months</option>{Array.from({ length: 12 }, (_, index) => <option key={index + 1} value={String(index + 1)}>{new Intl.DateTimeFormat("en-IN", { month: "long" }).format(new Date(2020, index, 1))}</option>)}</select></label>
          <label>Year<select value={filters.year} onChange={(event) => onChange("year", event.target.value)}><option value="">All years</option>{years.map((year) => <option key={year}>{year}</option>)}</select></label>
        </div>
      </Panel>
      <Panel title="All transactions" kicker={loading ? "UPDATING" : `${rows.length} MATCHING RECORD${rows.length === 1 ? "" : "S"}`}>
        {error && <p className="p3-inline-error" role="alert">{error}</p>}
        {loading ? <div className="p3-inline-loading" role="status">Loading transactions…</div> : <TransactionsTable rows={rows} emptyMessage="No financial data available for the selected filters." />}
      </Panel>
    </>
  );
}

function AnalyticsPage({ summary, monthly, categories }) {
  const average = (field) => monthly.length ? monthly.reduce((sum, row) => sum + Number(row[field] || 0), 0) / monthly.length : null;
  const highestCategory = Object.entries(categories).sort((left, right) => Number(right[1]) - Number(left[1]))[0];
  return (
    <>
      <PageTitle eyebrow="VISUAL ANALYTICS" title="Analytics" subtitle="Explore monthly cash flow and spending patterns from your records." action={<span className="p3-period-pill"><Icon name="calendar" />{formatPeriod(summary.period)}</span>} />
      <section className="metrics-grid phase3-analytics-metrics" aria-label="Key analytics metrics">
        <MetricCard label="Average monthly income" value={average("income") === null ? "—" : formatMoney(average("income"))} detail={`${monthly.length} month${monthly.length === 1 ? "" : "s"} in the API summary`} icon="income" tone="green" />
        <MetricCard label="Average monthly expenses" value={average("expenses") === null ? "—" : formatMoney(average("expenses"))} detail="Across available monthly records" icon="expenses" tone="lavender" />
        <MetricCard label="Average monthly surplus" value={average("surplus") === null ? "—" : formatMoney(average("surplus"))} detail="Income less expenses" icon="analytics" tone="blue" />
        <MetricCard label="Highest expense category" value={highestCategory?.[0] || "—"} detail={highestCategory ? formatMoney(highestCategory[1]) : "No category data"} icon="calendar" tone="sand" />
      </section>
      <section className="p3-dashboard-grid p3-analytics-grid">
        <Panel title="Income vs expenses" kicker="MONTHLY TREND" className="p3-trend-panel"><MonthlyTrendChart rows={monthly} /></Panel>
        <Panel title="Savings trend" kicker="MONTHLY SURPLUS"><SavingsTrendChart rows={monthly} /></Panel>
        <Panel title="Expense distribution" kicker="CURRENT PERIOD"><ExpenseDonutChart categories={categories} /></Panel>
        <Panel title="Essential vs non-essential" kicker="CURRENT PERIOD"><ExpenseComparison essential={summary.essential_expenses} nonEssential={summary.non_essential_expenses} /></Panel>
      </section>
    </>
  );
}

function HealthPage({ summary }) {
  return (
    <>
      <PageTitle eyebrow="FINANCIAL HEALTH" title="Your monthly health" subtitle={`Status and indicators returned by the backend for ${formatPeriod(summary.period)}.`} />
      <HealthSummary summary={summary} />
      <section className="metrics-grid phase3-health-metrics-grid">
        <MetricCard label="Monthly surplus / deficit" value={formatMoney(Math.abs(Number(summary.surplus)))} detail={Number(summary.surplus) < 0 ? "Deficit" : "Surplus"} icon="calendar" tone={Number(summary.surplus) < 0 ? "sand" : "green"} />
        <MetricCard label="Savings rate" value={`${Number(summary.savings_rate).toFixed(1)}%`} detail="Returned by the financial engine" icon="analytics" tone="blue" />
        <MetricCard label="Expense ratio" value={`${Number(summary.expense_ratio).toFixed(1)}%`} detail="Expenses relative to income" icon="expenses" tone="lavender" />
        <MetricCard label="Deficit amount" value={formatMoney(summary.deficit)} detail="Zero when there is no deficit" icon="health" tone="sand" />
      </section>
    </>
  );
}

function SettingsPage({ summary }) {
  return (
    <>
      <PageTitle eyebrow="SETTINGS" title="Demo profile" subtitle="Basic profile details for this Phase 3 demonstration." />
      <Panel title="Account details" kicker="READ-ONLY DEMO" className="p3-settings-panel">
        <dl className="p3-settings-list"><div><dt>Name</dt><dd>{summary.user_name || "FlexiFund Demo"}</dd></div><div><dt>User ID</dt><dd>{summary.user_id}</dd></div><div><dt>Data source</dt><dd>SQLite demo database</dd></div><div><dt>Data type</dt><dd>Fictional sample records</dd></div></dl>
        <p className="p3-settings-note">Profile editing and account security are outside this phase.</p>
      </Panel>
    </>
  );
}

function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [summary, setSummary] = useState(null);
  const [monthly, setMonthly] = useState([]);
  const [categories, setCategories] = useState({});
  const [incomeRecords, setIncomeRecords] = useState([]);
  const [expenseRecords, setExpenseRecords] = useState([]);
  const [demo, setDemo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [transactionFilters, setTransactionFilters] = useState({ kind: "all", category: "", month: "", year: "" });
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [transactionsLoading, setTransactionsLoading] = useState(false);
  const [transactionsError, setTransactionsError] = useState("");
  const [transactionRevision, setTransactionRevision] = useState(0);

  const loadDashboardData = useCallback(async (initialLoad = false) => {
    if (initialLoad) setLoading(true);
    else setRefreshing(true);
    setError("");
    try {
      const dashboardResponse = await fetchDashboard();
      const nextSummary = dashboardResponse?.data;
      if (!nextSummary) throw new Error("The dashboard response was incomplete.");
      const userParams = { user_id: nextSummary.user_id };
      const periodParams = { ...userParams, month: nextSummary.period.month, year: nextSummary.period.year };
      const [monthlyRows, categoryTotals, incomeResponse, expenseResponse, riderResponse] = await Promise.all([
        fetchMonthlySummary({ ...userParams, year: nextSummary.period.year }),
        fetchExpenseCategories(periodParams),
        fetchIncome(userParams),
        fetchExpenses(userParams),
        fetchRiderDemo(),
      ]);

      setSummary(nextSummary);
      setMonthly(Array.isArray(monthlyRows) ? monthlyRows : []);
      setCategories(categoryTotals || {});
      setIncomeRecords(incomeResponse?.data || []);
      setExpenseRecords(expenseResponse?.data || []);
      setDemo(riderResponse?.data || riderResponse);
    } catch {
      setError("Unable to connect to FlexiFund server. Please make sure the Flask backend is running.");
    } finally {
      if (initialLoad) setLoading(false);
      else setRefreshing(false);
    }
  }, []);

  useEffect(() => { void loadDashboardData(true); }, [loadDashboardData]);

  useEffect(() => {
    if (activePage !== "transactions" || !summary) return undefined;
    let cancelled = false;
    setTransactionsLoading(true);
    setTransactionsError("");
    const params = {
      user_id: summary.user_id,
      month: transactionFilters.month || undefined,
      year: transactionFilters.year || undefined,
    };
    const incomeRequest = transactionFilters.kind === "expense" ? Promise.resolve({ data: [] }) : fetchIncome(params);
    const expenseParams = { ...params, category: transactionFilters.category || undefined };
    const expenseRequest = transactionFilters.kind === "income" ? Promise.resolve({ data: [] }) : fetchExpenses(expenseParams);
    Promise.all([incomeRequest, expenseRequest])
      .then(([incomeResponse, expenseResponse]) => {
        if (!cancelled) setFilteredTransactions(combineTransactions(incomeResponse?.data || [], expenseResponse?.data || []));
      })
      .catch(() => {
        if (!cancelled) setTransactionsError("Unable to load transactions. Please check the backend connection and retry.");
      })
      .finally(() => { if (!cancelled) setTransactionsLoading(false); });
    return () => { cancelled = true; };
  }, [activePage, summary, transactionFilters.kind, transactionFilters.category, transactionFilters.month, transactionFilters.year, transactionRevision]);

  const transactions = useTransactionRows(incomeRecords, expenseRecords);
  const pageTitle = NAV_ITEMS.find((item) => item.id === activePage)?.label || "Dashboard";

  function updateTransactionFilter(field, value) {
    setTransactionFilters((current) => ({ ...current, [field]: value }));
  }

  async function handleRecordCreated() {
    await loadDashboardData(false);
    setTransactionRevision((current) => current + 1);
  }

  function renderCurrentPage() {
    if (!summary) return null;
    switch (activePage) {
      case "transactions":
        return <TransactionsPage rows={filteredTransactions} filters={transactionFilters} onChange={updateTransactionFilter} loading={transactionsLoading} error={transactionsError} />;
      case "income":
        return <IncomePage userId={summary.user_id} records={incomeRecords} onCreated={handleRecordCreated} />;
      case "expenses":
        return <ExpensesPage userId={summary.user_id} records={expenseRecords} onCreated={handleRecordCreated} />;
      case "analytics":
        return <AnalyticsPage summary={summary} monthly={monthly} categories={categories} />;
      case "health":
        return <HealthPage summary={summary} />;
      case "settings":
        return <SettingsPage summary={summary} />;
      default:
        return <DashboardPage summary={summary} monthly={monthly} categories={categories} transactions={transactions} demo={demo} onNavigate={setActivePage} />;
    }
  }

  return (
    <div className="app-shell phase3-shell">
      <Sidebar active={activePage} onNavigate={setActivePage} userName={summary?.user_name} />
      <main className="main-content phase3-main">
        <header className="topbar phase3-topbar">
          <div className="p3-breadcrumb"><span>Workspace</span><span aria-hidden="true">/</span><strong>{pageTitle}</strong></div>
          <div className="p3-topbar-right">
            <div className="p3-api-status"><span className={`p3-status-dot${error ? " offline" : loading ? " checking" : ""}`} />{error ? "API disconnected" : refreshing ? "Refreshing" : loading ? "Connecting" : "API connected"}</div>
            <span className="p3-demo-chip"><span />SYNTHETIC DEMO</span>
            <span className="p3-avatar" aria-label={`${summary?.user_name || "FlexiFund"} profile`}>{summary?.user_name?.[0] || "F"}</span>
          </div>
        </header>
        <div className="page-content phase3-page-content">
          {error && summary && <div className="p3-refresh-error" role="status">Showing the last loaded data. {error} <button type="button" onClick={() => loadDashboardData(false)}>Retry</button></div>}
          {loading && !summary ? <LoadingState /> : error && !summary ? <ConnectionState onRetry={() => loadDashboardData(true)} /> : renderCurrentPage()}
        </div>
      </main>
    </div>
  );
}

export default App;
