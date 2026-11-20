import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
    search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 4.5 4.5" /></>,
    bell: <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>,
    moon: <><path d="M20.5 15.5A8.5 8.5 0 0 1 8.5 3.5 8.5 8.5 0 1 0 20.5 15.5Z" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
    collapse: <><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M9 4v16M14 9l-3 3 3 3" /></>,
    expand: <><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M9 4v16m3-7 3 3-3 3" /></>,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
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

function Sidebar({ active, onNavigate, userName, collapsed, onToggleCollapse }) {
  return (
    <aside className="sidebar phase3-sidebar">
      <div className="p3-sidebar-head">
        <button className="brand" type="button" onClick={() => onNavigate("dashboard")} aria-label="FlexiFund dashboard">
          <BrandMark />
          <span>flexifund<span className="brand-period">.</span></span>
        </button>
        <button className="p3-collapse-button" type="button" onClick={onToggleCollapse} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-expanded={!collapsed} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
          <Icon name={collapsed ? "expand" : "collapse"} />
        </button>
      </div>
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
        <div className="p3-sidebar-profile">
          <span className="p3-sidebar-avatar" aria-hidden="true">{userName?.[0] || "F"}</span>
          <span><strong>{userName || "FlexiFund"}</strong><small>Demo profile</small></span>
        </div>
        <div className="p3-sidebar-note"><strong>A steadier view of money</strong><span>Built for income that can change week to week.</span></div>
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

function PeriodSelector({ value, onChange }) {
  return (
    <label className="p3-period-select-wrap">
      <Icon name="calendar" />
      <span className="sr-only">Dashboard period</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="this-month">This Month</option>
        <option value="last-month">Last Month</option>
        <option value="this-year">This Year</option>
      </select>
      <span className="p3-period-chevron" aria-hidden="true">⌄</span>
    </label>
  );
}

function Topbar({
  pageTitle,
  loading,
  refreshing,
  error,
  userName,
  theme,
  onToggleTheme,
  search,
  onSearchChange,
  onSearchSubmit,
  notificationsOpen,
  onToggleNotifications,
  onNavigate,
}) {
  return (
    <header className="topbar phase3-topbar">
      <div className="p3-breadcrumb"><span>Workspace</span><span aria-hidden="true">/</span><strong>{pageTitle}</strong></div>
      <div className="p3-topbar-right">
        <form className="p3-top-search" role="search" onSubmit={onSearchSubmit}>
          <Icon name="search" />
          <input aria-label="Search transactions" placeholder="Search transactions" value={search} onChange={(event) => onSearchChange(event.target.value)} />
          <button type="submit" aria-label="Show matching transactions"><span>⌕</span></button>
        </form>
        <div className="p3-api-status"><span className={`p3-status-dot${error ? " offline" : loading ? " checking" : ""}`} />{error ? "API disconnected" : refreshing ? "Refreshing" : loading ? "Connecting" : "API connected"}</div>
        <span className="p3-demo-chip"><span />SYNTHETIC DEMO</span>
        <button className="p3-icon-button" type="button" onClick={onToggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`} title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}><Icon name={theme === "dark" ? "sun" : "moon"} /></button>
        <div className="p3-notification-wrap">
          <button className="p3-icon-button" type="button" onClick={onToggleNotifications} aria-label="Notifications" aria-expanded={notificationsOpen} title="Notifications"><Icon name="bell" /></button>
          {notificationsOpen && <div className="p3-notification-popover" role="status"><strong>No new notifications</strong><span>Notification preferences are managed on this device.</span><button type="button" onClick={() => onNavigate("settings")}>Manage preferences</button></div>}
        </div>
        <button className="p3-profile-button" type="button" onClick={() => onNavigate("settings")} aria-label={`Open ${userName || "FlexiFund"} profile settings`} title="Profile settings">{userName?.[0] || "F"}</button>
      </div>
    </header>
  );
}

function Toast({ toast, onDismiss }) {
  if (!toast) return null;
  const role = toast.type === "error" ? "alert" : "status";
  return (
    <div className={`p3-toast toast-${toast.type || "success"}`} role={role} aria-live={role === "status" ? "polite" : "assertive"}>
      <span className="p3-toast-mark" aria-hidden="true">{toast.type === "error" ? "!" : "✓"}</span>
      <span>{toast.message}</span>
      <button type="button" onClick={onDismiss} aria-label="Dismiss notification"><Icon name="close" /></button>
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
        <div><span>Essential ratio</span><strong>{Number(summary.essential_expense_ratio).toFixed(1)}%</strong></div>
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

function TransactionsTable({ rows, emptyTitle = "No transactions yet", emptyMessage = "No transactions found for these filters.", onAddIncome, onAddExpense }) {
  if (!rows.length) return (
    <div className="p3-empty-list">
      <strong>{emptyTitle}</strong>
      <span>{emptyMessage}</span>
      {(onAddIncome || onAddExpense) && <div className="p3-empty-actions">{onAddIncome && <button type="button" onClick={onAddIncome}>+ Add income</button>}{onAddExpense && <button type="button" onClick={onAddExpense}>+ Add expense</button>}</div>}
    </div>
  );
  return (
    <div className="p3-table-scroll">
      <table className="p3-table">
        <thead><tr><th scope="col">Date</th><th scope="col">Description</th><th scope="col">Source / category</th><th scope="col">Type</th><th scope="col" className="align-right">Amount</th></tr></thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.recordType}-${row.id}`}>
              <td data-label="Date" className="p3-date-cell">{formatDate(row.date)}</td>
              <td data-label="Description"><strong className="p3-row-title">{row.label}</strong></td>
              <td data-label="Source / category">{row.categoryLabel}</td>
              <td data-label="Type"><span className={`p3-type-label ${row.recordType === "Income" ? "type-income" : "type-expense"}`}><span aria-hidden="true">{row.recordType === "Income" ? "↗" : "↘"}</span>{row.recordType} · {row.subtype}</span></td>
              <td data-label="Amount" className={`align-right p3-amount ${row.recordType === "Income" ? "amount-income" : "amount-expense"}`}>{row.recordType === "Income" ? "+" : "−"}{formatMoney(Math.abs(row.signedAmount))}</td>
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

function DashboardPage({ summary, monthly, categories, transactions, demo, onNavigate, periodSelection, onPeriodChange }) {
  return (
    <>
      <PageTitle eyebrow="FLEXIFUND · FINANCIAL OVERVIEW" title={`Welcome back${summary.user_name ? `, ${summary.user_name}` : ""}.`} subtitle={`Here is your financial picture for ${formatPeriod(summary.period)}.`} action={<PeriodSelector value={periodSelection} onChange={onPeriodChange} />} />
      <section className="metrics-grid phase3-metrics-grid" aria-label="Financial overview">
        <MetricCard label="Total income" value={formatMoney(summary.total_income)} detail="For the selected period" icon="income" tone="green" />
        <MetricCard label="Total expenses" value={formatMoney(summary.total_expenses)} detail={`${Number(summary.essential_expense_ratio).toFixed(1)}% essential`} icon="expenses" tone="lavender" />
        <MetricCard label={`${summary.period.month ? "Period" : "Yearly"} ${Number(summary.surplus) < 0 ? "deficit" : "surplus"}`} value={formatMoney(Math.abs(Number(summary.surplus)))} detail={Number(summary.surplus) < 0 ? "Deficit" : "Remaining after expenses"} icon="calendar" tone={Number(summary.surplus) < 0 ? "sand" : "green"} />
        <MetricCard label="Savings rate" value={`${Number(summary.savings_rate).toFixed(1)}%`} detail={`Expense ratio · ${Number(summary.expense_ratio).toFixed(1)}%`} icon="analytics" tone="blue" />
        <MetricCard label="Financial health" value={<HealthBadge status={summary.financial_status} />} detail="Status from the FlexiFund API" icon="health" tone="mint" />
      </section>

      <HealthSummary summary={summary} onOpen={() => onNavigate("health")} />

      <section className="p3-dashboard-grid p3-chart-grid-main">
        <Panel title="Monthly financial trend" kicker="CASH FLOW" className="p3-trend-panel">
          <MonthlyTrendChart rows={monthly} />
        </Panel>
        <Panel title="Expense distribution" kicker={formatPeriod(summary.period).toUpperCase()} className="p3-donut-panel">
          <ExpenseDonutChart categories={categories} />
        </Panel>
      </section>

      <section className="p3-dashboard-grid p3-lower-grid">
        <Panel title="Essential vs non-essential" kicker="SPENDING MIX" className="p3-comparison-panel">
          <ExpenseComparison essential={summary.essential_expenses} nonEssential={summary.non_essential_expenses} />
        </Panel>
        <Panel title="Recent transactions" kicker="LATEST ACTIVITY" className="p3-recent-panel" action={<button type="button" className="p3-link-button" onClick={() => onNavigate("transactions")}>View all <Icon name="arrow" /></button>}>
          <TransactionsTable rows={transactions.slice(0, 5)} emptyMessage="Start by adding your first income or expense." onAddIncome={() => onNavigate("income")} onAddExpense={() => onNavigate("expenses")} />
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

function IncomeForm({ userId, onCreated, onNotify }) {
  const [values, setValues] = useState({ source: "", amount: "", income_type: "Salary", date: todayLocalDate(), description: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    const amount = Number(values.amount);
    const commonError = validateCommonForm(values, amount);
    if (!values.source.trim()) return setError("Enter an income source.");
    if (commonError) return setError(commonError);

    setSubmitting(true);
    try {
      await addIncome({ ...values, user_id: userId, amount });
      onNotify?.({ type: "success", message: "Income added successfully." });
      setValues({ source: "", amount: "", income_type: "Salary", date: todayLocalDate(), description: "" });
      await onCreated();
    } catch (requestError) {
      onNotify?.({ type: "error", message: "Unable to add income. Check the form and backend, then retry." });
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
      <div className="p3-form-actions"><span className="p3-required-hint">* Required fields</span><button className="p3-primary-button" type="submit" disabled={submitting || !userId}>{submitting ? "Saving…" : "Add income"}<Icon name="arrow" /></button></div>
    </form>
  );
}

function ExpenseForm({ userId, onCreated, onNotify }) {
  const [values, setValues] = useState({ category: "Food", amount: "", expense_type: "Essential", date: todayLocalDate(), description: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    const amount = Number(values.amount);
    const commonError = validateCommonForm(values, amount);
    if (!values.category) return setError("Choose an expense category.");
    if (!values.expense_type) return setError("Choose an expense type.");
    if (commonError) return setError(commonError);

    setSubmitting(true);
    try {
      await addExpense({ ...values, user_id: userId, amount });
      onNotify?.({ type: "success", message: "Expense added successfully." });
      setValues({ category: "Food", amount: "", expense_type: "Essential", date: todayLocalDate(), description: "" });
      await onCreated();
    } catch (requestError) {
      onNotify?.({ type: "error", message: "Unable to add expense. Check the form and backend, then retry." });
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
      <div className="p3-form-actions"><span className="p3-required-hint">* Required fields</span><button className="p3-primary-button" type="submit" disabled={submitting || !userId}>{submitting ? "Saving…" : "Add expense"}<Icon name="arrow" /></button></div>
    </form>
  );
}

function IncomePage({ userId, summary, records, onCreated, onNotify }) {
  const transactions = useTransactionRows(records, []);
  const sourcesCount = new Set(records.map((record) => record.source)).size;
  return (
    <>
      <PageTitle eyebrow="INCOME MANAGEMENT" title="Income" subtitle="Record income sources and review your history." />
      <section className="metrics-grid phase3-management-metrics" aria-label="Income summary">
        <MetricCard label="Income this period" value={formatMoney(summary.total_income)} detail={formatPeriod(summary.period)} icon="income" tone="green" />
        <MetricCard label="Income records" value={records.length} detail="All recorded sources" icon="transactions" tone="blue" />
        <MetricCard label="Income sources" value={sourcesCount} detail="Distinct sources in your history" icon="analytics" tone="mint" />
      </section>
      <section className="p3-dashboard-grid p3-management-grid">
        <Panel title="Add income" kicker="NEW RECORD"><IncomeForm userId={userId} onCreated={onCreated} onNotify={onNotify} /></Panel>
        <Panel title="Income history" kicker={`${records.length} RECORD${records.length === 1 ? "" : "S"}`} className="p3-management-list-panel"><TransactionsTable rows={transactions} emptyMessage="No income records yet. Add your first income above." /></Panel>
      </section>
    </>
  );
}

function ExpensesPage({ userId, summary, records, onCreated, onNotify }) {
  const transactions = useTransactionRows([], records);
  return (
    <>
      <PageTitle eyebrow="EXPENSE MANAGEMENT" title="Expenses" subtitle="Track spending by category and type." />
      <section className="metrics-grid phase3-management-metrics" aria-label="Expense summary">
        <MetricCard label="Expenses this period" value={formatMoney(summary.total_expenses)} detail={formatPeriod(summary.period)} icon="expenses" tone="lavender" />
        <MetricCard label="Essential expenses" value={formatMoney(summary.essential_expenses)} detail={`${Number(summary.essential_expense_ratio).toFixed(1)}% of expenses`} icon="health" tone="green" />
        <MetricCard label="Non-essential expenses" value={formatMoney(summary.non_essential_expenses)} detail="From the dashboard API" icon="calendar" tone="sand" />
      </section>
      <section className="p3-dashboard-grid p3-management-grid">
        <Panel title="Add expense" kicker="NEW RECORD"><ExpenseForm userId={userId} onCreated={onCreated} onNotify={onNotify} /></Panel>
        <Panel title="Expense history" kicker={`${records.length} RECORD${records.length === 1 ? "" : "S"}`} className="p3-management-list-panel"><TransactionsTable rows={transactions} emptyMessage="No expenses recorded yet. Add your first expense above." /></Panel>
      </section>
    </>
  );
}

function TransactionsPage({ rows, filters, onChange, loading, error, onRetry }) {
  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 8 }, (_, index) => String(currentYear - index));
  const displayedRows = useMemo(() => {
    const query = filters.query.trim().toLocaleLowerCase();
    return rows
      .filter((row) => !query || `${row.label} ${row.categoryLabel} ${row.subtype} ${row.recordType}`.toLocaleLowerCase().includes(query))
      .filter((row) => !filters.dateFrom || row.date >= filters.dateFrom)
      .filter((row) => !filters.dateTo || row.date <= filters.dateTo)
      .sort((left, right) => {
        if (filters.sort === "oldest") return left.date.localeCompare(right.date);
        if (filters.sort === "amount-high") return Math.abs(right.signedAmount) - Math.abs(left.signedAmount);
        if (filters.sort === "amount-low") return Math.abs(left.signedAmount) - Math.abs(right.signedAmount);
        return right.date.localeCompare(left.date);
      });
  }, [rows, filters.query, filters.dateFrom, filters.dateTo, filters.sort]);
  const invalidDateRange = filters.dateFrom && filters.dateTo && filters.dateFrom > filters.dateTo;
  return (
    <>
      <PageTitle eyebrow="TRANSACTION HISTORY" title="Transactions" subtitle="Search, filter, and sort the income and expense records returned by the API." />
      <Panel title="Filter records" kicker="REFINE YOUR VIEW" className="p3-filter-panel">
        <div className="p3-filters">
          <label>Search records<div className="p3-filter-search"><Icon name="search" /><input value={filters.query} onChange={(event) => onChange("query", event.target.value)} placeholder="Description, source, category" /></div></label>
          <label>Record type<select value={filters.kind} onChange={(event) => onChange("kind", event.target.value)}><option value="all">All records</option><option value="income">Income</option><option value="expense">Expenses</option></select></label>
          <label>Category<select value={filters.category} onChange={(event) => onChange("category", event.target.value)} disabled={filters.kind === "income"}><option value="">All categories</option>{EXPENSE_CATEGORIES.map((category) => <option key={category}>{category}</option>)}</select></label>
          <label>Month<select value={filters.month} onChange={(event) => onChange("month", event.target.value)}><option value="">All months</option>{Array.from({ length: 12 }, (_, index) => <option key={index + 1} value={String(index + 1)}>{new Intl.DateTimeFormat("en-IN", { month: "long" }).format(new Date(2020, index, 1))}</option>)}</select></label>
          <label>Year<select value={filters.year} onChange={(event) => onChange("year", event.target.value)}><option value="">All years</option>{years.map((year) => <option key={year}>{year}</option>)}</select></label>
          <label>From date<input type="date" value={filters.dateFrom} onChange={(event) => onChange("dateFrom", event.target.value)} /></label>
          <label>To date<input type="date" value={filters.dateTo} onChange={(event) => onChange("dateTo", event.target.value)} /></label>
          <label>Sort by<select value={filters.sort} onChange={(event) => onChange("sort", event.target.value)}><option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="amount-high">Amount: high to low</option><option value="amount-low">Amount: low to high</option></select></label>
        </div>
        <button className="p3-clear-filters" type="button" onClick={() => ["query", "kind", "category", "month", "year", "dateFrom", "dateTo", "sort"].forEach((field) => onChange(field, field === "kind" ? "all" : field === "sort" ? "newest" : ""))}>Clear filters</button>
      </Panel>
      <Panel title="All transactions" kicker={loading ? "UPDATING" : `${displayedRows.length} MATCHING RECORD${displayedRows.length === 1 ? "" : "S"}`}>
        {error && <p className="p3-inline-error" role="alert">{error} <button type="button" className="p3-inline-retry" onClick={onRetry}>Retry</button></p>}
        {invalidDateRange && <p className="p3-inline-error" role="alert">The start date must be on or before the end date.</p>}
        {loading ? <div className="p3-inline-loading" role="status">Loading transactions…</div> : <TransactionsTable rows={invalidDateRange ? [] : displayedRows} emptyTitle="No matching transactions" emptyMessage="No transactions match these filters. Try changing the search or date range." />}
      </Panel>
    </>
  );
}

function AnalyticsPage({ summary, monthly, categories, periodSelection, onPeriodChange }) {
  const average = (field) => monthly.length ? monthly.reduce((sum, row) => sum + Number(row[field] || 0), 0) / monthly.length : null;
  const highestCategory = Object.entries(categories).sort((left, right) => Number(right[1]) - Number(left[1]))[0];
  return (
    <>
      <PageTitle eyebrow="VISUAL ANALYTICS" title="Analytics" subtitle="Explore monthly cash flow and spending patterns from your records." action={<PeriodSelector value={periodSelection} onChange={onPeriodChange} />} />
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

function ProgressMetric({ label, value, description, tone = "green" }) {
  const amount = Number(value) || 0;
  const width = Math.min(100, Math.max(0, amount));
  return (
    <div className="p3-progress-metric">
      <div className="p3-progress-copy"><span>{label}</span><strong>{amount.toFixed(1)}%</strong></div>
      <div className="p3-progress-track" role="img" aria-label={`${label}: ${amount.toFixed(1)} percent`}><span className={`p3-progress-fill progress-${tone}`} style={{ width: `${width}%` }} /></div>
      {description && <small>{description}</small>}
    </div>
  );
}

function HealthPage({ summary, periodSelection, onPeriodChange }) {
  return (
    <>
      <PageTitle eyebrow="FINANCIAL HEALTH" title="Your financial health" subtitle={`Status and indicators returned by the backend for ${formatPeriod(summary.period)}.`} action={<PeriodSelector value={periodSelection} onChange={onPeriodChange} />} />
      <HealthSummary summary={summary} />
      <section className="metrics-grid phase3-health-metrics-grid">
        <MetricCard label={Number(summary.surplus) < 0 ? "Monthly deficit" : "Monthly surplus"} value={formatMoney(Math.abs(Number(summary.surplus)))} detail={Number(summary.surplus) < 0 ? "Deficit" : "Surplus"} icon="calendar" tone={Number(summary.surplus) < 0 ? "sand" : "green"} />
        <MetricCard label="Savings rate" value={`${Number(summary.savings_rate).toFixed(1)}%`} detail="Returned by the financial engine" icon="analytics" tone="blue" />
        <MetricCard label="Expense ratio" value={`${Number(summary.expense_ratio).toFixed(1)}%`} detail="Expenses relative to income" icon="expenses" tone="lavender" />
        <MetricCard label="Deficit amount" value={formatMoney(summary.deficit)} detail="Zero when there is no deficit" icon="health" tone="sand" />
      </section>
      <Panel title="Financial ratios" kicker="FROM THE FINANCIAL ENGINE" className="p3-ratio-panel">
        <div className="p3-ratio-grid">
          <ProgressMetric label="Savings rate" value={summary.savings_rate} description="Share of income remaining after expenses." tone="green" />
          <ProgressMetric label="Expense ratio" value={summary.expense_ratio} description="Expenses as a share of income." tone="gold" />
          <ProgressMetric label="Essential expense ratio" value={summary.essential_expense_ratio} description="Essential expenses as a share of all expenses." tone="blue" />
        </div>
      </Panel>
    </>
  );
}

function SettingToggle({ label, description, checked, onChange }) {
  return (
    <label className="p3-setting-toggle">
      <span><strong>{label}</strong><small>{description}</small></span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span className="p3-switch" aria-hidden="true" />
    </label>
  );
}

function SettingsPage({ summary, themePreference, onThemeChange, dateFormat, onDateFormatChange, notifications, onNotificationChange }) {
  return (
    <>
      <PageTitle eyebrow="SETTINGS" title="Preferences" subtitle="Choose how FlexiFund looks and how dates are shown on this device." />
      <section className="p3-dashboard-grid p3-settings-grid">
        <Panel title="Profile" kicker="READ-ONLY DEMO">
          <dl className="p3-settings-list"><div><dt>Name</dt><dd>{summary.user_name || "FlexiFund Demo"}</dd></div><div><dt>Email</dt><dd>{summary.user_email || "Not available through the current API"}</dd></div><div><dt>User ID</dt><dd>{summary.user_id}</dd></div><div><dt>Account</dt><dd>Fictional sample records</dd></div></dl>
          <p className="p3-settings-note">Profile details are read-only. The current API does not provide email or profile editing.</p>
        </Panel>
        <Panel title="Preferences" kicker="SAVED LOCALLY">
          <div className="p3-setting-fields">
            <label>Currency display<select value="INR" disabled><option value="INR">INR · Indian rupee</option></select><small>Financial values are returned in INR. Currency conversion is not available.</small></label>
            <label>Date format<select value={dateFormat} onChange={(event) => onDateFormatChange(event.target.value)}><option value="short">20 Nov 2026 · Short</option><option value="numeric">20/11/2026 · Numeric</option><option value="iso">2026-11-20 · ISO</option></select></label>
            <label>Appearance<select value={themePreference} onChange={(event) => onThemeChange(event.target.value)}><option value="system">System preference</option><option value="light">Light mode</option><option value="dark">Dark mode</option></select></label>
          </div>
          <p className="p3-settings-note">Preferences are stored in this browser only. They are not sent to the Flask server.</p>
        </Panel>
        <Panel title="Notification preferences" kicker="THIS DEVICE" className="p3-notification-settings">
          <div className="p3-setting-toggle-list">
            <SettingToggle label="Financial alerts" description="Show account health notices in this interface." checked={notifications.financial} onChange={(value) => onNotificationChange("financial", value)} />
            <SettingToggle label="Spending alerts" description="Show spending notices in this interface." checked={notifications.spending} onChange={(value) => onNotificationChange("spending", value)} />
            <SettingToggle label="Monthly summaries" description="Show monthly summary notifications in this interface." checked={notifications.monthly} onChange={(value) => onNotificationChange("monthly", value)} />
          </div>
          <p className="p3-settings-note">These switches save local preferences. The backend does not send notifications.</p>
        </Panel>
      </section>
    </>
  );
}

function readPreference(key, fallback) {
  try {
    return window.localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function writePreference(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Keep the current session usable when browser storage is unavailable.
  }
}

function periodQuery(selection) {
  const today = new Date();
  if (selection === "this-year") return { year: today.getFullYear() };
  const selectedDate = selection === "last-month"
    ? new Date(today.getFullYear(), today.getMonth() - 1, 1)
    : today;
  return { month: selectedDate.getMonth() + 1, year: selectedDate.getFullYear() };
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
  const [periodSelection, setPeriodSelection] = useState(() => readPreference("flexifund-period", "this-month"));
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => readPreference("flexifund-sidebar-collapsed", "false") === "true");
  const [themePreference, setThemePreference] = useState(() => {
    const saved = readPreference("flexifund-theme", "system");
    return ["system", "light", "dark"].includes(saved) ? saved : "system";
  });
  const [systemPrefersDark, setSystemPrefersDark] = useState(() => window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false);
  const [dateFormat, setDateFormat] = useState(() => readPreference("flexifund-date-format", "short"));
  const [notifications, setNotifications] = useState(() => {
    try {
      return { financial: true, spending: true, monthly: true, ...JSON.parse(readPreference("flexifund-notifications", "{}")) };
    } catch {
      return { financial: true, spending: true, monthly: true };
    }
  });
  const [globalSearch, setGlobalSearch] = useState("");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const [transactionFilters, setTransactionFilters] = useState({ kind: "all", category: "", month: "", year: "", query: "", dateFrom: "", dateTo: "", sort: "newest" });
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [transactionsLoading, setTransactionsLoading] = useState(false);
  const [transactionsError, setTransactionsError] = useState("");
  const [transactionRevision, setTransactionRevision] = useState(0);
  const firstLoad = useRef(true);

  const resolvedTheme = themePreference === "system" ? (systemPrefersDark ? "dark" : "light") : themePreference;

  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!media) return undefined;
    const onChange = (event) => setSystemPrefersDark(event.matches);
    if (media.addEventListener) media.addEventListener("change", onChange);
    else media.addListener?.(onChange);
    return () => {
      if (media.removeEventListener) media.removeEventListener("change", onChange);
      else media.removeListener?.(onChange);
    };
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme;
    writePreference("flexifund-theme", themePreference);
  }, [resolvedTheme, themePreference]);

  useEffect(() => {
    writePreference("flexifund-sidebar-collapsed", String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  useEffect(() => {
    writePreference("flexifund-date-format", dateFormat);
  }, [dateFormat]);

  useEffect(() => {
    writePreference("flexifund-notifications", JSON.stringify(notifications));
  }, [notifications]);

  useEffect(() => {
    writePreference("flexifund-period", periodSelection);
  }, [periodSelection]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(null), 3600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const loadDashboardData = useCallback(async (initialLoad = false) => {
    if (initialLoad) setLoading(true);
    else setRefreshing(true);
    setError("");
    try {
      const dashboardResponse = await fetchDashboard(periodQuery(periodSelection));
      const nextSummary = dashboardResponse?.data;
      if (!nextSummary) throw new Error("The dashboard response was incomplete.");
      const userParams = { user_id: nextSummary.user_id };
      const periodParams = { ...userParams, month: nextSummary.period.month || undefined, year: nextSummary.period.year };
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
  }, [periodSelection]);

  useEffect(() => {
    const initialLoad = firstLoad.current;
    firstLoad.current = false;
    void loadDashboardData(initialLoad);
  }, [loadDashboardData]);

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

  function navigate(page) {
    setActivePage(page);
    setNotificationsOpen(false);
  }

  function updateTransactionFilter(field, value) {
    setTransactionFilters((current) => ({
      ...current,
      [field]: value,
      ...(field === "kind" && value === "income" ? { category: "" } : {}),
    }));
  }

  function submitGlobalSearch(event) {
    event.preventDefault();
    setTransactionFilters({ kind: "all", category: "", month: "", year: "", query: globalSearch, dateFrom: "", dateTo: "", sort: "newest" });
    navigate("transactions");
  }

  async function handleRecordCreated() {
    await loadDashboardData(false);
    setTransactionRevision((current) => current + 1);
  }

  function updateNotification(field, value) {
    setNotifications((current) => ({ ...current, [field]: value }));
    setToast({ type: "success", message: "Notification preference saved on this device." });
  }

  function setTheme(value) {
    setThemePreference(value);
    setToast({ type: "success", message: "Appearance preference saved." });
  }

  function renderCurrentPage() {
    if (!summary) return null;
    switch (activePage) {
      case "transactions":
        return <TransactionsPage rows={filteredTransactions} filters={transactionFilters} onChange={updateTransactionFilter} loading={transactionsLoading} error={transactionsError} onRetry={() => setTransactionRevision((current) => current + 1)} />;
      case "income":
        return <IncomePage userId={summary.user_id} summary={summary} records={incomeRecords} onCreated={handleRecordCreated} onNotify={setToast} />;
      case "expenses":
        return <ExpensesPage userId={summary.user_id} summary={summary} records={expenseRecords} onCreated={handleRecordCreated} onNotify={setToast} />;
      case "analytics":
        return <AnalyticsPage summary={summary} monthly={monthly} categories={categories} periodSelection={periodSelection} onPeriodChange={setPeriodSelection} />;
      case "health":
        return <HealthPage summary={summary} periodSelection={periodSelection} onPeriodChange={setPeriodSelection} />;
      case "settings":
        return <SettingsPage summary={summary} themePreference={themePreference} onThemeChange={setTheme} dateFormat={dateFormat} onDateFormatChange={setDateFormat} notifications={notifications} onNotificationChange={updateNotification} />;
      default:
        return <DashboardPage summary={summary} monthly={monthly} categories={categories} transactions={transactions} demo={demo} onNavigate={navigate} periodSelection={periodSelection} onPeriodChange={setPeriodSelection} />;
    }
  }

  return (
    <div className={`app-shell phase3-shell${sidebarCollapsed ? " sidebar-collapsed" : ""}`}>
      <Sidebar active={activePage} onNavigate={navigate} userName={summary?.user_name} collapsed={sidebarCollapsed} onToggleCollapse={() => setSidebarCollapsed((current) => !current)} />
      <main className="main-content phase3-main">
        <Topbar
          pageTitle={pageTitle}
          loading={loading}
          refreshing={refreshing}
          error={error}
          userName={summary?.user_name}
          theme={resolvedTheme}
          onToggleTheme={() => setThemePreference(resolvedTheme === "dark" ? "light" : "dark")}
          search={globalSearch}
          onSearchChange={setGlobalSearch}
          onSearchSubmit={submitGlobalSearch}
          notificationsOpen={notificationsOpen}
          onToggleNotifications={() => setNotificationsOpen((current) => !current)}
          onNavigate={navigate}
        />
        <div className="page-content phase3-page-content">
          {error && summary && <div className="p3-refresh-error" role="status">Showing the last loaded data. {error} <button type="button" onClick={() => loadDashboardData(false)}>Retry</button></div>}
          {loading && !summary ? <LoadingState /> : error && !summary ? <ConnectionState onRetry={() => loadDashboardData(true)} /> : renderCurrentPage()}
        </div>
      </main>
      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}

export default App;
