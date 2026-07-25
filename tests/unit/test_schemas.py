"""
Tests for shared enums and pagination schemas.

These enum *values* are the wire/DB representation (e.g. TradeOwner.SELF == "C")
and are relied on by ingestion, the API, and Alembic enum migrations, so
locking them down guards against an accidental rename breaking stored data.
"""

import pytest

from domains.base.schemas import (
    Chamber,
    PaginationParams,
    PoliticalParty,
    SubscriptionTier,
    TransactionType,
)
from domains.congressional.schemas import FilingStatus, TradeOwner

pytestmark = pytest.mark.unit


class TestEnumWireValues:
    def test_trade_owner_values(self):
        assert TradeOwner.SELF == "C"
        assert TradeOwner.SPOUSE == "SP"
        assert TradeOwner.JOINT == "JT"
        assert TradeOwner.DEPENDENT_CHILD == "DC"

    def test_transaction_type_values(self):
        assert TransactionType.PURCHASE == "P"
        assert TransactionType.SALE == "S"
        assert TransactionType.EXCHANGE == "E"

    def test_filing_status_values(self):
        assert FilingStatus.NEW == "N"
        assert FilingStatus.PARTIAL == "P"
        assert FilingStatus.AMENDMENT == "A"

    def test_political_party_values(self):
        assert PoliticalParty.DEMOCRAT == "D"
        assert PoliticalParty.REPUBLICAN == "R"
        assert PoliticalParty.INDEPENDENT == "I"

    def test_chamber_values(self):
        assert Chamber.HOUSE == "House"
        assert Chamber.SENATE == "Senate"

    def test_subscription_tiers(self):
        # Uppercase values matter: an Alembic migration renamed these and the API
        # tier-gating compares against them.
        assert {t.value for t in SubscriptionTier} == {
            "FREE",
            "PRO",
            "PREMIUM",
            "ENTERPRISE",
        }


class TestPaginationParams:
    @pytest.mark.parametrize(
        "page,size,expected_offset",
        [(1, 20, 0), (2, 20, 20), (3, 20, 40), (5, 10, 40)],
    )
    def test_offset_calculation(self, page, size, expected_offset):
        assert PaginationParams(page=page, size=size).offset == expected_offset

    def test_defaults(self):
        p = PaginationParams()
        assert p.page == 1
        assert p.size == 20
        assert p.offset == 0

    def test_rejects_non_positive_page(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PaginationParams(page=0)

    def test_rejects_oversized_page_size(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PaginationParams(size=101)
