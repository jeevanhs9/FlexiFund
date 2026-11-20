# FlexiFund

FlexiFund is a financial safety system concept for workers whose income changes from week to week, including delivery riders. The project follows **Predict → Protect → Prove**: understand irregular income, help a worker plan a safety buffer, and explain the evidence behind a recommendation.

## Phase 1: Foundation

This phase establishes the backend structure, PostgreSQL connection, SQLAlchemy models, validation schemas, persona adapter interface, Flask API, synthetic rider history, and a read-only React/Vite dashboard. It does not calculate risk or recommend financial actions.

Ravi is a fictional demo profile. His Bengaluru profile and all associated income and expense history are **synthetic and not real-world verified financial data**. The records are authored to show normal, strong, rain-affected, lean, recovery, and festival-demand weeks.

## Technology

- Python 3.11 or newer
- Flask and Flask-CORS
- SQLAlchemy 2.x
- PostgreSQL with the Psycopg 3 driver
- NumPy, available for later analysis work
- Pydantic for request and response validation
- python-dotenv for local environment configuration
- React and Vite for the read-only demo dashboard

## Project structure

```text
flexifund/
├── backend/
│   ├── app/
│   │   ├── adapters/       # Persona normalization interface and rider adapter
│   │   ├── engine/         # Reserved for later financial engines
│   │   ├── routes/         # Health and read-only synthetic demo endpoint
│   │   ├── app.py          # Local Flask entry point
│   │   ├── config.py       # Environment-backed settings
│   │   ├── database.py     # SQLAlchemy engine and session helpers
│   │   ├── models.py       # Rider and financial history tables
│   │   ├── schemas.py      # Pydantic validation schemas
│   │   └── seed.py         # Synthetic Ravi data
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # React/Vite dashboard for the synthetic rider data
│   ├── src/                # Dashboard UI and responsive styles
│   ├── index.html
│   ├── package.json
│   └── vite.config.js      # Proxies API calls to Flask
├── docker-compose.yml      # Local PostgreSQL only
└── .gitignore
```

## Run locally

### 1. Configure the environment

From the repository root, copy `backend/.env.example` to `backend/.env`. The example contains local development credentials only; replace them if you change the PostgreSQL credentials.

```powershell
Copy-Item backend/.env.example backend/.env
```

### 2. Start PostgreSQL

Docker Desktop must be installed and running. From the repository root:

```powershell
docker compose up -d
docker compose ps
```

Compose starts only PostgreSQL, keeps its data in a named volume, and waits for its health check. It publishes the database on host port `5433` (container port `5432`) to avoid colliding with a locally installed PostgreSQL service. The local development defaults match the example database URL. Set `POSTGRES_HOST_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` in a root `.env` file or the shell to change the port or credentials; update `DATABASE_URL` in `backend/.env` to match.

### 3. Install Python dependencies

From the repository root:

```powershell
py -3 -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

### 4. Seed the synthetic rider

```powershell
Set-Location backend
python -m app.seed
```

The seed creates the tables if needed, inserts Ravi if he is missing, and adds any missing weekly history records. Its 32-week demo timeline has fixed dates, so rerunning it later will not shift the history or add another batch. Each date represents the start of a synthetic week; income, work costs, and household essential expenses are stored as separate decimal amounts.

### 5. Start Flask

Keep the shell in the `backend` directory:

```powershell
python -m app.app
```

For Flask's development server instead:

```powershell
flask --app app.app run --debug
```

Open the health check at [http://localhost:5000/health](http://localhost:5000/health). It returns `{"status":"ok","service":"FlexiFund API"}`. The root endpoint at [http://localhost:5000/](http://localhost:5000/) returns the API welcome message and phase.

The read-only dashboard data endpoint is `GET /api/demo/rider`. It returns Ravi's seeded profile and weekly history without calculating financial outcomes.

### 6. Start the frontend

Leave the backend running. Open a second PowerShell window from the repository root:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The dashboard reads Ravi's synthetic weekly history through `GET /api/demo/rider`; Vite forwards that request to Flask. If the database or seed is unavailable, the page explains what to start. The chart displays gross income and household essentials as separate stored values and does not calculate a surplus or risk score.

## Data model

`Rider` identifies the worker and whether the profile is synthetic. `FinancialHistory` links each dated record to a rider. All money columns use `NUMERIC(12, 2)` and map to Python `Decimal` values.

Work costs (fuel, maintenance, data, and other work costs) remain separate from household essential expenses. Later phases can therefore calculate work-adjusted income and then subtract household expenses without mixing those categories. Phase 1 stores the inputs only; it does not perform those calculations.

## Phase 2 direction

Phase 2 can add the Financial Intelligence Engine, starting with clearly defined income and expense calculations. Later work may add risk simulation, protection planning, stability scoring, what-if scenarios, and evidence benchmarks. The current React/Vite dashboard is read-only; none of those later features are implemented yet.
