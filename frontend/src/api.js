// Reusable fetch helpers for the Flask API.

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.message ?? `Request failed with status ${response.status}.`);
  }
  return payload;
}

function withQuery(path, params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  }
  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
}

export const fetchDashboard = (params = {}) =>
  requestJson(withQuery("/api/dashboard", params));

export const fetchMonthlySummary = (params = {}) =>
  requestJson(withQuery("/api/dashboard/monthly", params));

export const fetchExpenseCategories = (params = {}) =>
  requestJson(withQuery("/api/dashboard/expense-categories", params));

export const fetchIncome = (params = {}) =>
  requestJson(withQuery("/api/income", params));

export const fetchExpenses = (params = {}) =>
  requestJson(withQuery("/api/expenses", params));

export const addIncome = (income) =>
  requestJson("/api/income", { method: "POST", body: JSON.stringify(income) });

export const addExpense = (expense) =>
  requestJson("/api/expenses", { method: "POST", body: JSON.stringify(expense) });

export const fetchRiderDemo = () => requestJson("/api/demo/rider");
