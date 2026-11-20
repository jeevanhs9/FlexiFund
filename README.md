# FlexiFund

FlexiFund is a financial safety system for workers with changing income. Phase 2 added the finance backend and calculation engine. Phase 3 adds a responsive React dashboard for reviewing monthly cash flow, recording income and expenses, and exploring visual analytics. The original synthetic rider history remains available.

## Technology

- Python 3.11 or newer, Flask, Flask-CORS, SQLAlchemy, Pydantic, and python-dotenv
- SQLite for local development; the database file is created at `backend/flexifund.db`
- React and Vite for the frontend
- NumPy remains available for later analysis work

Docker is not required. The existing Compose file is retained from the earlier setup; the current application uses SQLite.

## Run on Windows

Open two PowerShell terminals from the repository root (`E:\FlexiFund`).

### Backend

```powershell
Set-Location E:\FlexiFund\backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.seed
python -m app.app
```

If PowerShell blocks virtual environment activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again. If `.env` already exists, skip `Copy-Item`.

The API runs at `http://127.0.0.1:5000`. `python -m app.seed` can be run again safely; it only inserts missing demo records.

For production, set `DEBUG=false`, set `FRONTEND_URL` to the exact frontend origin, and provide a randomly generated `SECRET_KEY` of at least 32 characters. The app rejects a missing or example secret outside debug mode and uses secure session cookies there. Local debug mode generates an ephemeral key when the example file is blank or contains a placeholder.

### Frontend

In the second terminal:

```powershell
Set-Location E:\FlexiFund\frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite forwards `/api` requests to the Flask server.

## Demo data

Run `python -m app.seed` to create or update the presentation account. It contains 12 completed months plus the current month of clearly marked synthetic income and expense records, so the dashboard, financial health, forecasts, personalization, goals, recommendations, and next-month expense model have data to display. The login page’s **Open presentation demo** button signs in with the synthetic account; its credentials are `demo@flexifund.local` and `FlexiFundDemo2026!`.

The current demo month records ₹50,000 income and ₹30,000 expenses, leaving ₹20,000 surplus and a 40% savings rate. Ravi's separate synthetic weekly rider records are retained for the rider history view. Both datasets are fictional and are separate from accounts created by users.

## Phase 3 dashboard

The React/Vite frontend provides:

- A dashboard with API-backed income, expenses, surplus, savings rate, and financial-health status.
- Monthly income, expense, and surplus charts, plus an expense-category doughnut chart.
- Essential versus non-essential spending comparison and recent transactions.
- Income and expense forms with validation, success/error feedback, and refreshed summaries after saving.
- A transactions page with API filters for record type, category, month, and year, plus text search, date range, and sorting.
- An analytics page with average monthly metrics and a savings trend, plus a financial-health detail page.
- A collapsible desktop sidebar, compact horizontally scrollable mobile navigation, and responsive transaction cards.
- Light, dark, and system appearance; date format; period selection; and notification preferences saved in the browser only.
- Dashboard period selection for this month, last month, and this year. Arbitrary date ranges are available in transaction filters; the dashboard API supports month/year filters.

Charts use accessible SVG rendered from API responses, so no chart package is needed. The API base defaults to the Vite `/api` proxy. To call Flask directly, set `VITE_API_BASE_URL` to `http://127.0.0.1:5000/api` before starting Vite.

## API

All API responses use JSON. Validation failures return a `4xx` status with a `message` field.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | API and database health |
| POST | `/api/auth/register` | Create an account and start a session |
| POST | `/api/auth/login` | Sign in and start a session |
| GET | `/api/auth/me` | Return the signed-in account and CSRF token |
| POST | `/api/auth/logout` | Revoke active sessions and sign out |
| POST | `/api/users` | Create a user |
| POST / GET | `/api/income` | Add income / list income, optionally filter by user, month, or year |
| POST / GET | `/api/expenses` | Add expense / list expenses, optionally filter by user, month, year, category, or type |
| GET | `/api/dashboard` | Current-month totals and financial health |
| GET | `/api/dashboard/monthly` | Monthly income, expenses, surplus, and savings rate |
| GET | `/api/dashboard/expense-categories` | Expense totals grouped by category |
| GET | `/api/demo/rider` | Existing synthetic rider profile and weekly history |

