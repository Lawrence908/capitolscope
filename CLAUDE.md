# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

CapitolScope is a full-stack platform for tracking and analyzing congressional stock trading disclosures. Backend is a FastAPI/SQLAlchemy async app with a Supabase-hosted PostgreSQL database; frontend is React 18 + TypeScript + Vite. Deployed as Docker services on the `daedalus` homelab host (see root `/mnt/CLAUDE.md` for host-level infra context) at `capitolscope.chrislawrence.ca`, port 8120.

## Commands

### Backend (run from repo root; package root is `app/`, source root is `app/src`)

```bash
# Install deps (uv is the package manager; pyproject.toml is the source of truth)
uv pip install -e .[dev]

# Run the API locally (must run from app/src — imports are rooted there, e.g. `from core.config import settings`)
cd app/src && python -m uvicorn main:app --reload --port 8000

# Alembic migrations (run from repo root — alembic.ini and alembic/ live there, but env.py adds app/src to sys.path)
alembic upgrade head
alembic revision --autogenerate -m "description"

# Celery worker / beat scheduler (from app/src, matches compose.yaml)
cd app/src && python -m celery -A background.celery_app worker -P solo --loglevel=info
cd app/src && python -m celery -A background.celery_app beat --schedule=/app/celery/celerybeat-schedule

# Lint / format / type-check
black app/src
isort app/src
flake8 app/src
mypy app/src
bandit -r app/src
```

**Backend tests are a real pytest suite under `tests/`** (added to "right the ship"). Run from the repo root with the venv:

```bash
.venv/bin/python -m pytest                 # full suite + coverage report
.venv/bin/python -m pytest --no-cov -q     # faster
.venv/bin/python -m pytest tests/unit      # unit only
.venv/bin/python -m pytest -m "not db"     # skip tests needing a live DB
```

See `tests/README.md` for conventions. Key points: `tests/conftest.py` puts `app/src` on the path and injects dummy `SUPABASE_*` env vars (so `core.config` imports without a real backend) and disables the local-LLM ticker reranker; use the `make_settings()` fixture instead of the module-level `settings` singleton; markers `unit`/`integration`/`db`/`slow` are `--strict`. `tests/integration/test_migrations.py` is an **offline** Alembic drift guard (asserts a single head, single base, linear chain) — run it before generating new migrations. Known-wrong behavior is captured as `xfail` in `TestKnownIssues` classes; an xpass means the bug is fixed and the test should be promoted to a hard assertion. There is intentionally **no `--cov-fail-under` gate yet** (see the note in `pyproject.toml`).

The old-style standalone scripts at repo root (`test_congressional_pipeline.py`, `test_cap_24_25_implementation.py`, `test_price_fetcher_simple.py`, `simple_test*.py`) are **not** collected by pytest — they're manual `python …` scripts with `__main__` blocks. Prefer adding to the `tests/` suite; CRUD/service/API-route coverage is the main gap (needs a test DB or async-session mocking).

### Frontend (`frontend/`)

```bash
cd frontend
npm run dev       # Vite dev server, port 5173
npm run build     # tsc + vite build
npm run lint      # eslint .
npm run preview
```

### Docker (production-shaped local run)

```bash
docker compose -f compose.yaml up -d --build
```
Services: `capitolscope` (API, :8120→8000), `capitolscope-redis`, `capitolscope-worker` (Celery), `capitolscope-scheduler` (Celery beat), `capitolscope-frontend` (:8121→5173). All backend containers set `working_dir: /app/src` and `PYTHONPATH=/app/src` — this is required, not incidental, because of how imports are structured (see Architecture below).

## Architecture

### Import root gotcha

Backend code is *not* imported as `app.src.domains.foo` — it's imported as `domains.foo`, `core.config`, `api.trades`, etc., because `app/src` is added directly to `sys.path` (via `PYTHONPATH=/app/src` in Docker, and via `sys.path.insert()` in `main.py` and `alembic/env.py` for local runs). Any script or tool that needs to import backend modules must either run with cwd/`PYTHONPATH` set to `app/src`, or manually insert that path first — see the `sys.path.insert(0, ...)` pattern at the top of the root-level `test_*.py` scripts.

### Domain-driven layout

Business logic lives under `app/src/domains/<domain>/`, one package per bounded context: `congressional`, `securities`, `market_data`, `portfolio`, `notifications`, `users`, `analytics`, `trading`. Each domain generally has its own `models.py` (SQLAlchemy), `schemas.py` (Pydantic), `crud.py`, `services.py`, and `interfaces.py`. `domains/base/` defines the generic contracts everything else implements:
- `interfaces.py` — `BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType]` ABC (generic CRUD contract)
- `models.py` — `CapitolScopeBaseModel`, the declarative base all domain models inherit
- `crud.py` / `services.py` — generic base implementations domain-specific classes extend

