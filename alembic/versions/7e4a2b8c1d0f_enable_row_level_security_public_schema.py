"""Enable RLS on all public tables for PostgREST hardening

Revision ID: 7e4a2b8c1d0f
Revises: f095fc199c74
Create Date: 2026-03-25

CapitolScope data is accessed via FastAPI using the postgres role (bypasses RLS).
PostgREST exposes the public schema to anon/authenticated; with RLS enabled and no
policies, those roles cannot read or write rows, which resolves Supabase linter
findings (rls_disabled_in_public, sensitive_columns_exposed).

If you later query these tables from the browser with the Supabase client, add
explicit policies for anon/authenticated (e.g. auth.uid()).
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "7e4a2b8c1d0f"
down_revision = "f095fc199c74"
branch_labels = None
depends_on = None

_ENABLE_RLS_LOOP = """
DO $rls$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', r.tablename);
  END LOOP;
END $rls$;
"""

_DISABLE_RLS_LOOP = """
DO $rls$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
  LOOP
    EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', r.tablename);
  END LOOP;
END $rls$;
"""


def upgrade() -> None:
    op.execute(_ENABLE_RLS_LOOP)


def downgrade() -> None:
    op.execute(_DISABLE_RLS_LOOP)
