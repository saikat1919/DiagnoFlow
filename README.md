# DiagnoFlow

DiagnoFlow is a web-based diagnostic centre and pharmacy management system. It brings patient registration, diagnostic testing workflows, report handling, pharmacy operations, and day-to-day centre management into one application.

It also includes an AI assistant that can answer questions about the centre using available system tools and knowledge sources.

## What the System Does

DiagnoFlow supports the main activities of a diagnostic centre and its pharmacy:

- **Patient management:** Maintain patient profiles and manage patient accounts.
- **Staff and role management:** Support separate access for system administrators, receptionists, lab technicians, pharmacists, and pharmacy managers.
- **Diagnostic test catalogue:** Organise diagnostic departments and available tests.
- **Diagnostic orders:** Create and track diagnostic orders, test-item progress, and payment status.
- **Test reports:** Upload reports, manage report status, and release completed reports to patients.
- **Pharmacy catalogue:** Maintain medicine details, strengths, dosage forms, selling prices, and reorder levels.
- **Inventory management:** Manage suppliers, purchase orders, medicine batches, expiry dates, stock movements, and usable stock.
- **Prescription management:** Record prescriptions and match prescribed medicines with the pharmacy catalogue.
- **Pharmacy sales:** Process medicine sales and track payment status.
- **AI assistant:** Answer supported questions about medicines, tests, centre policies, and role-appropriate summaries.
- **Knowledge retrieval:** Use a retrieval-based knowledge module for supported knowledge sources such as policies and test information.

The system applies role-based access so users can access only the functionality and information permitted for their role.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python 3.14, FastAPI |
| Frontend | React 19, Vite 6 |
| Database | PostgreSQL 17 with pgvector |
| ORM and database access | SQLAlchemy 2.x (async) |
| Database migrations | Alembic |
| Python dependency management | uv |
| AI chat model | Groq API using the OpenAI-compatible client |
| Text embeddings | Google Gemini Embedding API |
| Authentication | JWT |
| Password hashing | pwdlib with Argon2 |
| Containerisation | Docker and Docker Compose |
| Application protocol integration | Model Context Protocol (MCP) |

## System Architecture

At a high level, the React frontend communicates with the FastAPI backend through HTTP API requests. The backend contains the application modules, authentication and role checks, business logic, and database access layer.

PostgreSQL stores application data. The pgvector extension supports vector-based knowledge retrieval. The AI assistant uses the configured Groq model for responses and Gemini for generating text embeddings.

```text
                 ┌─────────────────────┐
                 │   React Frontend    │
                 │     (Vite)          │
                 └──────────┬──────────┘
                            │ HTTP
                            ▼
                 ┌─────────────────────┐
                 │    FastAPI Backend  │
                 │                     │
                 │  API / Services     │
                 │  Authentication     │
                 │  Role Permissions   │
                 │  AI Assistant / MCP │
                 └───────┬─────┬───────┘
                         │     │
               SQL       │     │ AI / Embeddings
                         ▼     ▼
              ┌────────────┐  ┌──────────────────┐
              │ PostgreSQL │  │ Groq API         │
              │ + pgvector │  │ Gemini API       │
              └────────────┘  └──────────────────┘
```

## Prerequisites

Choose either the Docker-based setup or the local development setup.

### Required for either setup

