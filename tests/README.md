# CapitolScope test suite

Real `pytest` suite for the backend. This replaces the old convention of
standalone `test_*.py` scripts at the repo root (which are run manually with
`python …` and are *not* collected by pytest).

## Running

From the repo root, using the project virtualenv:

```bash
.venv/bin/python -m pytest                 # full suite + coverage report
.venv/bin/python -m pytest --no-cov -q     # faster, no coverage
.venv/bin/python -m pytest tests/unit      # unit tests only
.venv/bin/python -m pytest -m "not db"     # skip tests needing a live database
.venv/bin/python -m pytest -k ticker       # by keyword
```

`uv pip install -e .[dev]` installs pytest, pytest-asyncio, pytest-mock, etc.

## Layout

- `tests/conftest.py` — bootstraps the import path (`app/src`) and injects dummy
  `SUPABASE_*` env vars so `core.config` imports without a real backend. Also
  disables the optional local-LLM ticker reranker so no test hits the network.
  Provides the `enhancer`, `ticker_extractor`, and `make_settings` fixtures.
- `tests/unit/` — fast, no I/O. Config validation, exceptions, response
  envelope, shared enums, and the two data-quality/ticker-extraction engines.
- `tests/integration/` — two kinds of tests:
  - `test_migrations.py` guards the Alembic revision graph (single head/base,
    linear chain, resolvable parents). It runs **offline** — parses migration
    scripts, never opens a database.
  - `test_crud_*.py` exercise the CRUD/repository layer against a **real
    Postgres** (see "Database-backed tests" below).

## Database-backed tests

CRUD tests are marked `db` and use fixtures from `tests/integration/conftest.py`:

- The schema is built by running the **real Alembic migrations** (`alembic
  upgrade head`), not `Base.metadata.create_all` — the ORM models have drifted
  from the migrations (e.g. `sectors` won't build via create_all), so the
  migrations are the source of truth.
- Where the database comes from, in order: `TEST_DATABASE_URL` if set (must be
  a **disposable** DB — migrations run against it); otherwise an ephemeral
  `postgres:16-alpine` container via `testcontainers` (needs Docker); otherwise
  the db tests are **skipped** so the rest of the suite still runs.
- `db_session` — a synchronous `Session` for the sync CRUD (e.g.
  `domains.securities.crud`). `async_db_session` — an `AsyncSession` for the
  async repositories (e.g. `domains.congressional.crud`). Both wrap each test
  in a transaction with `join_transaction_mode="create_savepoint"`, so CRUD
  code that calls `commit()` is still rolled back for perfect per-test
  isolation. The schema is migrated once per session; only data is rolled back.
- `_register_orm_models` (autouse) imports every domain's models so SQLAlchemy's
  string-based relationships (e.g. `Security` → `"MemberPortfolio"`) resolve
  regardless of which db-test subset runs.

Run just the DB tests: `.venv/bin/python -m pytest -m db`. Skip them (no Docker):
`.venv/bin/python -m pytest -m "not db"`. First run pulls/starts a container, so
it takes ~40-60s; subsequent runs reuse the local `postgres:16-alpine` image.

## Conventions

- **Import root is `app/src`.** Import backend modules as `core.config`,
  `domains.congressional.data_quality`, etc. — not `app.src.…`. `pythonpath` in
  `pyproject.toml` and `conftest.py` handle this.
- **Never construct the module-level `settings` singleton in a test.** Use the
  `make_settings(**overrides)` fixture; it disables `.env` loading for
  determinism and lets you override individual fields.
- **Markers:** `unit`, `integration`, `db` (needs a live database), `slow`.
  `--strict-markers` is on, so register new markers in `pyproject.toml`.
- **`TestKnownIssues` / `xfail`:** known-wrong behavior we intend to fix is
  captured as `@pytest.mark.xfail(strict=False)` asserting the *desired*
  outcome. When the code is fixed the test xpasses — that is the signal to
  delete the marker and promote it to a hard assertion. See the false-positive
  ticker cases in `test_data_quality.py` and `test_ticker_extraction.py`.

## Coverage

Coverage is measured (`--cov=app/src`) and printed, but there is **no**
`--cov-fail-under` gate yet — the suite is being grown from zero and a hard floor
would fail an otherwise-green run. Re-introduce a floor once the core domains are
covered (see the note in `pyproject.toml`).

## Bugs surfaced by these tests

The `xfail` / `TestKnownIssues` cases document real defects to fix:

- `SectorCRUD.get_top_level_sectors()` / `get_sub_sectors()` filter
  `Sector.parent_sector_id`, which does not exist (the column is
  `parent_sector_gics_code`) — they always raise `AttributeError`.
- `domains/market_data/__init__.py` fails to import (a Pydantic
  field/annotation clash in `schemas.py`), which is why the DB fixture mirrors
  Alembic and excludes `market_data`.
- The ORM models have drifted from the Alembic migrations (`create_all` cannot
  build `sectors`).
- False-positive ticker extraction in both extractor implementations.

## Not yet covered (good next targets)

The sync (`securities`) and async (`congressional`) CRUD paths now have example
coverage. Remaining gaps: the rest of the CRUD/repository methods, the service
layer, and API routes (which would use FastAPI's `TestClient` with dependency
overrides). The `db` fixtures are ready to extend for the first two.
