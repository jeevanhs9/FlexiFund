import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  addExpense,
  addIncome,
  clearAssistantHistory,
  compareFinancialScenario,
  createFinancialGoal,
  deleteFinancialGoal,
  fetchDashboard,
  fetchExpenseCategories,
  fetchExpenses,
  fetchIncome,
  fetchIntelligenceOverview,
  fetchMonthlySummary,
  fetchRiderDemo,
  fetchPersonalizationInsights,
  fetchAssistantHistory,
  fetchCurrentUser,
  loginAccount,
  logoutAccount,
  runWhatIfScenario,
  registerAccount,
  sendAssistantQuestion,
  updateFinancialGoal,
} from "./api.js";
import {
  ExpenseComparison,
  ExpenseDonutChart,
  ForecastChart,
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
    assistant: <><path d="M5 5.5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-7l-5 3v-3H5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2Z" /><path d="m12 8 .7 2.1 2.1.7-2.1.7L12 13.6l-.7-2.1-2.1-.7 2.1-.7L12 8Z" /></>,
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
  { id: "personalization", label: "Personalization", icon: "analytics" },
  { id: "assistant", label: "AI Assistant", icon: "assistant" },
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
          <span><strong>{userName || "FlexiFund"}</strong><small>Private account</small></span>
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
  onLogout,
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
        <span className="p3-demo-chip"><span />PRIVATE ACCOUNT</span>
        <button className="p3-icon-button" type="button" onClick={onToggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`} title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}><Icon name={theme === "dark" ? "sun" : "moon"} /></button>
        <div className="p3-notification-wrap">
          <button className="p3-icon-button" type="button" onClick={onToggleNotifications} aria-label="Notifications" aria-expanded={notificationsOpen} title="Notifications"><Icon name="bell" /></button>
          {notificationsOpen && <div className="p3-notification-popover" role="status"><strong>No new notifications</strong><span>Notification preferences are managed on this device.</span><button type="button" onClick={() => onNavigate("settings")}>Manage preferences</button></div>}
        </div>
        <button className="p3-profile-button" type="button" onClick={() => onNavigate("settings")} aria-label={`Open ${userName || "FlexiFund"} profile settings`} title="Profile settings">{userName?.[0] || "F"}</button>
        <button className="p3-logout-button" type="button" onClick={onLogout}>Sign out</button>
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

function IntelligencePanels({ intelligence, loading, error, onRetry }) {
  if (loading && !intelligence) return <Panel title="Financial intelligence" kicker="ANALYSIS"><div className="p3-inline-loading">Preparing insights from your transactions…</div></Panel>;
  if (error && !intelligence) return <Panel title="Financial intelligence" kicker="ANALYSIS"><div className="p3-intelligence-error" role="status"><span>{error}</span><button type="button" onClick={onRetry}>Retry</button></div></Panel>;
  if (!intelligence) return null;

  const risk = intelligence.risk || {};
  const spending = intelligence.spending || {};
  const forecast = intelligence.forecast || {};
  const expensePrediction = intelligence.expense_prediction || forecast.expense_prediction || {};
  const savings = intelligence.savings || {};
  const recommendations = intelligence.recommendations || [];
  const history = intelligence.features?.monthly_history || [];
  const category = spending.top_category;
  const anomalies = intelligence.anomalies || [];
  const recurring = intelligence.recurring || [];
  return (
    <>
      {error && <div className="p3-intelligence-error" role="status">Showing the last loaded insights. {error} <button type="button" onClick={onRetry}>Retry</button></div>}
      <section className="p3-dashboard-grid p3-intelligence-grid" aria-label="Financial intelligence">
        <Panel title="Financial health score" kicker="EXPLAINABLE RISK INDICATOR">
          {risk.score === null || risk.score === undefined ? <div className="p3-intelligence-empty">{risk.explanation || "Add financial transactions to unlock financial intelligence."}</div> : <>
            <div className="p3-risk-score"><strong>{risk.score}<small>/100</small></strong><span className={`p3-risk-band band-${String(risk.band).toLowerCase().replaceAll(" ", "-")}`}>{risk.band}{risk.coverage_percent < 100 ? " · provisional" : ""}</span></div>
            <div className="p3-risk-meter" role="img" aria-label={`Financial health score ${risk.score} out of 100`}><span style={{ width: `${Math.max(0, Math.min(100, risk.score))}%` }} /></div>
            <p className="p3-intelligence-note">Data coverage: {Number(risk.coverage_percent || 0).toFixed(0)}% of weighted score components. {risk.explanation}</p>
            {!!(risk.positive_factors || []).length && <ul className="p3-factor-list positive">{risk.positive_factors.map((factor) => <li key={factor}>{factor}</li>)}</ul>}
            {!!(risk.negative_factors || []).length && <ul className="p3-factor-list negative">{risk.negative_factors.map((factor) => <li key={factor}>{factor}</li>)}</ul>}
          </>}
        </Panel>
        <Panel title="Cash-flow forecast" kicker={forecast.available ? `${forecast.historical_months} COMPLETED MONTHS · ${forecast.forecast_month.toUpperCase()}` : "ACTUALS AND ESTIMATE KEPT SEPARATE"}>
          <ForecastChart rows={history} forecast={forecast} />
          <div className="p3-forecast-values">
            <div><span>Predicted income</span><strong>{forecast.available ? formatMoney(forecast.predicted_income) : "Unavailable"}</strong></div>
            <div><span>{expensePrediction.available ? "Predicted expenses · validated model" : "Predicted expenses"}</span><strong>{forecast.available ? formatMoney(forecast.predicted_expenses) : "Unavailable"}</strong></div>
            <div><span>Predicted savings</span><strong className={savings.potential_negative_cash_flow ? "negative-value" : ""}>{forecast.available ? formatMoney(savings.predicted_next_month_savings) : "Unavailable"}</strong></div>
            <div><span>Current savings rate</span><strong>{savings.current_savings_rate === null || savings.current_savings_rate === undefined ? "—" : `${Number(savings.current_savings_rate).toFixed(1)}%`}</strong></div>
            <div><span>Predicted savings rate</span><strong>{savings.predicted_savings_rate === null || savings.predicted_savings_rate === undefined ? "—" : `${Number(savings.predicted_savings_rate).toFixed(1)}%`}</strong></div>
          </div>
          <p className="p3-intelligence-note">{forecast.available ? `${forecast.method?.replaceAll("_", " ")} using ${forecast.inputs?.join(", ") || `${forecast.historical_months} completed months`}. ${forecast.explanation}` : forecast.explanation}</p>
          {expensePrediction.available && <p className="p3-intelligence-note">Expense model: {expensePrediction.selected_model?.replaceAll("_", " ")}. Chronological validation · MAE {formatMoney(expensePrediction.evaluation?.mae)} · RMSE {formatMoney(expensePrediction.evaluation?.rmse)}{expensePrediction.evaluation?.r2 == null ? " · R² unavailable for this holdout" : ` · R² ${Number(expensePrediction.evaluation.r2).toFixed(3)}`}. Actual bars are recorded transactions; the outlined next-month bar is projected.</p>}
          {savings.potential_negative_cash_flow && <p className="p3-intelligence-alert">Potential negative cash flow in {forecast.forecast_month} based on the statistical estimate.</p>}
        </Panel>
      </section>
      <section className="p3-dashboard-grid p3-intelligence-grid">
        <Panel title="Smart recommendations" kicker={`${recommendations.length} DATA-DRIVEN ACTION${recommendations.length === 1 ? "" : "S"}`}>
          {recommendations.length ? <ul className="p3-recommendation-list">{recommendations.slice(0, 5).map((item, index) => <li key={`${item.title}-${index}`}><span className={`p3-priority priority-${item.priority.toLowerCase()}`}>{item.priority}</span><div><strong>{item.title}</strong><p>{item.message}</p><small>{item.basis}</small></div></li>)}</ul> : <div className="p3-intelligence-empty">No recommendations can be derived from the selected records.</div>}
        </Panel>
        <Panel title="Spending signals" kicker="OBSERVED TRANSACTIONS">
          <div className="p3-signal-grid">
            <div><span>Top category</span><strong>{category?.category || "No category data"}</strong>{category && <small>{formatMoney(category.amount)} · {Number(category.percentage).toFixed(1)}% of expenses</small>}</div>
            <div><span>Overspending</span><strong>{spending.overspending?.length ? `${spending.overspending.length} category alert${spending.overspending.length === 1 ? "" : "s"}` : "None detected"}</strong><small>Requires at least three prior observed months</small></div>
            <div><span>Unusual spending</span><strong>{anomalies.length ? `${anomalies.length} alert${anomalies.length === 1 ? "" : "s"}` : "None detected"}</strong><small>Statistical flags, not fraud findings</small></div>
            <div><span>Recurring expenses</span><strong>{recurring.length || "None detected"}</strong><small>{recurring.slice(0, 2).map((item) => `${item.name} · ${formatMoney(item.average_amount)}`).join("; ") || "Requires at least three similar dated expenses"}</small></div>
            <div><span>Emergency fund</span><strong>{intelligence.emergency_fund?.current_balance === null ? "Balance not provided" : formatMoney(intelligence.emergency_fund.current_balance)}</strong><small>{intelligence.emergency_fund?.recommended_minimum === null ? "Add essential expenses to estimate a target." : `${intelligence.emergency_fund.provisional ? "Preliminary estimate" : "Estimated target"} from ${intelligence.emergency_fund.basis_months} observed month(s) · 3-month: ${formatMoney(intelligence.emergency_fund.recommended_minimum)} · 6-month: ${formatMoney(intelligence.emergency_fund.recommended_target)}`}</small></div>
            <div><span>Savings trend</span><strong>{savings.savings_trend?.replaceAll("_", " ") || "Insufficient history"}</strong><small>{savings.average_monthly_savings === null ? "No monthly average available" : `Observed monthly average ${formatMoney(savings.average_monthly_savings)}`}</small></div>
          </div>
          {!!(intelligence.data_quality?.warnings || []).length && <p className="p3-intelligence-note">Data quality: {intelligence.data_quality.warnings.join(" ")}</p>}
        </Panel>
      </section>
    </>
  );
}

const ASSISTANT_PROMPTS = [
  "How am I doing financially?",
  "Where did I spend the most?",
  "Why did my expenses increase?",
  "Can I reach my savings goal?",
  "What are my biggest financial risks?",
  "What will my expenses look like next month?",
];

function splitStoredAssistantMessage(message) {
  const factMarker = "[FACTUAL CALCULATION]\n";
  const explanationMarker = "\n\n[AI-GENERATED EXPLANATION]\n";
  if (!message?.startsWith(factMarker)) return { factual: null, explanation: null, text: message || "" };
  const body = message.slice(factMarker.length);
  const separator = body.indexOf(explanationMarker);
  return separator < 0
    ? { factual: body, explanation: null, text: null }
    : { factual: body.slice(0, separator), explanation: body.slice(separator + explanationMarker.length), text: null };
}

function AssistantPage({ initialQuestion, onLogout }) {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState(initialQuestion || "");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [sending, setSending] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState("");
  const messageEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    setDraft(initialQuestion || "");
  }, [initialQuestion]);

  useEffect(() => {
    let cancelled = false;
    fetchAssistantHistory()
      .then((response) => {
        if (cancelled) return;
        setConversationId(response?.data?.conversation_id || null);
        setMessages(response?.data?.messages || []);
      })
      .catch((requestError) => {
        if (cancelled) return;
        if (requestError.status === 401) void onLogout();
        else setError(requestError.message || "Unable to load conversation history.");
      })
      .finally(() => { if (!cancelled) setLoadingHistory(false); });
    return () => { cancelled = true; };
  }, [onLogout]);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  async function submitQuestion(event) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || sending) return;
    setError("");
    setSending(true);
    try {
      const response = await sendAssistantQuestion(question, conversationId);
      const data = response?.data;
      if (!data?.conversation_id || !Array.isArray(data.messages)) throw new Error("The assistant response was incomplete.");
      setConversationId(data.conversation_id);
      const assistantEntry = data.messages.find((item) => item.role === "assistant");
      const userEntry = data.messages.find((item) => item.role === "user");
      setMessages((current) => [...current, ...(userEntry ? [userEntry] : []), ...(assistantEntry ? [{ ...assistantEntry, aiStatus: data.ai_status }] : [])]);
      setDraft("");
    } catch (requestError) {
      if (requestError.status === 401) void onLogout();
      else setError(requestError.message || "The assistant could not answer. Please try again.");
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  async function clearConversation() {
    setClearing(true);
    setError("");
    try {
      await clearAssistantHistory();
      setConversationId(null);
      setMessages([]);
    } catch (requestError) {
      if (requestError.status === 401) void onLogout();
      else setError(requestError.message || "Conversation history could not be cleared.");
    } finally {
      setClearing(false);
    }
  }

  function choosePrompt(prompt) {
    setDraft(prompt);
    inputRef.current?.focus();
  }

  return (
    <section className="assistant-page" aria-label="FlexiFund AI financial assistant">
      <PageTitle
        eyebrow="FLEXIFUND · PERSONAL FINANCE"
        title="AI Financial Assistant"
        subtitle="Ask about your recorded cash flow, spending, savings, and financial health."
        action={<button className="assistant-clear-button" type="button" onClick={clearConversation} disabled={clearing || loadingHistory || (!messages.length && !conversationId)}>{clearing ? "Clearing…" : "Clear conversation"}</button>}
      />
      <div className="assistant-workspace">
        <div className="assistant-privacy-note"><strong>Private, data-backed answers</strong><span>FlexiFund calculates the facts from your account. If an AI provider is configured, it receives your question, up to eight recent chat messages, and a compact summary—not transaction descriptions or account credentials.</span></div>
        {!!error && <div className="assistant-error" role="alert">{error}</div>}
        <div className="assistant-chat" aria-label="Conversation with the FlexiFund assistant">
          <div className="assistant-message-list" role="log" aria-live="polite" aria-relevant="additions text" aria-label="Conversation messages">
            {loadingHistory && <div className="assistant-empty-state" role="status">Loading your conversation…</div>}
            {!loadingHistory && messages.length === 0 && (
              <div className="assistant-empty-state">
                <span className="assistant-sparkle" aria-hidden="true"><Icon name="assistant" /></span>
                <h2>Your financial picture, explained</h2>
                <p>Ask a question to get a calculation from your records and, when configured, a plain-language AI explanation.</p>
                <div className="assistant-prompts" aria-label="Suggested questions">
                  {ASSISTANT_PROMPTS.map((prompt) => <button key={prompt} type="button" onClick={() => choosePrompt(prompt)}>{prompt}</button>)}
                </div>
              </div>
            )}
            {messages.map((item) => {
              const assistant = item.role === "assistant";
              const parsed = assistant ? splitStoredAssistantMessage(item.message) : { text: item.message };
              return (
                <article className={`assistant-message ${assistant ? "assistant-message-bot" : "assistant-message-user"}`} key={item.id || `${item.role}-${item.timestamp}`}>
                  <div className="assistant-avatar" aria-hidden="true">{assistant ? "F" : "You"}</div>
                  <div className="assistant-message-body">
                    <div className="assistant-message-meta"><strong>{assistant ? "FlexiFund assistant" : "You"}</strong><time dateTime={item.timestamp}>{item.timestamp ? new Date(item.timestamp).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "Just now"}</time></div>
                    {assistant && parsed.factual !== null ? <>
                      <div className="assistant-answer-section"><span>Factual calculation</span><p>{parsed.factual}</p></div>
                      {parsed.explanation && <div className="assistant-answer-section assistant-ai-section"><span>AI-generated explanation</span><p>{parsed.explanation}</p></div>}
                    </> : <p className="assistant-message-text">{parsed.text}</p>}
                    {assistant && item.aiStatus && item.aiStatus !== "available" && <small className="assistant-fallback-note">AI explanation unavailable; factual results are calculated by FlexiFund.</small>}
                  </div>
                </article>
              );
            })}
            {sending && <div className="assistant-typing" role="status" aria-live="polite"><span aria-hidden="true"><i /><i /><i /></span>Checking your recorded data…</div>}
            <div ref={messageEndRef} />
          </div>
          <form className="assistant-composer" onSubmit={submitQuestion}>
            <label htmlFor="assistant-question">Your question</label>
            <textarea id="assistant-question" ref={inputRef} value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={2000} rows={3} placeholder="For example, where did I spend the most this month?" disabled={loadingHistory || sending} />
            <div className="assistant-composer-footer"><span>{draft.length}/2000 · Your chat is saved to this account.</span><button type="submit" disabled={loadingHistory || sending || !draft.trim()}>{sending ? "Working…" : "Send question"}<span aria-hidden="true">↗</span></button></div>
          </form>
        </div>
        <p className="assistant-disclaimer">FlexiFund provides budgeting insights from recorded transactions, not professional financial advice. Forecasts are estimates and are only shown when enough history exists.</p>
      </div>
    </section>
  );
}

function AssistantInvite({ onAsk }) {
  return (
    <section className="assistant-invite" aria-labelledby="assistant-invite-title">
      <div className="assistant-invite-mark"><Icon name="assistant" /></div>
      <div className="assistant-invite-copy"><span>YOUR DATA, IN PLAIN LANGUAGE</span><h2 id="assistant-invite-title">Ask FlexiFund AI</h2><p>Get a clear explanation of your spending, savings, and financial outlook.</p></div>
      <div className="assistant-invite-actions"><button type="button" onClick={() => onAsk("")}>Open assistant <span aria-hidden="true">↗</span></button><button type="button" onClick={() => onAsk("How am I doing financially?")}>Ask how I'm doing</button></div>
    </section>
  );
}

function PersonalizationPreview({ data, loading, error, onNavigate }) {
  const firstGoal = data?.goals?.goals?.find((goal) => goal.status === "active");
  const firstAction = data?.recommendations?.recommendations?.[0];
  return (
    <Panel title="Personal financial pattern" kicker="ADAPTIVE INSIGHTS" className="p7-dashboard-preview" action={<button type="button" className="p3-link-button" onClick={() => onNavigate("personalization")}>Open <Icon name="arrow" /></button>}>
      {loading ? <p className="p7-muted">Loading insights from your records…</p> : error ? <p className="p7-muted">Personalized insights could not be loaded. Open the section to retry.</p> : <div className="p7-preview-grid">
        <div><span>Behavior</span><strong>{data?.behavior?.behavioral_classification?.label || "Insufficient data"}</strong></div>
        <div><span>Goal progress</span><strong>{firstGoal ? `${firstGoal.name} · ${Number(firstGoal.progress_percent).toFixed(0)}%` : "No active goal"}</strong></div>
        <div className="p7-preview-action"><span>Suggested action</span><strong>{firstAction?.title || "No specific action yet"}</strong><small>{firstAction?.explanation || data?.recommendations?.insufficient_data?.[0] || "Add more records to receive evidence-based actions."}</small></div>
      </div>}
    </Panel>
  );
}

function DashboardPage({ summary, monthly, categories, transactions, demo, intelligence, intelligenceLoading, intelligenceError, personalization, personalizationLoading, personalizationError, onRetryIntelligence, onNavigate, onAskAssistant, periodSelection, onPeriodChange }) {
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
      <PersonalizationPreview data={personalization} loading={personalizationLoading} error={personalizationError} onNavigate={onNavigate} />
      <AssistantInvite onAsk={onAskAssistant} />

      <IntelligencePanels intelligence={intelligence} loading={intelligenceLoading} error={intelligenceError} onRetry={onRetryIntelligence} />

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
      <footer className="p3-footer">FlexiFund · Financial views are limited to your signed-in account.</footer>
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

function IncomeForm({ onCreated, onNotify }) {
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
      await addIncome({ ...values, amount });
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
      <div className="p3-form-actions"><span className="p3-required-hint">* Required fields</span><button className="p3-primary-button" type="submit" disabled={submitting}>{submitting ? "Saving…" : "Add income"}<Icon name="arrow" /></button></div>
    </form>
  );
}

function ExpenseForm({ onCreated, onNotify }) {
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
      await addExpense({ ...values, amount });
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
      <div className="p3-form-actions"><span className="p3-required-hint">* Required fields</span><button className="p3-primary-button" type="submit" disabled={submitting}>{submitting ? "Saving…" : "Add expense"}<Icon name="arrow" /></button></div>
    </form>
  );
}

function IncomePage({ summary, records, onCreated, onNotify }) {
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
        <Panel title="Add income" kicker="NEW RECORD"><IncomeForm onCreated={onCreated} onNotify={onNotify} /></Panel>
        <Panel title="Income history" kicker={`${records.length} RECORD${records.length === 1 ? "" : "S"}`} className="p3-management-list-panel"><TransactionsTable rows={transactions} emptyMessage="No income records yet. Add your first income above." /></Panel>
      </section>
    </>
  );
}

function ExpensesPage({ summary, records, onCreated, onNotify }) {
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
        <Panel title="Add expense" kicker="NEW RECORD"><ExpenseForm onCreated={onCreated} onNotify={onNotify} /></Panel>
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

function localFutureDate(monthsAhead = 3) {
  const value = new Date();
  value.setMonth(value.getMonth() + monthsAhead);
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function tomorrowLocalDate() {
  const value = new Date();
  value.setDate(value.getDate() + 1);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function profileMoney(value) {
  return value === null || value === undefined ? "Not enough data" : formatMoney(value);
}

function GoalEditor({ goal, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [values, setValues] = useState({
    name: goal.name,
    target_amount: String(goal.target_amount),
    current_amount: String(goal.current_amount),
    target_date: goal.target_date,
    priority: goal.priority,
    category: goal.category || "",
  });

  useEffect(() => {
    setValues({
      name: goal.name,
      target_amount: String(goal.target_amount),
      current_amount: String(goal.current_amount),
      target_date: goal.target_date,
      priority: goal.priority,
      category: goal.category || "",
    });
  }, [goal.id, goal.name, goal.target_amount, goal.current_amount, goal.target_date, goal.priority, goal.category]);

  async function save(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await onUpdate(goal.id, {
        name: values.name,
        target_amount: Number(values.target_amount),
        current_amount: Number(values.current_amount),
        target_date: values.target_date,
        priority: values.priority,
        category: values.category.trim() || null,
      });
      setEditing(false);
    } catch (requestError) {
      setError(requestError.message || "Unable to update this goal.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleStatus() {
    setBusy(true);
    setError("");
    try {
      await onUpdate(goal.id, { status: goal.status === "paused" ? "active" : "paused" });
    } catch (requestError) {
      setError(requestError.message || "Unable to update this goal.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Delete “${goal.name}” and its recorded goal adjustments?`)) return;
    setBusy(true);
    setError("");
    try {
      await onDelete(goal.id);
    } catch (requestError) {
      setError(requestError.message || "Unable to delete this goal.");
      setBusy(false);
    }
  }

  return (
    <article className="p7-goal-card">
      <div className="p7-goal-heading">
        <div><span className="p7-kicker">{goal.priority} priority{goal.category ? ` · ${goal.category}` : ""}</span><h3>{goal.name}</h3></div>
        <span className={`p7-status p7-status-${goal.status}`}>{goal.status.replaceAll("_", " ")}</span>
      </div>
      <div className="p7-goal-progress" role="progressbar" aria-label={`${goal.name} progress`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.min(100, Math.max(0, Number(goal.progress_percent) || 0))}><span style={{ width: `${Math.min(100, Math.max(0, Number(goal.progress_percent) || 0))}%` }} /></div>
      <div className="p7-goal-figures"><span>{formatMoney(goal.current_amount)} saved</span><strong>{Number(goal.progress_percent).toFixed(1)}%</strong><span>of {formatMoney(goal.target_amount)}</span></div>
      <div className="p7-goal-details">
        <div><span>Remaining</span><strong>{formatMoney(goal.remaining_amount)}</strong></div>
        <div><span>Needed monthly</span><strong>{formatMoney(goal.required_monthly_savings)}</strong></div>
        <div><span>Target date</span><strong>{formatDate(goal.target_date)}</strong></div>
        <div><span>Projected completion</span><strong>{goal.projected_completion_date ? formatDate(goal.projected_completion_date) : "Not available"}</strong></div>
      </div>
      <p className="p7-goal-feasibility">{goal.feasibility.replaceAll("_", " ")}</p>
      <div className="p7-inline-actions">
        {goal.status !== "completed" && <button type="button" onClick={toggleStatus} disabled={busy}>{goal.status === "paused" ? "Resume" : "Pause"}</button>}
        <button type="button" onClick={() => setEditing((current) => !current)} disabled={busy}>{editing ? "Close editor" : "Edit goal"}</button>
        <button className="p7-danger-button" type="button" onClick={remove} disabled={busy}>Delete</button>
      </div>
      {error && <p className="p7-inline-error" role="alert">{error}</p>}
      {editing && <form className="p7-form p7-goal-edit" onSubmit={save}>
        <label>Goal name<input value={values.name} onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))} maxLength="120" required /></label>
        <label>Target amount<input type="number" min="0.01" step="0.01" value={values.target_amount} onChange={(event) => setValues((current) => ({ ...current, target_amount: event.target.value }))} required /></label>
        <label>Current amount<input type="number" min="0" step="0.01" value={values.current_amount} onChange={(event) => setValues((current) => ({ ...current, current_amount: event.target.value }))} required /></label>
        <label>Target date<input type="date" min={tomorrowLocalDate()} value={values.target_date} onChange={(event) => setValues((current) => ({ ...current, target_date: event.target.value }))} required /></label>
        <label>Priority<select value={values.priority} onChange={(event) => setValues((current) => ({ ...current, priority: event.target.value }))}><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
        <label>Category <span>optional</span><input value={values.category} onChange={(event) => setValues((current) => ({ ...current, category: event.target.value }))} maxLength="60" placeholder="e.g. Emergency fund" /></label>
        {error && <p className="p7-inline-error" role="alert">{error}</p>}
        <button className="p3-primary-button" type="submit" disabled={busy}>{busy ? "Saving…" : "Save changes"}</button>
      </form>}
    </article>
  );
}