Registration requires a name, email, and password of at least 12 characters. Passwords are stored as Werkzeug scrypt hashes. Login creates a signed, HTTP-only, SameSite=Lax session cookie with a 12-hour expiry and a CSRF token. The frontend sends credentials and includes the CSRF token on writes. Logout increments the account's session version so previously copied session cookies stop working.

Income, expenses, dashboards, analytics, and all intelligence endpoints require an authenticated session. The server derives the account ID from that session. `user_id` is optional for compatibility, but a supplied ID must match the signed-in account or the API returns 403. New income and expense requests do not need a `user_id`; the server assigns ownership. Browser writes must come from the configured `FRONTEND_URL` and include the CSRF token. `/api/health` and the synthetic rider demo endpoint remain public; the rider endpoint contains only synthetic sample data. Expense type values are `Essential` and `Non-Essential`.

The frontend first checks `/api/auth/me`, then shows the login/register view until a session exists. It consumes the dashboard, income, expenses, and intelligence APIs without selecting a user ID, and provides sign out. The Vite proxy can be changed with `VITE_API_PROXY_TARGET` for local integration testing.

## Phase 5 — Financial Intelligence

The Phase 5 engine is a read-only pipeline over the selected user's actual income and expense records. It does not use the separate synthetic rider history, generate sample transactions, or alter stored finance rows.

```text
Income and expense rows
  → data_processor (validate, normalize, quality notes)
  → feature_engineering (monthly metrics and changes)
  → financial_engine (existing Decimal calculator)
  → spending / forecast / savings / anomaly / recurring analysis
  → risk_engine (coverage-aware score)
  → recommendation_engine
  → intelligence API and dashboard
```

Modules are kept in `backend/app/services/`: `data_processor.py`, `feature_engineering.py`, `financial_engine.py`, `spending_analysis.py`, `forecasting_engine.py`, `savings_prediction.py`, `anomaly_detection.py`, `recurring_detection.py`, `risk_engine.py`, `recommendation_engine.py`, and `intelligence_service.py`. HTTP handlers live in `backend/app/routes/intelligence_routes.py`. Basic amounts continue to use the existing `Decimal` calculator as the source of truth; the dashboard calculator now also exposes the non-essential expense ratio.

### Algorithms and fallback behavior

- Data validation rejects non-finite/non-positive amounts, invalid dates, and rows whose `user_id` differs from the selected account. A missing expense category is labeled `Uncategorized`; unknown essentiality is left unclassified. Exact duplicate candidates are reported and retained, never silently deleted.
- Monthly features are calculated only for months with recorded transactions. Savings/expense ratios are `null` in features when income is zero, even though the legacy summary API preserves its safe numeric zero behavior.
- Spending analysis ranks categories and reports their share, transaction count, monthly changes, largest transactions, and volatility. A trend needs at least ₹250 of change and at least 10% movement. Overspending compares the latest selected month with up to three prior observed months and requires a 25% increase, a 1.5-standard-deviation threshold, and at least ₹250 above the baseline.
- Forecasting uses a weighted moving average over up to six contiguous, completed months, with weights increasing from oldest to newest. It requires at least three consecutive observed months ending in the month before the current month. Otherwise prediction amounts and confidence are `null` and the API explains why. Current partial-month data is not used for the forecast. The low/medium confidence label reflects sample count and expense variability; it is not a claimed accuracy rate.
- Savings prediction is strictly predicted income minus predicted expenses. It is unavailable when forecasting is unavailable or predicted income is zero.
- Category-spike anomalies compare against at least three previous observed monthly values using the greater of mean + 1.5 standard deviations or 125% of the mean, plus a ₹250 minimum increase. Large individual transactions are compared only with same-category transaction peers. Alerts are called “Unusual Spending,” not fraud.
- Recurring detection requires at least three similar expenses, 20% maximum adjacent amount variation, and repeated 6–40 day intervals. Frequency is labeled weekly/monthly when the average interval supports it.
- The 0–100 health indicator uses disclosed weights: savings rate (20), expense ratio (20), cash-flow stability (15), income stability (10), essential ratio (10), discretionary ratio (10), spending volatility (10), and savings trend (5). Missing components are excluded, the observed weights are normalized, and coverage is reported. Bands follow the requested 80/65/50/30 thresholds. This is a budgeting indicator, not a credit score.
- Recommendations reference selected-period results or explicit statistical comparisons. A 10% discretionary reduction is labeled a hypothetical illustration. Emergency targets use observed essential expenses multiplied by three and six; current balance stays `null` because the app has no emergency-fund balance field.
- No ML model is trained in Phase 5: the explainable statistical pipeline is more appropriate for the available history. Phase 7 adds account-owned goal tracking and personalization endpoints alongside this Phase 5 pipeline.

