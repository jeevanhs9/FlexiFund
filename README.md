# FlexiFund

FlexiFund is a financial safety system for workers with changing income. Phase 2 adds a financial engine that tracks income and expenses, calculates surplus and savings rate, and summarizes monthly cash flow. The existing synthetic rider dashboard remains available.

## Technology

- Python 3.11 or newer, Flask, Flask-CORS, SQLAlchemy, Pydantic, and python-dotenv
- SQLite for local development; the database file is created at `backend/flexifund.db`
- React and Vite for the frontend
- NumPy remains available for later analysis work

Docker is not required for Phase 2. The existing Compose file is retained for the earlier PostgreSQL setup.

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

### Frontend

In the second terminal:

```powershell
Set-Location E:\FlexiFund\frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite forwards `/api` requests to the Flask server.

## Demo data

The seeded finance demo user has monthly income of ₹50,000 and expenses of ₹30,000, leaving ₹20,000 surplus and a 40% savings rate. Ravi's separate synthetic weekly rider records are retained for the rider history view. Both sets of demo data are fictional.

## API

All API responses use JSON. Validation failures return a `4xx` status with an `error` field.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | API and database health |
| POST | `/api/users` | Create a user |
| POST / GET | `/api/income` | Add income / list income, optionally filter by user, month, or year |
| POST / GET | `/api/expenses` | Add expense / list expenses, optionally filter by user, month, year, category, or type |
| GET | `/api/dashboard` | Current-month totals and financial health |
| GET | `/api/dashboard/monthly` | Monthly income, expenses, surplus, and savings rate |
| GET | `/api/dashboard/expense-categories` | Expense totals grouped by category |
| GET | `/api/demo/rider` | Existing synthetic rider profile and weekly history |

The dashboard endpoints accept `user_id` (defaults to the seeded demo user), plus `month` and `year` where applicable. Expense type is `essential` or `non-essential`.

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

## Calculations

Money is stored as `NUMERIC(12, 2)` and calculated with Python `Decimal` values. Surplus is income minus expenses; savings rate is surplus divided by income, expressed as a percentage. Zero income produces a zero savings rate. Health is `Deficit` when surplus is negative, `Healthy` at a savings rate of 20% or more, `Moderate` at 10% or more, and `Needs Attention` below 10%.

## Calculator tests

From the backend directory, run:

```powershell
python -m unittest discover -s tests -v
```
