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
- `tests/integration/` — `test_migrations.py` guards the Alembic revision graph
  (single head/base, linear chain, resolvable parents). It runs **offline** —
  it parses migration scripts and never opens a database.

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

## Not yet covered (good next targets)

CRUD/service layers and API routes need either a real test database or async
session mocking; none exist yet. The `db` marker and `integration/` directory
are the intended home for those once a disposable Postgres (or SQLite-compat
subset) fixture is wired up.