### Intelligence endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/intelligence/overview` | Full analysis, quality, forecast, risk, alerts, emergency targets, and recommendations |
| GET | `/api/intelligence/forecast` | Cash-flow estimate and data sufficiency explanation |
| GET | `/api/intelligence/spending` | Categories, monthly changes, overspending, and largest transactions |
| GET | `/api/intelligence/anomalies` | Statistical unusual-spending flags |
| GET | `/api/intelligence/recurring` | Repeated expenses inferred from recorded rows |
| GET | `/api/intelligence/risk` | Score, component coverage, and risk factors |
| GET | `/api/intelligence/recommendations` | Prioritized data-backed actions |
| GET | `/api/intelligence/savings` | Observed and forecast savings details |

Each returns `{"status":"success","data":...,"generated_at":"..."}`. All intelligence routes use the signed-in account; an optional `user_id` can only repeat that account ID. `month` and `year` select the period used for the summary and category mix. Forecasting always uses completed historical periods. The dashboard renders actual monthly records as solid bars and any available estimate as dashed, outlined bars. If the intelligence request fails, the existing dashboard data remains usable and the intelligence panel provides a retry state.

### Scope and limitations

The auth migration adds nullable `password_hash` and `session_version` columns to existing `users` tables without deleting rows. Legacy accounts have no inferred password; the app does not provide email verification, password reset, or legacy-account recovery yet. A new account starts with its own records and does not inherit the seeded demo account's history. Emergency-fund balances are not stored, and the profile reports that limitation. Forecasts are intentionally unavailable until there is enough contiguous completed history, and missing months are not fabricated as zero-spend months.

Example requests from PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
Invoke-RestMethod http://127.0.0.1:5000/api/dashboard
Invoke-RestMethod 'http://127.0.0.1:5000/api/expenses?category=food'

