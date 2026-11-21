// Reusable fetch helpers for the Flask API. Set VITE_API_BASE_URL to point at
// a different backend; Vite proxies /api to Flask during local development.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");
let csrfToken = null;

export function setCsrfToken(value) {
  csrfToken = typeof value === "string" ? value : null;
}

function apiUrl(path) {
  return `${API_BASE_URL}/${path.replace(/^\/+/, "")}`;
}

async function requestJson(path, options = {}) {
  let response;
  const method = (options.method || "GET").toUpperCase();
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const headers = {
    ...(options.body && !isFormData ? { "Content-Type": "application/json" } : {}),
    ...(method !== "GET" && method !== "HEAD" && csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    ...options.headers,
  };
  try {
    response = await fetch(apiUrl(path), {
      ...options,
      credentials: "include",
      headers,
    });
  } catch {
    throw new Error("Unable to connect to FlexiFund server. Please make sure Flask is running.");
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(payload?.message ?? `Request failed with status ${response.status}.`);
    error.status = response.status;
    throw error;
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

export const fetchIntelligenceOverview = (params = {}) =>
  requestJson(withQuery("/intelligence/overview", params));

export const fetchIncome = (params = {}) =>
  requestJson(withQuery("/income", params));

export const fetchExpenses = (params = {}) =>
  requestJson(withQuery("/expenses", params));

export const addIncome = (income) =>
  requestJson("/income", { method: "POST", body: JSON.stringify(income) });

export const addExpense = (expense) =>
  requestJson("/expenses", { method: "POST", body: JSON.stringify(expense) });

function statementFormData(file, mapping = null) {
  const form = new FormData();
  form.append("file", file);
  if (mapping && typeof mapping === "object") form.append("mapping", JSON.stringify(mapping));
  return form;
}

export const previewBankStatement = (file, mapping = null) =>
  requestJson("/transactions/preview", { method: "POST", body: statementFormData(file, mapping) });

export const importBankStatement = (file, mapping = null) =>
  requestJson("/transactions/import", { method: "POST", body: statementFormData(file, mapping) });

export const fetchImportBatches = () => requestJson("/transactions/imports");

export const fetchImportedTransactions = (batchId, reviewOnly = false) =>
  requestJson(withQuery(`/transactions/imports/${batchId}/transactions`, { review_only: reviewOnly || undefined }));

export const fetchImportedTransactionList = (reviewOnly = false) =>
  requestJson(withQuery("/transactions", { review_only: reviewOnly || undefined }));

export const updateImportedTransaction = (transactionId, changes) =>
  requestJson(`/transactions/imported/${transactionId}`, { method: "PATCH", body: JSON.stringify(changes) });

export const fetchRiderDemo = () => requestJson("/demo/rider");

export const fetchAssistantHistory = (conversationId = null) =>
  requestJson(withQuery("/assistant/history", { conversation_id: conversationId }));

export const sendAssistantQuestion = (question, conversationId = null) =>
  requestJson("/assistant/chat", {
    method: "POST",
    body: JSON.stringify({ question, ...(conversationId ? { conversation_id: conversationId } : {}) }),
  });

export const clearAssistantHistory = (conversationId = null) =>
  requestJson(withQuery("/assistant/history", { conversation_id: conversationId }), { method: "DELETE" });

export const fetchPersonalizationInsights = () =>
  requestJson("/personalization/insights");

export const fetchPersonalizationProfile = () =>
  requestJson("/personalization/profile");

export const fetchPersonalizationBehavior = () =>
  requestJson("/personalization/behavior");

export const fetchPersonalizationBudget = () =>
  requestJson("/personalization/budget");

export const fetchFinancialGoals = () =>
  requestJson("/personalization/goals");

export const fetchPersonalizedRecommendations = () =>
  requestJson("/personalization/recommendations");

export const createFinancialGoal = (goal) =>
  requestJson("/personalization/goals", { method: "POST", body: JSON.stringify(goal) });

export const updateFinancialGoal = (goalId, changes) =>
  requestJson(`/personalization/goals/${goalId}`, { method: "PUT", body: JSON.stringify(changes) });

export const deleteFinancialGoal = (goalId) =>
  requestJson(`/personalization/goals/${goalId}`, { method: "DELETE" });

export const runWhatIfScenario = (plan) =>
  requestJson("/personalization/what-if", { method: "POST", body: JSON.stringify(plan) });

export const compareFinancialScenario = (plan) =>
  requestJson("/personalization/scenario", { method: "POST", body: JSON.stringify(plan) });

export async function registerAccount(account) {
  const response = await requestJson("/auth/register", {
    method: "POST",
    body: JSON.stringify(account),
  });
  setCsrfToken(response?.data?.csrf_token);
  return response?.data?.user;
}

export async function loginAccount(credentials) {
  const response = await requestJson("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
  setCsrfToken(response?.data?.csrf_token);
  return response?.data?.user;
}

export async function fetchCurrentUser() {
  const response = await requestJson("/auth/me");
  setCsrfToken(response?.data?.csrf_token);
  return response?.data?.user;
}

export async function logoutAccount() {
  try {
    await requestJson("/auth/logout", { method: "POST" });
  } finally {
    setCsrfToken(null);
  }
}