function PersonalizationPage({ onLogout, onNotify }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [reloadVersion, setReloadVersion] = useState(0);
  const [goalBusy, setGoalBusy] = useState(false);
  const [scenarioBusy, setScenarioBusy] = useState(false);
  const [scenarioError, setScenarioError] = useState("");
  const [scenarioResult, setScenarioResult] = useState(null);
  const [goalForm, setGoalForm] = useState({ name: "", target_amount: "", current_amount: "0", target_date: localFutureDate(), priority: "medium", category: "" });
  const [scenarioForm, setScenarioForm] = useState({ name: "Spending adjustment", change_type: "reduce_expense_category", category: "Food", amount: "" });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setPageError("");
    fetchPersonalizationInsights()
      .then((response) => { if (!cancelled) setData(response?.data || null); })
      .catch((requestError) => {
        if (cancelled) return;
        if (requestError.status === 401) void onLogout();
        else setPageError(requestError.message || "Unable to load personalized financial insights.");
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [reloadVersion, onLogout]);

  function refresh() {
    setReloadVersion((current) => current + 1);
  }

  async function saveGoal(event) {
    event.preventDefault();
    setGoalBusy(true);
    try {
      await createFinancialGoal({
        name: goalForm.name,
        target_amount: Number(goalForm.target_amount),
        current_amount: Number(goalForm.current_amount || 0),
        target_date: goalForm.target_date,
        priority: goalForm.priority,
        category: goalForm.category.trim() || null,
      });
      setGoalForm({ name: "", target_amount: "", current_amount: "0", target_date: localFutureDate(), priority: "medium", category: "" });
      onNotify?.({ type: "success", message: "Savings goal saved." });
      refresh();
    } catch (requestError) {
      if (requestError.status === 401) void onLogout();
      else onNotify?.({ type: "error", message: requestError.message || "Unable to save this goal." });
    } finally {
      setGoalBusy(false);
    }
  }

  async function editGoal(goalId, changes) {
    const response = await updateFinancialGoal(goalId, changes);
    setData((current) => current ? { ...current, goals: response.data } : current);
    onNotify?.({ type: "success", message: "Savings goal updated." });
  }

  async function removeGoal(goalId) {
    await deleteFinancialGoal(goalId);
    onNotify?.({ type: "success", message: "Savings goal deleted." });
    refresh();
  }

  async function submitScenario(event) {
    event.preventDefault();
    const mode = event.nativeEvent.submitter?.value || "what-if";
    setScenarioBusy(true);
    setScenarioError("");
    setScenarioResult(null);
    const change = { change_type: scenarioForm.change_type, amount: Number(scenarioForm.amount) };
    if (["reduce_expense_category", "decrease_recurring_expense", "add_recurring_expense", "change_budget"].includes(change.change_type)) change.category = scenarioForm.category;
    if (change.change_type === "change_goal_contribution") change.goal_id = Number(scenarioForm.goal_id);
    const operation = mode === "scenario" ? compareFinancialScenario : runWhatIfScenario;
    try {
      const response = await operation({ name: scenarioForm.name, changes: [change] });
      setScenarioResult(response?.data || null);
    } catch (requestError) {
      if (requestError.status === 401) void onLogout();
      else setScenarioError(requestError.message || "Unable to run this scenario.");
    } finally {
      setScenarioBusy(false);
    }
  }

  const profile = data?.profile;
  const behavior = data?.behavior;
  const budget = data?.budget;
  const goals = data?.goals;
  const recommendations = data?.recommendations;
  const goalList = goals?.goals || [];

  if (loading && !data) return <><PageTitle eyebrow="PERSONAL FINANCIAL INTELLIGENCE" title="Personalization" subtitle="Loading profile, goals, and adaptive insights from your account." /><div className="p7-loading" role="status">Calculating from your recorded financial history…</div></>;

  return (
    <section className="p7-page">
      <PageTitle eyebrow="PERSONAL FINANCIAL INTELLIGENCE" title="Personalization" subtitle="Understand your recorded patterns, plan goals, and compare possible changes." action={<button className="p7-refresh-button" type="button" onClick={refresh} disabled={loading}>{loading ? "Refreshing…" : "Refresh insights"}</button>} />
      {pageError && <div className="p7-error" role="alert">{pageError} <button type="button" onClick={refresh}>Retry</button></div>}
      {data && <>
        <div className="p7-note"><strong>Based on your records</strong><span>Personalized metrics use transactions and goal updates in this signed-in account. Behavior labels use deterministic thresholds; no machine-learning model is trained on the available history.</span></div>
        <section className="p7-grid p7-profile-grid" aria-label="Financial profile">
          <Panel title="Financial profile" kicker="OBSERVED HISTORY" className="p7-profile-panel">
            <div className="p7-profile-head"><strong>{behavior?.behavioral_classification?.label || "Insufficient data"}</strong><span>{profile?.period_count || 0} observed transaction month(s)</span></div>
            <div className="p7-metric-grid">
              <div><span>Average monthly income</span><strong>{profileMoney(profile?.average_monthly_income)}</strong></div>
              <div><span>Average monthly expenses</span><strong>{profileMoney(profile?.average_monthly_expenses)}</strong></div>
              <div><span>Average monthly surplus</span><strong>{profileMoney(profile?.average_monthly_surplus)}</strong></div>
              <div><span>Average savings rate</span><strong>{profile?.average_savings_rate_percent == null ? "Not enough data" : `${Number(profile.average_savings_rate_percent).toFixed(1)}%`}</strong></div>
              <div><span>Essential expense ratio</span><strong>{profile?.essential_expense_ratio_percent == null ? "Not enough data" : `${Number(profile.essential_expense_ratio_percent).toFixed(1)}%`}</strong></div>
              <div><span>Discretionary expense ratio</span><strong>{profile?.discretionary_expense_ratio_percent == null ? "Not enough data" : `${Number(profile.discretionary_expense_ratio_percent).toFixed(1)}%`}</strong></div>
              <div><span>Income variation</span><strong>{profile?.income_variation_percent == null ? "Not enough data" : `${Number(profile.income_variation_percent).toFixed(1)}%`}</strong></div>
              <div><span>Spending volatility</span><strong>{profile?.spending_volatility_percent == null ? "Not enough data" : `${Number(profile.spending_volatility_percent).toFixed(1)}%`}</strong></div>
              <div><span>Recurring expense ratio</span><strong>{profile?.recurring_expense_ratio_percent == null ? "Not enough data" : `${Number(profile.recurring_expense_ratio_percent).toFixed(1)}%`}</strong></div>
              <div><span>Positive surplus months</span><strong>{profile?.savings_consistency_percent == null ? "Not enough data" : `${Number(profile.savings_consistency_percent).toFixed(0)}%`}</strong></div>
            </div>
            <div className="p7-risk-strip"><span>Financial health</span><strong>{profile?.financial_health?.score == null ? "Insufficient data" : `${profile.financial_health.score}/100 · ${profile.financial_health.band}`}</strong><small>{profile?.financial_health?.coverage_percent ?? 0}% of weighted indicators supported by history</small></div>
            {profile?.risk_factors?.length > 0 && <ul className="p7-risk-list" aria-label="Recorded risk factors">{profile.risk_factors.map((factor, index) => <li key={`${factor.factor}-${index}`}><strong>{factor.factor}</strong><span>{factor.message}</span></li>)}</ul>}
            {!!profile?.insufficient_data?.length && <p className="p7-muted">{profile.insufficient_data.join(" ")}</p>}
          </Panel>
          <Panel title="Top spending categories" kicker="ALL RECORDED HISTORY">
            {profile?.top_spending_categories?.length ? <ul className="p7-category-list">{profile.top_spending_categories.map((row) => <li key={row.category}><span>{row.category}</span><strong>{formatMoney(row.amount)}</strong><small>{Number(row.share_percent).toFixed(1)}% of recorded expenses</small></li>)}</ul> : <p className="p7-empty">Add expense records to see category totals.</p>}
          </Panel>
        </section>

        <section className="p7-grid p7-analysis-grid" aria-label="Behavior and adaptive budget">
          <Panel title="Behavioral insights" kicker="MEASURED PATTERNS">
            <div className="p7-summary-pair"><div><span>Monthly expense pattern</span><strong>{behavior?.monthly_expense_trend?.status?.replaceAll("_", " ") || "Insufficient data"}</strong></div><div><span>Savings rate trend</span><strong>{behavior?.savings_rate_trend?.status?.replaceAll("_", " ") || "Insufficient data"}</strong></div></div>
            {behavior?.insights?.length ? <ul className="p7-insight-list">{behavior.insights.map((item, index) => <li key={`${item.type}-${index}`}><span className={`p7-severity p7-severity-${item.severity}`}>{item.severity}</span><div><strong>{item.message}</strong><small>{item.supporting_values?.current_amount != null && item.supporting_values?.previous_amount != null ? `${formatMoney(item.supporting_values.previous_amount)} → ${formatMoney(item.supporting_values.current_amount)}` : "Calculated from recorded transactions"}</small></div></li>)}</ul> : <p className="p7-empty">{behavior?.insufficient_data?.[0] || "No measured behavior changes were found in the available history."}</p>}
            <div className="p7-seasonality"><strong>Seasonal pattern</strong><span>{behavior?.seasonality?.available ? `${behavior.seasonality.peak_calendar_month} has the highest observed average expense total.` : behavior?.seasonality?.reason}</span></div>
          </Panel>
          <Panel title="Adaptive budget" kicker="RECENT OBSERVED BASELINE">
            <div className="p7-budget-summary"><div><span>Recorded this month to date</span><strong>{formatMoney(budget?.current_month_expenses)}</strong></div><div><span>Possible monthly improvement</span><strong>{budget?.potential_monthly_improvement == null ? "Not enough data" : formatMoney(budget.potential_monthly_improvement)}</strong></div></div>
            {budget?.category_budgets?.length ? <div className="p7-budget-table-wrap"><table className="p7-budget-table"><thead><tr><th>Category</th><th>Recorded to date</th><th>History avg.</th><th>Target</th><th>Potential</th></tr></thead><tbody>{budget.category_budgets.map((row) => <tr key={row.category}><td>{row.category}</td><td>{formatMoney(row.current_spending)}</td><td>{row.historical_average == null ? "—" : formatMoney(row.historical_average)}</td><td>{row.recommended_amount == null ? "—" : formatMoney(row.recommended_amount)}</td><td>{row.potential_monthly_improvement == null ? "—" : formatMoney(row.potential_monthly_improvement)}</td></tr>)}</tbody></table></div> : <p className="p7-empty">No current-month expense categories are recorded.</p>}
            <p className="p7-muted">{budget?.method}</p>
            {budget?.baseline_available && <small className="p7-muted">Baseline months: {budget.baseline_months.join(", ")}. Annual improvement assumes the monthly pattern repeats.</small>}
          </Panel>
        </section>

        <section className="p7-grid p7-goals-grid" aria-label="Savings goals">
          <Panel title="Create a savings goal" kicker="SMART GOALS" className="p7-goal-create-panel">
            <form className="p7-form" onSubmit={saveGoal}>
              <label>Goal name<input value={goalForm.name} onChange={(event) => setGoalForm((current) => ({ ...current, name: event.target.value }))} maxLength="120" placeholder="e.g. Emergency fund" required /></label>
              <label>Target amount<input type="number" min="0.01" step="0.01" value={goalForm.target_amount} onChange={(event) => setGoalForm((current) => ({ ...current, target_amount: event.target.value }))} placeholder="₹" required /></label>
              <label>Already saved<input type="number" min="0" step="0.01" value={goalForm.current_amount} onChange={(event) => setGoalForm((current) => ({ ...current, current_amount: event.target.value }))} /></label>
              <label>Target date<input type="date" min={tomorrowLocalDate()} value={goalForm.target_date} onChange={(event) => setGoalForm((current) => ({ ...current, target_date: event.target.value }))} required /></label>
              <label>Priority<select value={goalForm.priority} onChange={(event) => setGoalForm((current) => ({ ...current, priority: event.target.value }))}><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
              <label>Category <span>optional</span><input value={goalForm.category} onChange={(event) => setGoalForm((current) => ({ ...current, category: event.target.value }))} maxLength="60" placeholder="e.g. Education" /></label>
              <button className="p3-primary-button" type="submit" disabled={goalBusy}>{goalBusy ? "Saving…" : "Create goal"}<Icon name="arrow" /></button>
            </form>
          </Panel>
          <Panel title="Goal optimization" kicker="CAPACITY-AWARE PLAN" className="p7-optimization-panel">
            <div className="p7-capacity"><span>Observed monthly contribution capacity</span><strong>{profileMoney(goals?.optimization?.observed_monthly_contribution_capacity)}</strong><small>Based on {goals?.optimization?.basis_month_count || 0} month(s) with income and expenses recorded.</small></div>
            {goals?.optimization?.allocations?.length ? <ol className="p7-allocation-list">{goals.optimization.allocations.map((row) => <li key={row.goal_id}><div><strong>{row.rank}. {row.goal_name}</strong><small>{row.reason}</small></div><span>{profileMoney(row.recommended_monthly_allocation)} / month</span></li>)}</ol> : <p className="p7-empty">{goals?.insufficient_data?.[0] || "Create an active goal to see a contribution plan."}</p>}
            <p className="p7-muted">{goals?.optimization?.method}</p>
          </Panel>
          <Panel title="Your savings goals" kicker={`${goalList.length} SAVED`} className="p7-goal-list-panel">
            {goalList.length ? <div className="p7-goal-list">{goalList.map((goal) => <GoalEditor key={goal.id} goal={goal} onUpdate={editGoal} onDelete={removeGoal} />)}</div> : <p className="p7-empty">No saved goals yet. Create a goal to calculate progress, required monthly savings, feasibility, and projected completion.</p>}
          </Panel>
        </section>

        <Panel title="Personalized actions" kicker="FROM YOUR RECORDS" className="p7-recommendations-panel">
          {recommendations?.recommendations?.length ? <div className="p7-recommendation-list">{recommendations.recommendations.map((item, index) => <article key={`${item.title}-${index}`}><div className="p7-recommendation-title"><strong>{item.title}</strong><span className={`p7-priority priority-${item.priority}`}>{item.priority}</span></div><p>{item.explanation}</p><small>{item.reason}</small>{item.estimated_impact?.monthly_cash_flow != null && <div className="p7-impact">Potential monthly improvement: <strong>{formatMoney(item.estimated_impact.monthly_cash_flow)}</strong></div>}</article>)}</div> : <p className="p7-empty">{recommendations?.insufficient_data?.[0] || "No personalized actions are supported by the current records."}</p>}
        </Panel>

        <Panel title="What-if simulator & scenario comparison" kicker="PROJECTED · READ-ONLY" className="p7-scenario-panel">
          <p className="p7-muted">Simulate a monthly change. Calculations are hypothetical and never update transactions. Any annual value assumes the monthly difference repeats for 12 months.</p>
          <form className="p7-form p7-scenario-form" onSubmit={submitScenario}>
            <label>Scenario name<input value={scenarioForm.name} onChange={(event) => setScenarioForm((current) => ({ ...current, name: event.target.value }))} maxLength="80" required /></label>
            <label>Change type<select value={scenarioForm.change_type} onChange={(event) => setScenarioForm((current) => ({ ...current, change_type: event.target.value }))}><option value="reduce_expense_category">Reduce expense category</option><option value="increase_income">Increase monthly income</option><option value="decrease_recurring_expense">Decrease detected recurring expense</option><option value="add_recurring_expense">Add monthly recurring expense</option><option value="increase_savings">Allocate more to savings</option><option value="change_budget">Set a category budget</option><option value="change_goal_contribution">Set a goal contribution</option></select></label>
            {["reduce_expense_category", "decrease_recurring_expense", "add_recurring_expense", "change_budget"].includes(scenarioForm.change_type) && <label>Expense category<select value={scenarioForm.category} onChange={(event) => setScenarioForm((current) => ({ ...current, category: event.target.value }))}>{EXPENSE_CATEGORIES.map((category) => <option key={category}>{category}</option>)}</select></label>}
            {scenarioForm.change_type === "change_goal_contribution" && <label>Active goal<select value={scenarioForm.goal_id || ""} onChange={(event) => setScenarioForm((current) => ({ ...current, goal_id: event.target.value }))} required><option value="">Choose a goal</option>{goalList.filter((goal) => goal.status === "active").map((goal) => <option key={goal.id} value={goal.id}>{goal.name}</option>)}</select></label>}
            <label>Monthly amount<input type="number" min="0.01" step="0.01" value={scenarioForm.amount} onChange={(event) => setScenarioForm((current) => ({ ...current, amount: event.target.value }))} required /></label>
            {scenarioError && <p className="p7-inline-error" role="alert">{scenarioError}</p>}
            <div className="p7-scenario-actions"><button className="p3-primary-button" type="submit" value="what-if" disabled={scenarioBusy}>{scenarioBusy ? "Calculating…" : "Run what-if"}</button><button className="p7-secondary-button" type="submit" value="scenario" disabled={scenarioBusy}>{scenarioBusy ? "Calculating…" : "Compare scenario"}</button></div>
          </form>
          {scenarioResult && <div className="p7-result" aria-live="polite"><h3>{scenarioResult.name} · {scenarioResult.status}</h3><div className="p7-comparison-table-wrap"><table className="p7-budget-table p7-comparison-table"><thead><tr><th>Metric</th><th>{scenarioResult.current_plan.label}</th><th>{scenarioResult.proposed_plan.label}</th></tr></thead><tbody>{[["Monthly income", "income"], ["Monthly expenses", "expenses"], ["Monthly surplus", "surplus"], ["Savings rate", "savings_rate_percent"], ["Projected annual surplus", "projected_annual_surplus"], ["Projected annual savings", "projected_annual_savings"]].map(([label, field]) => <tr key={field}><td>{label}</td><td>{field === "savings_rate_percent" ? (scenarioResult.current_plan[field] == null ? "Not available" : `${Number(scenarioResult.current_plan[field]).toFixed(1)}%`) : formatMoney(scenarioResult.current_plan[field])}</td><td>{field === "savings_rate_percent" ? (scenarioResult.proposed_plan[field] == null ? "Not available" : `${Number(scenarioResult.proposed_plan[field]).toFixed(1)}%`) : formatMoney(scenarioResult.proposed_plan[field])}</td></tr>)}<tr><td>Annual surplus change if repeated</td><td colSpan="2">{formatMoney(scenarioResult.comparison.annual_surplus_change_if_repeated)} · projected</td></tr><tr><td>Annual savings change if repeated</td><td colSpan="2">{formatMoney(scenarioResult.comparison.annual_savings_change_if_repeated)} · projected</td></tr></tbody></table></div>
            {scenarioResult.proposed_plan.goal_completion?.length > 0 && <div className="p7-result-goals"><strong>Goal completion projection</strong>{scenarioResult.proposed_plan.goal_completion.map((item) => <span key={item.goal_id}>{item.goal_name}: {item.projected_months_to_target == null ? "No contribution projection" : `${item.projected_months_to_target} months at the scenario contribution`}</span>)}</div>}
            <ul className="p7-assumptions">{scenarioResult.assumptions.map((assumption) => <li key={assumption}>{assumption}</li>)}</ul>
          </div>}
        </Panel>
      </>}
    </section>
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
          <dl className="p3-settings-list"><div><dt>Name</dt><dd>{summary.user_name || "FlexiFund account"}</dd></div><div><dt>Account</dt><dd>Private account</dd></div></dl>
          <p className="p3-settings-note">Profile details are read-only in this version.</p>
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

function AuthScreen({ initialError, onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = mode === "register"
        ? await registerAccount({ name, email, password })
        : await loginAccount({ email, password });
      onAuthenticated(user);
    } catch (requestError) {
      setError(requestError.message || "Unable to authenticate. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function usePresentationDemo() {
    setError("");
    setBusy(true);
    try {
      const user = await loginAccount({
        email: "demo@flexifund.local",
        password: "FlexiFundDemo2026!",
      });
      onAuthenticated(user);
    } catch (requestError) {
      setError(requestError.message || "The presentation demo is unavailable. Run python -m app.seed in the backend folder, then try again.");
    } finally {
      setBusy(false);
    }
  }

  function switchMode(nextMode) {
    setMode(nextMode);
    setError("");
  }

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="auth-title">
        <div className="auth-brand"><BrandMark /><span>flexifund<span className="brand-period">.</span></span></div>
        <div className="auth-kicker">PRIVATE FINANCIAL WORKSPACE</div>
        <h1 id="auth-title">{mode === "login" ? "Welcome back" : "Create your account"}</h1>
        <p className="auth-description">Sign in to review your own income, spending, and financial outlook.</p>
        <div className="auth-mode-tabs" role="tablist" aria-label="Account access">
          <button type="button" role="tab" aria-selected={mode === "login"} className={mode === "login" ? "active" : ""} onClick={() => switchMode("login")}>Sign in</button>
          <button type="button" role="tab" aria-selected={mode === "register"} className={mode === "register" ? "active" : ""} onClick={() => switchMode("register")}>Create account</button>
        </div>
        {(initialError || error) && <div className="auth-error" role="alert">{error || initialError}</div>}
        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === "register" && <label>Name<input autoComplete="name" maxLength="120" value={name} onChange={(event) => setName(event.target.value)} required /></label>}
          <label>Email<input type="email" autoComplete="email" maxLength="320" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <label>Password<input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={mode === "register" ? 12 : 1} maxLength="128" value={password} onChange={(event) => setPassword(event.target.value)} required /><small>{mode === "register" ? "Use at least 12 characters." : ""}</small></label>
          <button className="auth-submit" type="submit" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in securely" : "Create account"}</button>
        </form>
        {mode === "login" && <section className="auth-demo" aria-label="Presentation demo">
          <strong>Present FlexiFund with demo data</strong>
          <span>Uses a separate synthetic account with dashboard, forecast, goals, and personalized insights.</span>
          <button type="button" onClick={usePresentationDemo} disabled={busy}>Open presentation demo</button>
        </section>}
        <p className="auth-security-note">Your password is stored as a one-way hash. Each account’s financial records stay private to that signed-in account.</p>
      </section>
    </main>
  );
}

function App() {
  const [authUser, setAuthUser] = useState(null);
  const [authState, setAuthState] = useState("checking");
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchCurrentUser()
      .then((user) => { if (!cancelled) setAuthUser(user); })
      .catch((requestError) => {
        if (!cancelled && requestError.status !== 401) {
          setAuthError("The authentication service is unavailable. Check that the backend is running.");
        }
      })
      .finally(() => { if (!cancelled) setAuthState("ready"); });
    return () => { cancelled = true; };
  }, []);

  async function signOut() {
    try {
      await logoutAccount();
    } catch {
      // Remove the private view even if the session has already expired.
    }
    setAuthUser(null);
  }

  if (authState === "checking") return <LoadingState />;
  if (!authUser) return <AuthScreen initialError={authError} onAuthenticated={(user) => { setAuthError(""); setAuthUser(user); }} />;
  return <DashboardApp onLogout={signOut} />;
}

