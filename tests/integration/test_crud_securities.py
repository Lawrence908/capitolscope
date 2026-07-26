"""
CRUD integration tests for the (synchronous) securities domain.

These exercise the real CRUDBase machinery against a migrated Postgres via the
`db_session` fixture. They are the reference example for writing further CRUD
tests. Marked `db` so they are skipped when no database is available.
"""

import pytest

from domains.securities.crud import AssetTypeCRUD, SectorCRUD
from domains.securities.schemas import (
    AssetTypeCreate,
    AssetTypeUpdate,
    SectorCreate,
)

pytestmark = [pytest.mark.integration, pytest.mark.db]


class TestAssetTypeCRUD:
    def test_create_and_get(self, db_session):
        crud = AssetTypeCRUD(db_session)
        created = crud.create(
            AssetTypeCreate(code="EQ", name="Equity", category="equity", risk_level=3)
        )
        assert created.id is not None
        assert created.code == "EQ"

        fetched = crud.get(created.id)
        assert fetched is not None
        assert fetched.name == "Equity"

    def test_get_by_code(self, db_session):
        crud = AssetTypeCRUD(db_session)
        crud.create(AssetTypeCreate(code="BND", name="Bond", category="bond"))
        found = crud.get_by_code("BND")
        assert found is not None
        assert found.name == "Bond"

    def test_update(self, db_session):
        crud = AssetTypeCRUD(db_session)
        created = crud.create(AssetTypeCreate(code="ETF", name="ETF old"))
        updated = crud.update(created, AssetTypeUpdate(name="ETF new"))
        assert updated.name == "ETF new"
        assert crud.get(created.id).name == "ETF new"

    def test_delete(self, db_session):
        crud = AssetTypeCRUD(db_session)
        created = crud.create(AssetTypeCreate(code="OPT", name="Option"))
        assert crud.delete(created.id) is True
        assert crud.get(created.id) is None

    def test_count_reflects_inserts(self, db_session):
        crud = AssetTypeCRUD(db_session)
        before = crud.count()
        crud.create(AssetTypeCreate(code="C1", name="Cash"))
        crud.create(AssetTypeCreate(code="C2", name="Crypto"))
        assert crud.count() == before + 2


class TestSectorCRUD:
    def test_create_and_lookup_by_name_and_code(self, db_session):
        crud = SectorCRUD(db_session)
        created = crud.create(
            SectorCreate(gics_code="45", name="Information Technology")
        )
        assert created.id is not None
        assert crud.get_by_name("Information Technology").gics_code == "45"
        assert crud.get_by_gics_code("45").name == "Information Technology"

    @pytest.mark.xfail(
        reason="BUG: SectorCRUD.get_top_level_sectors()/get_sub_sectors() filter "
        "Sector.parent_sector_id, but the model column is "
        "parent_sector_gics_code — the attribute does not exist, so these "
        "methods always raise AttributeError. Fix the column reference to make "
        "this pass.",
        strict=False,
        raises=AttributeError,
    )
    def test_top_level_sectors_have_no_parent(self, db_session):
        crud = SectorCRUD(db_session)
        crud.create(SectorCreate(gics_code="10", name="Energy"))
        top = crud.get_top_level_sectors()
        assert "10" in {s.gics_code for s in top}


class TestTransactionalIsolation:
    """
    Guards the rollback behaviour of db_session: data written in one test must
    not leak into another. The two tests below insert the *same* primary key;
    if isolation were broken the second would hit a unique-violation.
    """

    def test_isolation_first_insert(self, db_session):
        AssetTypeCRUD(db_session).create(
            AssetTypeCreate(code="ISO", name="Isolation probe")
        )
        assert AssetTypeCRUD(db_session).get_by_code("ISO") is not None

    def test_isolation_second_insert_sees_clean_state(self, db_session):
        # If the previous test's row survived, get_by_code would find it.
        assert AssetTypeCRUD(db_session).get_by_code("ISO") is None
        AssetTypeCRUD(db_session).create(
            AssetTypeCreate(code="ISO", name="Isolation probe 2")
        )