- Git
- API credentials for:
  - [Groq](https://console.groq.com/) — chat model access
  - [Google AI Studio](https://aistudio.google.com/) — Gemini embedding access

### Docker-based setup

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose

### Local development setup

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Node.js 20 LTS or later
- npm
- Docker Desktop (used to run the PostgreSQL database), or a PostgreSQL 17 installation with pgvector enabled

---

## Local Setup

The following instructions use the repository root as the working directory.

### 1. Clone the repository

```bash
git clone https://github.com/saikat1919/DiagnoFlow.git
cd DiagnoFlow
```

### 2. Configure environment variables

Create your local `.env` file from the example:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**Linux / macOS**

```bash
cp .env.example .env
```

Open `.env` and provide the required values.

Example local configuration:

```dotenv
APP_NAME=DiagnoFlow
DEBUG=true

DB_HOST=localhost
DB_PORT=5433
DB_USER=diagnoflow_user
DB_PASSWORD=change-this-local-password
DB_NAME=diagnoflow
DB_SCHEMA=diagnoflow

JWT_SECRET=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=30

GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=your-available-groq-model
GROQ_BASE_URL=https://api.groq.com/openai/v1

GEMINI_API_KEY=your-gemini-api-key

UPLOAD_DIR=uploads
CORS_ORIGINS=http://localhost:5173,http://localhost:5174
```

Generate a secure JWT secret rather than using the example value. For example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not commit `.env` or share API keys, database passwords, or JWT secrets. The repository's `.gitignore` excludes `.env`.

#### Environment variable reference

| Variable | Purpose |
|---|---|
| `APP_NAME` | Application name. Defaults to `DiagnoFlow`. |
| `DEBUG` | Enables or disables debug mode. |
| `DB_HOST` | PostgreSQL hostname. Use `localhost` when running the backend on your computer; Docker Compose overrides this to `db` for the backend container. |
| `DB_PORT` | PostgreSQL port. Use `5433` from your computer with the provided Compose configuration; the backend container uses `5432`. |
| `DB_USER` | PostgreSQL username. |
| `DB_PASSWORD` | PostgreSQL password. |
| `DB_NAME` | PostgreSQL database name. |
| `DB_SCHEMA` | Application database schema. The example uses `diagnoflow`. |
| `JWT_SECRET` | Secret used to sign authentication tokens. |
| `JWT_ALGORITHM` | JWT signing algorithm. The example uses `HS256`. |
| `ACCESS_TOKEN_MINUTES` | Access-token lifetime in minutes. |
| `GROQ_API_KEY` | API key used by the AI chat provider. |
| `GROQ_MODEL` | A model identifier available to your Groq account. |
| `GROQ_BASE_URL` | Groq's OpenAI-compatible API base URL. |
| `GEMINI_API_KEY` | API key used by the Gemini embedding client. |
| `UPLOAD_DIR` | Directory used for uploaded files. Defaults to `uploads`. |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins. |

---

## Option A: Run the Full System with Docker Compose

This is the simplest way to start the backend, frontend, and database together.

### 1. Make sure `.env` is configured

Complete the environment variables as described above. The provided Compose file maps the database to port `5433` on your computer and overrides the backend container's database host and port to `db:5432`.

### 2. Build and start the services

From the repository root:

```bash
docker compose up --build -d db diagnoflow frontend
```

This starts:

| Service | Local address |
|---|---|
| Frontend | http://localhost:5174 |
| Backend | http://localhost:8002 |
| PostgreSQL | `localhost:5433` |

The Compose file also defines an `embedder` service. The current backend embedding client uses the Gemini API configured through `GEMINI_API_KEY`; the `embedder` service is not required for the setup commands above.

### 3. Run database migrations

The database tables must be created before using the application.

```bash
docker compose exec diagnoflow alembic upgrade head
```

The PostgreSQL initialisation script enables the `vector` extension and creates the `diagnoflow` schema on the first database initialisation. Alembic applies the remaining schema migrations.

### 4. Create the initial System Admin

The project does not create the initial System Admin through public registration. Create the first administrator from the backend container:

```bash
docker compose exec diagnoflow python -m scripts.create_system_admin
```

Follow the prompts to enter the administrator's name, mobile number, email, and password.

### 5. Add demo/master data

To create the sample staff accounts, patient records, departments, tests, suppliers, medicines, and opening pharmacy stock:

```bash
docker compose exec diagnoflow python -m scripts.seed_master_script
```

This script creates sample data where records do not already exist. The demo staff and patient accounts use a shared password defined inside `scripts/seed_master_script.py`. It is intended for local demonstration only; change or remove demo credentials before using real data.

### 6. Add demo transactions (optional)

To create sample diagnostic orders, reports, prescriptions, stock movements, and pharmacy sales:

```bash
docker compose exec diagnoflow python -m scripts.seed_transaction_script
```

The transaction seed script skips its work if diagnostic orders already exist. Run it only when you want the sample transaction data.

### 7. Open the application

- Frontend: http://localhost:5174
- Backend health check: http://localhost:8002/health
- Database health check: http://localhost:8002/db/health

### Useful Docker commands

View service status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f diagnoflow
```

View frontend logs:

```bash
docker compose logs -f frontend
```

Stop the services:

```bash
docker compose down
```

The database is stored in a named Docker volume, so `docker compose down` does not delete the database.

**Warning:** The following command also deletes the database volume and all local database data:

```bash
docker compose down -v
```

Use it only when you intentionally want to reset the local database.

---

## Option B: Run the Backend and Frontend Directly

This setup is useful during development because the backend and Vite frontend can run directly on your computer with their development reload features. Docker is used only for PostgreSQL.

### 1. Configure `.env`

Follow the environment configuration steps above. For this setup, use:

```dotenv
DB_HOST=localhost
DB_PORT=5433
```

The other database and API settings should also be populated.

### 2. Start PostgreSQL

Start only the database service from the repository root:

```bash
docker compose up -d db
```

The Compose configuration uses the `pgvector/pgvector:pg17` image and publishes the database on port `5433`.

Check that the database container is running:

```bash
docker compose ps
```

### 3. Install backend dependencies

Install `uv` if it is not already installed. Then, from the repository root:

```bash
uv sync --frozen
```

This installs the Python dependencies specified by `uv.lock`.

### 4. Apply database migrations

```bash
uv run alembic upgrade head
```

### 5. Create the initial System Admin

```bash
uv run python -m scripts.create_system_admin
```

### 6. Seed demo/master data

```bash
uv run python -m scripts.seed_master_script
```

Optional demo transactions:

```bash
uv run python -m scripts.seed_transaction_script
```

See the Docker setup section for details about what the seed scripts create and their demo credentials.

### 7. Start the backend

From the repository root:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

The backend will be available at http://localhost:8002.

### 8. Install and start the frontend

Open a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite starts the frontend at:

http://localhost:5173

The Vite development server proxies `/api` requests to `http://localhost:8002`, so the local frontend can communicate with the backend without a separate frontend API URL setting.

---

## Database and Seed Scripts

The project uses Alembic to manage database schema changes.

| Command | Purpose |
|---|---|
| `uv run alembic upgrade head` | Apply all migrations to the latest revision when running locally. |
| `uv run python -m scripts.create_system_admin` | Interactively create the initial System Admin account. |
| `uv run python -m scripts.seed_master_script` | Add demo staff, patients, departments, tests, suppliers, medicines, and opening stock. |
| `uv run python -m scripts.seed_transaction_script` | Add optional demo diagnostic and pharmacy transactions. |

When running these commands inside Docker, replace the `uv run` prefix with `docker compose exec diagnoflow` and use the corresponding command shown in Option A.

Do not run demo seed scripts against a production database unless you explicitly intend to insert demonstration records.

## Project Structure

```text
DiagnoFlow/
├── app/
│   ├── api/                  # API routes and versioned routers
│   ├── core/                 # Configuration, security, exceptions
│   ├── db/                   # Database base, session, model imports
│   ├── integrations/         # Groq and Gemini integrations
│   ├── mcp/                  # MCP server and context
│   └── modules/              # Application business modules
│       ├── chat/
│       ├── diagnostic_orders/
│       ├── diagnostic_test_catalogue/
│       ├── inventory/
│       ├── knowledge/
│       ├── medicines/
│       ├── patients/
│       ├── prescriptions/
│       ├── purchases/
│       ├── sales/
│       ├── suppliers/
│       ├── test_reports/
│       └── users/
├── alembic/                  # Database migration revisions
├── frontend/
│   ├── public/
│   └── src/                  # React application
├── scripts/
│   ├── create_system_admin.py
│   ├── seed_master_script.py
│   ├── seed_transaction_script.py
│   └── init-db.sql
├── .env.example
├── alembic.ini
├── docker-compose.yaml
├── Dockerfile
├── pyproject.toml
├── render.yaml
└── uv.lock
```