`app/src/api/` holds one FastAPI router module per resource (`trades.py`, `members.py`, `portfolios.py`, `market_data.py`, `notifications.py`, `auth.py`, `stripe.py`, `health.py`), wired up in `main.py` under `settings.API_V1_PREFIX` (`/api/v1`). `api/middleware.py` has the custom `RateLimitMiddleware`, `RequestLoggingMiddleware`, and `ErrorHandlingMiddleware`.

`app/src/core/` is cross-cutting: `config.py` (Pydantic `Settings`, env-driven), `database.py` (`DatabaseManager` — maintains both an async engine/session factory for the app and a sync engine/session factory for import scripts and Alembic), `auth.py`, `email.py`, `exceptions.py`, `responses.py`.

`app/src/background/` is Celery: `celery_app.py` defines the app, `tasks.py` the task definitions, `price_ingestion_task.py` a dedicated periodic job. There's a separate `cloud_run_worker.py` / `production_celery.py` pair for the GCP Cloud Run deployment path (see `docs/CLOUD_RUN_*`, `deploy/`, `scripts/gcloud/`) — this repo supports two deployment targets (homelab Docker Compose and GCP Cloud Run) and they use different worker entrypoints.

### Congressional data ingestion

This is the most complex subsystem. `domains/congressional/ingestion.py` is the pipeline entry point (PDF/CSV/API sources → `TradeRecord` → DB), backed by `data_quality.py` (`DataQualityEnhancer`, fuzzy-matching ticker/amount/owner normalization via `fuzzywuzzy`), `ticker_extraction.py`, and `pdf_parser.py`. `domains/congressional/fetch/` (currently untracked/in-progress) holds `house_fetcher.py`, `senate_fetcher.py`, `orchestrator.py`, `base.py`, `state.py` — a newer fetcher abstraction layered on top of the ingestion pipeline; check its state before assuming it's wired into the orchestration described in the older docs. Background docs worth reading before touching this code: `CONGRESSIONAL_IMPORT_GUIDE.md`, `CONGRESSIONAL_DATA_QUALITY_IMPROVEMENTS.md`, `docs/DATA_QUALITY_AUDIT.md`, `data_migration_strategy.md`.

### Database

PostgreSQL via Supabase, accessed through SQLAlchemy 2.0 async (`asyncpg`) for the app and sync (`psycopg2`) for Alembic/scripts — both engines are constructed from the same `settings.database_url` / `database_url_sync` in `core/database.py`. Migrations are in `alembic/versions/`; `alembic/env.py` imports every domain's `models.py` so autogenerate can see the full schema. There's an in-flight, not-yet-applied migration at `alembic/versions/7e4a2b8c1d0f_enable_row_level_security_public_schema.py` — check `alembic current` / `alembic heads` before generating new migrations to avoid branching.

### Frontend

`frontend/src/services/api.ts` is a single Axios-based `APIClient` used app-wide; base URL resolution is environment-aware (forces HTTPS in production to avoid mixed-content errors — see `MIXED_CONTENT_FIX.md`). `frontend/src/pages/` are route-level views, `frontend/src/components/` are shared/presentational components (`alerts/`, `charts/` subfolders), `frontend/src/hooks/` for data-fetching/state hooks, `frontend/src/contexts/` for React context providers, `frontend/src/core/` for cross-cutting frontend utilities (e.g. `logging`). Alerts (`components/alerts/`, `pages/alerts/`, `hooks/useAlerts.ts`) are a distinct feature area mirroring the backend `notifications` domain.

### Subscription tiers & billing

Free / Pro / Premium / Enterprise tiers gate feature access; Stripe handles billing (`api/stripe.py`, `scripts/setup_stripe_products.py`, `STRIPE_LOCAL_DEV_SETUP.md`, `stripe_products_mock.env.example`). Tier logic touches `domains/users` and is referenced from `domains/congressional` and `domains/portfolio` for access gating — check `docs/PRICING_TIERS.md` before changing tier behavior.

### Legacy code

`legacy/` contains a prior implementation (including its own `ingestion/test_validation_system.py`). Don't extend it; it's kept for reference during the migration described in `data_migration_strategy.md` / `DATA_MIGRATION_GUIDE.md`.

## Conventions

- No emdashes in generated text (repo-wide style rule, inherited from host-level config) — use commas, semicolons, colons, or restructure the sentence instead.
