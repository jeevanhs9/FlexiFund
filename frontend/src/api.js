// Reusable fetch helpers for the Flask API. Set VITE_API_BASE_URL to point at
// a different backend; Vite proxies /api to Flask during local development.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");

function apiUrl(path) {
  return `${API_BASE_URL}/${path.replace(/^\/+/, "")}`;
}

async function requestJson(path, options = {}) {
  let response;
  try {
    response = await fetch(apiUrl(path), {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new Error("Unable to connect to FlexiFund server. Please make sure Flask is running.");
  }

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
  requestJson(withQuery("/dashboard", params));

export const fetchMonthlySummary = (params = {}) =>
  requestJson(withQuery("/dashboard/monthly", params));

export const fetchExpenseCategories = (params = {}) =>
  requestJson(withQuery("/dashboard/expense-categories", params));

export const fetchIncome = (params = {}) =>
  requestJson(withQuery("/income", params));

export const fetchExpenses = (params = {}) =>
  requestJson(withQuery("/expenses", params));

export const addIncome = (income) =>
  requestJson("/income", { method: "POST", body: JSON.stringify(income) });

export const addExpense = (expense) =>
  requestJson("/expenses", { method: "POST", body: JSON.stringify(expense) });

export const fetchRiderDemo = () => requestJson("/demo/rider");
