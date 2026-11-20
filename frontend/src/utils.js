const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

const numberFormatter = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 1,
});

export function formatMoney(value) {
  return currencyFormatter.format(Number(value) || 0);
}

export function formatCompactMoney(value) {
  const amount = Number(value) || 0;
  if (Math.abs(amount) >= 100000) return `₹${numberFormatter.format(amount / 100000)}L`;
  if (Math.abs(amount) >= 1000) return `₹${numberFormatter.format(amount / 1000)}K`;
  return formatMoney(amount);
}

export function formatDate(value, options = { day: "numeric", month: "short", year: "numeric" }) {
  if (!value) return "—";
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", options).format(parsed);
}

export function formatPeriod(period) {
  if (!period?.month || !period?.year) return "All periods";
  return new Intl.DateTimeFormat("en-IN", { month: "long", year: "numeric" }).format(
    new Date(period.year, period.month - 1, 1),
  );
}

export function todayLocalDate() {
  const today = new Date();
  const localDate = new Date(today.getTime() - today.getTimezoneOffset() * 60000);
  return localDate.toISOString().slice(0, 10);
}

export function combineTransactions(income = [], expenses = []) {
  const rows = [
    ...income.map((record) => ({
      ...record,
      recordType: "Income",
      label: record.description || record.source,
      categoryLabel: record.source,
      subtype: record.income_type,
      signedAmount: Number(record.amount),
    })),
    ...expenses.map((record) => ({
      ...record,
      recordType: "Expense",
      label: record.description || record.category,
      categoryLabel: record.category,
      subtype: record.expense_type,
      signedAmount: -Number(record.amount),
    })),
  ];

  return rows.sort((left, right) => {
    const dateOrder = right.date.localeCompare(left.date);
    if (dateOrder !== 0) return dateOrder;
    return String(right.created_at || "").localeCompare(String(left.created_at || ""));
  });
}

export function getHealthMessage(summary) {
  if (!summary) return "Your financial summary will appear here when the API is connected.";
  const surplus = Number(summary.surplus) || 0;
  switch (summary.financial_status) {
    case "Deficit":
      return `Expenses exceed income by ${formatMoney(Math.abs(surplus))} this period.`;
    case "Healthy":
      return `${formatMoney(surplus)} remains after expenses this period, with a healthy savings rate.`;
    case "Moderate":
      return `${formatMoney(surplus)} remains after expenses this period, with a moderate savings rate.`;
    default:
      return `${formatMoney(surplus)} remains after expenses this period; this is a small share of income.`;
  }
}
