"""
CRUD integration tests for the (asynchronous) congressional repository layer.

These validate the `async_db_session` fixture and the async repository pattern
(AsyncSession + `await self.db.commit()`). Marked `db`; skipped without a
database. asyncio_mode=auto (see pyproject.toml) runs the async tests.
"""

import pytest

from domains.congressional.crud import CongressMemberRepository
from domains.congressional.schemas import CongressMemberCreate

pytestmark = [pytest.mark.integration, pytest.mark.db]


def _member(**overrides) -> CongressMemberCreate:
    data = {
        "first_name": "Jane",
        "last_name": "Doe",
        "full_name": "Jane Doe",
        "state": "CA",
        "bioguide_id": "D000001",
    }
    data.update(overrides)
    return CongressMemberCreate(**data)


class TestCongressMemberRepository:
    async def test_create_and_get_by_id(self, async_db_session):
        repo = CongressMemberRepository(async_db_session)
        created = await repo.create(_member())
        assert created.id is not None
        assert created.full_name == "Jane Doe"

        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.last_name == "Doe"

    async def test_get_by_bioguide_id(self, async_db_session):
        repo = CongressMemberRepository(async_db_session)
        await repo.create(_member(bioguide_id="B000123", full_name="Bob Smith",
                                   first_name="Bob", last_name="Smith"))
        found = await repo.get_by_bioguide_id("B000123")
        assert found is not None
        assert found.first_name == "Bob"

    async def test_missing_member_returns_none(self, async_db_session):
        import uuid

        repo = CongressMemberRepository(async_db_session)
        assert await repo.get_by_id(uuid.uuid4()) is None
