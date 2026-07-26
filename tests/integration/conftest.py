"""
Database fixtures for CRUD/repository integration tests.

Schema provisioning strategy
----------------------------
Tables are built by running the real Alembic migrations (`alembic upgrade
head`) against a throwaway Postgres, NOT by `Base.metadata.create_all`. The
ORM models have drifted from the migrations (e.g. the ``sectors`` self-FK does
not build under create_all), so the migrations are the source of truth and the
thing we actually deploy — testing against them is both correct and exercises
the migration chain.

Where the database comes from
-----------------------------
1. If ``TEST_DATABASE_URL`` is set, it is used as-is. It MUST point at a
   disposable database — migrations run against it.
2. Otherwise, an ephemeral ``postgres:16-alpine`` container is started via
   testcontainers (Docker required).
3. If neither is available, every test that requests a db fixture is skipped
   (the rest of the suite stays green).

Isolation
---------
Each test runs inside an outer transaction with ``join_transaction_mode=
"create_savepoint"``, so even CRUD code that calls ``commit()`` is rolled back
at the end of the test. The schema is migrated once per session; only the data
is rolled back per test.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POSTGRES_IMAGE = os.environ.get("TEST_POSTGRES_IMAGE", "postgres:16-alpine")


class _DbParams:
    """Connection parameters for the provisioned test database."""

    def __init__(self, host: str, port: int, user: str, password: str, dbname: str):
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.dbname = dbname

    @property
    def sync_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.dbname}"
        )

    @property
    def async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.dbname}"
        )


def _docker_available() -> bool:
    try:
        import testcontainers  # noqa: F401
    except Exception:
        return False
    return shutil.which("docker") is not None


def _params_from_url(url: str) -> _DbParams:
    from sqlalchemy.engine import make_url

    u = make_url(url)
    return _DbParams(
        host=u.host or "localhost",
        port=u.port or 5432,
        user=u.username or "postgres",
        password=u.password or "",
        dbname=u.database or "postgres",
    )


def _run_migrations(params: _DbParams) -> None:
    """Run `alembic upgrade head` against the target database.

    alembic/env.py builds its URL from ``settings.database_url``, so we point
    the DATABASE_* settings (and blank out SUPABASE_URL) at the test database
    and run alembic in a subprocess to get fresh, uncached settings.
    """
    # gen_random_uuid() etc. live in pgcrypto; create it defensively first.
    from sqlalchemy import create_engine, text

    engine = create_engine(params.sync_url)
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            conn.commit()
    finally:
        engine.dispose()

    env = dict(os.environ)
    env.update(
        {
            "ENVIRONMENT": "testing",
            "TESTING": "true",
            # Force the "traditional" (non-Supabase) DSN branch in config.py.
            "SUPABASE_URL": "",
            "SUPABASE_KEY": "test",
            "SUPABASE_SERVICE_ROLE_KEY": "test",
            "SUPABASE_PASSWORD": "test",
            "SUPABASE_JWT_SECRET": "test",
            "DATABASE_PROVIDER": "local",
            "DATABASE_HOST": params.host,
            "DATABASE_PORT": str(params.port),
            "DATABASE_USER": params.user,
            "DATABASE_PASSWORD": params.password,
            "DATABASE_NAME": params.dbname,
        }
    )
    alembic_bin = Path(sys.executable).parent / "alembic"
    cmd = [str(alembic_bin)] if alembic_bin.exists() else [sys.executable, "-m", "alembic"]
    result = subprocess.run(
        cmd + ["upgrade", "head"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "alembic upgrade head failed while provisioning the test database:\n"
            f"{result.stdout}\n{result.stderr}"
        )


@pytest.fixture(scope="session", autouse=True)
def _register_orm_models():
    """
    Import every mapped model so SQLAlchemy's string-based relationships (e.g.
    Security -> "MemberPortfolio") resolve when mappers are configured — no
    matter which subset of db tests is being run. Without this, running only
    the securities CRUD tests fails because the portfolio/congressional classes
    were never imported. Mirrors the model set in alembic/env.py.
    """
    import domains.securities.models  # noqa: F401
    import domains.congressional.models  # noqa: F401
    import domains.users.models  # noqa: F401
    import domains.notifications.models  # noqa: F401
    import domains.portfolio.models  # noqa: F401
    from sqlalchemy.orm import configure_mappers

    configure_mappers()


@pytest.fixture(scope="session")
def database() -> _DbParams:
    """
    Provision a migrated Postgres for the test session.

    Skips (rather than fails) the whole db-dependent slice when no database and
    no Docker are available.
    """
    explicit_url: Optional[str] = os.environ.get("TEST_DATABASE_URL")
    if explicit_url:
        params = _params_from_url(explicit_url)
        _run_migrations(params)
        yield params
        return

    if not _docker_available():
        pytest.skip(
            "No TEST_DATABASE_URL and Docker/testcontainers unavailable; "
            "skipping database-backed tests."
        )

    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer(POSTGRES_IMAGE) as container:
        params = _DbParams(
            host=container.get_container_host_ip(),
            port=container.get_exposed_port(5432),
            user=container.username,
            password=container.password,
            dbname=container.dbname,
        )
        _run_migrations(params)
        yield params


@pytest.fixture(scope="session")
def sync_engine(database: _DbParams):
    from sqlalchemy import create_engine

    engine = create_engine(database.sync_url, future=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(sync_engine):
    """
    A synchronous Session bound to a rolled-back transaction.

    Matches the sync CRUD layer (e.g. domains.securities.crud), which calls
    self.db.commit(); create_savepoint mode keeps those commits inside the
    outer transaction so they are discarded at teardown.
    """
    from sqlalchemy.orm import Session

    connection = sync_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
async def async_db_session(database: _DbParams):
    """
    An AsyncSession bound to a rolled-back transaction, for the async CRUD/
    repository layer (e.g. domains.congressional.crud, domains.users.crud).

    A dedicated async engine is created per test to avoid cross-event-loop
    reuse issues with the function-scoped asyncio loop.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    engine = create_async_engine(database.async_url, poolclass=None)
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(
        bind=connection, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        await session.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()
        await engine.dispose()