function periodQuery(selection) {
  const today = new Date();
  if (selection === "this-year") return { year: today.getFullYear() };
  const selectedDate = selection === "last-month"
    ? new Date(today.getFullYear(), today.getMonth() - 1, 1)
    : today;
  return { month: selectedDate.getMonth() + 1, year: selectedDate.getFullYear() };
}

function DashboardApp({ onLogout }) {
  const [activePage, setActivePage] = useState("dashboard");
  const [assistantSeedQuestion, setAssistantSeedQuestion] = useState("");
  const [summary, setSummary] = useState(null);
  const [monthly, setMonthly] = useState([]);
  const [categories, setCategories] = useState({});
  const [incomeRecords, setIncomeRecords] = useState([]);
  const [expenseRecords, setExpenseRecords] = useState([]);
  const [demo, setDemo] = useState(null);
  const [intelligence, setIntelligence] = useState(null);
  const [intelligenceError, setIntelligenceError] = useState("");
  const [intelligenceLoading, setIntelligenceLoading] = useState(true);
  const [personalization, setPersonalization] = useState(null);
  const [personalizationError, setPersonalizationError] = useState("");
  const [personalizationLoading, setPersonalizationLoading] = useState(true);
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
    setIntelligenceLoading(true);
    setIntelligenceError("");
    setPersonalizationLoading(true);
    setPersonalizationError("");
    try {
      const dashboardResponse = await fetchDashboard(periodQuery(periodSelection));
      const nextSummary = dashboardResponse?.data;
      if (!nextSummary) throw new Error("The dashboard response was incomplete.");
      const periodParams = { month: nextSummary.period.month || undefined, year: nextSummary.period.year };
      const [monthlyRows, categoryTotals, incomeResponse, expenseResponse, riderResult, intelligenceResult, personalizationResult] = await Promise.all([
        fetchMonthlySummary({ year: nextSummary.period.year }),
        fetchExpenseCategories(periodParams),
        fetchIncome(),
        fetchExpenses(),
        fetchRiderDemo()
          .then((response) => ({ response }))
          .catch(() => ({ response: null })),
        fetchIntelligenceOverview(periodParams)
          .then((response) => ({ response }))
          .catch((requestError) => ({ requestError })),
        fetchPersonalizationInsights()
          .then((response) => ({ response }))
          .catch((requestError) => ({ requestError })),
      ]);

      setSummary(nextSummary);
      setMonthly(Array.isArray(monthlyRows) ? monthlyRows : []);
      setCategories(categoryTotals || {});
      setIncomeRecords(incomeResponse?.data || []);
      setExpenseRecords(expenseResponse?.data || []);
      setDemo(riderResult.response?.data || riderResult.response);
      if (intelligenceResult.requestError) {
        setIntelligenceError(intelligenceResult.requestError.message || "Unable to load financial intelligence.");
      } else {
        setIntelligence(intelligenceResult.response?.data || null);
      }
      if (personalizationResult.requestError) {
        setPersonalizationError(personalizationResult.requestError.message || "Unable to load personalization insights.");
      } else {
        setPersonalization(personalizationResult.response?.data || null);
      }
    } catch (requestError) {
      if (requestError.status === 401) {
        void onLogout();
        return;
      }
      setError("Unable to connect to FlexiFund server. Please make sure the Flask backend is running.");
    } finally {
      if (initialLoad) setLoading(false);
      else setRefreshing(false);
      setIntelligenceLoading(false);
      setPersonalizationLoading(false);
    }
  }, [periodSelection, onLogout]);

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
    if (page !== "assistant") setAssistantSeedQuestion("");
    setActivePage(page);
    setNotificationsOpen(false);
  }

  function askAssistant(question = "") {
    setAssistantSeedQuestion(question);
    navigate("assistant");
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
        return <IncomePage summary={summary} records={incomeRecords} onCreated={handleRecordCreated} onNotify={setToast} />;
      case "expenses":
        return <ExpensesPage summary={summary} records={expenseRecords} onCreated={handleRecordCreated} onNotify={setToast} />;
      case "analytics":
        return <AnalyticsPage summary={summary} monthly={monthly} categories={categories} periodSelection={periodSelection} onPeriodChange={setPeriodSelection} />;
      case "health":
        return <HealthPage summary={summary} periodSelection={periodSelection} onPeriodChange={setPeriodSelection} />;
      case "personalization":
        return <PersonalizationPage onLogout={onLogout} onNotify={setToast} />;
      case "assistant":
        return <AssistantPage initialQuestion={assistantSeedQuestion} onLogout={onLogout} />;
      case "settings":
        return <SettingsPage summary={summary} themePreference={themePreference} onThemeChange={setTheme} dateFormat={dateFormat} onDateFormatChange={setDateFormat} notifications={notifications} onNotificationChange={updateNotification} />;
      default:
        return <DashboardPage summary={summary} monthly={monthly} categories={categories} transactions={transactions} demo={demo} intelligence={intelligence} intelligenceLoading={intelligenceLoading} intelligenceError={intelligenceError} personalization={personalization} personalizationLoading={personalizationLoading} personalizationError={personalizationError} onRetryIntelligence={() => loadDashboardData(false)} onNavigate={navigate} onAskAssistant={askAssistant} periodSelection={periodSelection} onPeriodChange={setPeriodSelection} />;
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
          onLogout={onLogout}
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
