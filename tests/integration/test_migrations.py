"""
Alembic migration-integrity guards.

These run entirely offline: they parse the migration scripts with Alembic's
ScriptDirectory API and never open a database connection or import
``alembic/env.py`` (which would pull in ``core.config`` and real settings).

The single-head test is the tripwire that catches migration *drift* the moment
a branch is introduced, which is exactly what we want to prevent going forward.
"""

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory


@pytest.fixture(scope="module")
def script_directory(repo_root: Path) -> ScriptDirectory:
    cfg = Config(str(repo_root / "alembic.ini"))
    # Resolve script_location relative to the repo root regardless of cwd.
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    return ScriptDirectory.from_config(cfg)


@pytest.mark.integration
def test_migrations_have_exactly_one_head(script_directory: ScriptDirectory):
    """
    There must be exactly one Alembic head.

    More than one head means the revision graph has branched (two migrations
    share a down_revision), which breaks `alembic upgrade head` and is the
    "drift" this guard exists to catch.
    """
    heads = script_directory.get_heads()
    assert len(heads) == 1, (
        f"Expected a single migration head, found {len(heads)}: {heads}. "
        "The revision graph has branched — reconcile with a merge migration "
        "(`alembic merge <heads>`) or fix the offending down_revision."
    )


@pytest.mark.integration
def test_migrations_have_single_base(script_directory: ScriptDirectory):
    """There should be exactly one base revision (down_revision = None)."""
    bases = script_directory.get_bases()
    assert len(bases) == 1, f"Expected a single base migration, found: {bases}"


@pytest.mark.integration
def test_migration_chain_is_linear_and_connected(script_directory: ScriptDirectory):
    """
    Following down_revision from the head must reach the base through every
    revision exactly once: a single unbroken line with no orphans and no merge
    revisions (a tuple down_revision indicates the graph forked and was merged).
    """
    all_revisions = {rev.revision for rev in script_directory.walk_revisions()}

    head = script_directory.get_current_head()
    chain = []
    current = head
    while current is not None:
        rev = script_directory.get_revision(current)
        chain.append(rev.revision)
        down = rev.down_revision
        assert not isinstance(down, tuple), (
            f"Revision {rev.revision} is a merge revision (multiple parents "
            f"{down}); the graph is not linear."
        )
        current = down

    orphans = all_revisions - set(chain)
    assert not orphans, (
        f"These revisions are not on the head->base chain: {orphans}. "
        "They are orphaned (disconnected from the main line)."
    )
    assert len(chain) == len(all_revisions), "A revision was visited more than once"


@pytest.mark.integration
def test_all_down_revisions_resolve(script_directory: ScriptDirectory):
    """
    Every non-base migration's down_revision must point at a revision that
    actually exists (catches a typo'd or deleted parent).
    """
    known = {rev.revision for rev in script_directory.walk_revisions()}
    for rev in script_directory.walk_revisions():
        downs = rev.down_revision
        if downs is None:
            continue
        if isinstance(downs, str):
            downs = (downs,)
        for parent in downs:
            assert parent in known, (
                f"Revision {rev.revision} references unknown down_revision "
                f"{parent!r}"
            )