$incomeBody = @{
  user_id = 1
  source = "Salary"
  amount = 50000
  income_type = "Salary"
  date = "2026-11-20"
  description = "Monthly salary"
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/income `
  -ContentType "application/json" -Body $incomeBody

$expenseBody = @{
  user_id = 1
  category = "Food"
  amount = 5000
  expense_type = "Essential"
  date = "2026-11-20"
  description = "Monthly food expenses"
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/expenses `
  -ContentType "application/json" -Body $expenseBody
```

Income and expense endpoints wrap results in `status` and `data`. Dashboard example:

```json
{
  "status": "success",
  "data": {
    "total_income": 50000,
    "total_expenses": 30000,
    "surplus": 20000,
    "savings_rate": 40.0,
    "expense_ratio": 60.0,
    "essential_expenses": 25000,
    "non_essential_expenses": 5000,
    "essential_expense_ratio": 83.33,
    "financial_status": "Healthy"
  }
}
```

Invalid requests return a JSON error such as `{"status":"error","message":"Amount must be greater than zero."}`. Monthly summaries return a JSON array, and the category summary returns a JSON object keyed by category.

## Phase 6 — AI Financial Assistant

The assistant is integrated into the authenticated React workspace. The query analyzer routes common questions to deterministic intents: balance, income, expenses, spending, category, budget, savings, forecast, risk, goal, scenario, anomaly, recommendation, financial health, and general. It runs the existing Phase 5 intelligence pipeline against the signed-in user's own records, then returns a structured factual calculation. Goal, budget, recommendation, risk, monthly savings, and what-if questions also call the Phase 7 personalization services. It does not create sample data or invent missing forecasts.

The optional LLM is only used to explain verified facts. `AI_PROVIDER=disabled` is the default, so deterministic answers still work without an external AI account. Supported adapters are `openai` (Responses API) and `openai_compatible` (Chat Completions-compatible services). Configure these backend-only environment variables:

| Variable | Purpose |
| --- | --- |
| `AI_PROVIDER` | `disabled`, `openai`, or `openai_compatible` |
| `AI_API_KEY` | Provider key; never exposed to Vite or browser code |
| `AI_MODEL` | Model/deployment name accepted by the configured provider |
| `AI_API_BASE_URL` | Optional API base URL; defaults to the OpenAI API for the selected adapter |
| `AI_TIMEOUT_SECONDS` | Provider timeout, capped at 20 seconds; defaults to 8 |

When enabled, the provider receives the question, up to eight recent conversation messages, and a compact intent-specific summary of calculated metrics. It does not receive the user's name/email or raw transaction descriptions. If the provider is unconfigured, times out, rejects its key, or returns malformed data, FlexiFund keeps the verified calculation and reports that the AI explanation is unavailable. Provider errors and response bodies are not logged.

Conversation messages are stored in the additive `assistant_messages` table with user ID, UUID conversation ID, role, body, and timestamp. All history reads/deletes are scoped to the session user. History is limited to the latest 40 messages in API responses, and only the latest eight messages are considered for optional LLM context. The assistant page is part of the current SPA rather than a separate HTML app; dashboard shortcuts and the sidebar open it.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/assistant/chat` | Analyze a question, calculate facts, and optionally request an explanation |
| GET | `/api/assistant/history` | Return the signed-in user's latest conversation, optionally selected by `conversation_id` |
| DELETE | `/api/assistant/history` | Clear the signed-in user's conversations |

All three endpoints require the authenticated cookie session; writes require the existing origin and CSRF checks. A supplied `user_id` must match the session identity. Conversation IDs are also checked against their owner. Phase 7 goal questions use the account's saved goals and calculated allocation strategy. Emergency-fund estimates still use the Phase 5 engine and do not imply that a current balance is known.

Run the complete backend and live HTTP regression suite with:

```powershell
Set-Location E:\FlexiFund\backend
python -m unittest discover -s tests -v
```

## Phase 7 — Personalization & Adaptive Financial Intelligence

Phase 7 extends the existing Flask, SQLAlchemy, SQLite, Phase 5 intelligence, Phase 6 assistant, and React SPA. Its snapshot loader reads the signed-in user's income, expenses, goals, and goal adjustments once per request, then reuses the Phase 5 calculation pipeline. It does not read the synthetic rider history or create financial data.

The financial profile reports averages only for months that contain the corresponding recorded data. Surplus and savings-rate averages require both income and expenses in the same month. The profile also exposes essential and discretionary ratios, Phase 5 income variation and spending volatility, recurring-cost ratio, positive-surplus consistency, top categories, goal progress, financial-health coverage, and data gaps.

Behavior analysis reports observed month-to-month expense and category changes, savings-rate direction, Phase 5 anomaly and recurring signals, goal contribution consistency, and seasonal patterns only after at least 24 observed months with repeated calendar-month observations. Classification is deterministic and lists its threshold basis. It does not use clustering or a behavioral ML model.

Adaptive category targets require three prior observed expense months. Each target is capped at the average of those observed months; it does not apply a generic percentage cut. Goal math includes remaining amount, progress, monthly requirement, required savings rate, projected completion based on observed positive surplus, and feasibility. The allocation plan orders active goals by priority and then target date, and caps the total by the observed average positive surplus. All projections are planning estimates, not guarantees.

`financial_goals` stores user-owned goals. `goal_contributions` records opening balances, user-recorded increases, and withdrawals. These rows reflect values entered into FlexiFund; they are not bank-verified. On an existing installation with a `users` table, startup creates the two tables additively without reseeding the demo account or altering finance transactions. New installations get them through the existing `create_tables` setup.

The what-if engine supports reducing a category, increasing income, reducing a detected recurring cost, adding a recurring cost, changing a category budget, allocating more to savings, and changing an active goal contribution. A scenario returns current recorded values beside proposed values and does not write transactions or persist scenario results. Annual changes assume the monthly difference repeats 12 times. The Phase 5 health score is not recalculated for hypothetical values because it scores recorded history.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/personalization/insights` | Combined profile, behavior, budget, goals, recommendations, and risk |
| GET | `/api/personalization/profile` | Account-specific financial profile |
| GET | `/api/personalization/behavior` | Trends, classification, recurring patterns, anomalies, and seasonality |
| GET | `/api/personalization/budget` | Adaptive category targets and potential improvement |
| GET | `/api/personalization/goals` | Goal progress, feasibility, and allocation strategy |
| POST | `/api/personalization/goals` | Create a goal |
| PUT | `/api/personalization/goals/<goal_id>` | Update a goal and record a balance adjustment |
| DELETE | `/api/personalization/goals/<goal_id>` | Delete an owned goal and its adjustment history |
| GET | `/api/personalization/recommendations` | Evidence-based personalized actions |
| POST | `/api/personalization/what-if` | Calculate a hypothetical plan |
| POST | `/api/personalization/scenario` | Compare recorded and proposed plans |

## Phase 7.1 — Next-month Expense Prediction

Phase 7.1 adds one account-scoped ML feature: a prediction of total expenses for the next calendar month. It uses only actual completed months that contain recorded expense transactions. A missing month is never turned into a zero-expense observation.

The feature vector for each target month contains the prior three total expense months (`lag_1_expenses`, `lag_2_expenses`, `lag_3_expenses`), their three-month mean, their three-month change, and sine/cosine representations of the target calendar month. The target month is excluded from its own features, so the training process cannot see a future expense total.

FlexiFund requires 12 consecutive completed expense months. It creates nine supervised observations, trains on the first six, and keeps the final three chronological observations for validation. The candidate regressors are Linear Regression, Random Forest Regressor, and Gradient Boosting Regressor. The service measures MAE, RMSE, and R² when the holdout has sufficient variation, then compares them with a naive previous-month baseline. An ML model is selected only if it improves validation MAE; otherwise the baseline is retained. The endpoint returns the selected method and the actual validation metrics for that account rather than claiming a fixed accuracy.

Per-account artifacts are written atomically under `MODEL_STORE_DIR` (default: `backend/model_store`, ignored by Git), use an app-controlled filename derived from the authenticated account ID, and are reused only when an aggregate monthly-data fingerprint and the feature schema match. The artifact contains fitted parameters and aggregate monthly values only; it does not store transaction descriptions. A changed history retrains and replaces the artifact. The model-store directory must remain writable by the backend and must not be exposed as a static download directory.

The existing Phase 5 weighted moving average remains the income estimator and the fallback for expense histories without enough data. When the validated expense predictor is available, the cash-flow forecast uses its expense estimate, derives projected savings from that estimate, adds a clearly labeled projected-expense factor to risk/recommendations, and supplies the exact structured result to the Phase 6 assistant. The dashboard chart keeps actual bars separate from the outlined predicted next-month bars.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/intelligence/expense-prediction` | Return the signed-in account’s validated next-month expense prediction, evaluation, baseline, or honest insufficient-data result |

The endpoint is authenticated and any supplied `user_id` must match the signed-in account. The assistant answers “What will I spend next month?”, “How much can I save next month?”, and “Are my expenses increasing?” from the same calculation. No prediction changes transactions.

Every route requires the authenticated cookie session. The account ID comes from that session; supplied `user_id` values must match it. Goal reads and writes include the owner in their database query, so a guessed ID returns not found. All writes keep the existing origin and CSRF checks. Invalid input returns a client error; database failures return a generic service-unavailable message without logging transaction details.

The Personalization page contains the financial profile, risk indicator, trends, adaptive budget, goal creation and editing, allocation ordering, recommendations, and scenario comparison. The dashboard preview uses the same API. The Phase 6 assistant calls these services for goal, budget, recommendation, risk, monthly-savings, and parseable what-if questions; any optional LLM receives only the calculated summary, not raw transaction descriptions or account identity.

Known limits: current-month totals can be partial; category budgeting and scenarios show recorded-to-date amounts. A goal's current balance is user-entered. An emergency-fund balance is not configured. Three prior expense months are needed for an adaptive category target, three observed transaction months for behavior classification, and 24 observed months for seasonality. Small or sparse histories remain labeled insufficient rather than filled with invented values.

## Calculations

Money is stored as `NUMERIC(12, 2)` and calculated with Python `Decimal` values. Surplus is income minus expenses; savings rate is surplus divided by income, expressed as a percentage. Zero income produces a zero savings rate. Health is `Deficit` when surplus is negative, `Healthy` at a savings rate of 20% or more, `Moderate` at 10% or more, and `Needs Attention` below 10%.

## Tests

From the backend directory, run:

```powershell
python -m unittest discover -s tests -v
```

Tests use temporary SQLite databases. They cover finance and goal CRUD, profile and behavioral calculations, budgets, recommendations, goal feasibility, all supported scenario types, transaction immutability, login/logout, password hashing, session invalidation, CSRF and origin checks, unauthenticated access, cross-user IDOR attempts across finance, intelligence, assistant, goals, and scenarios, additive legacy schema setup, forecast sufficiency, risk score bounds, predictive-feature leakage, chronological model evaluation, artifact reuse, API authentication/isolation, assistant prediction use, and existing phase regressions. The live integration tests start a localhost Flask HTTP server on an ephemeral port and do not modify the demo database.
