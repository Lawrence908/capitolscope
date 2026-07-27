"""
Tests for per-tier usage quotas (core.quotas, Phase 7b).
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import schemas  # noqa: F401  (resolve circular-import ordering)
from core import quotas

pytestmark = pytest.mark.unit


class TestTierLimit:
    def test_known_tiers(self):
        assert quotas.tier_limit("FREE", "alert_rules") == 3
        assert quotas.tier_limit("PRO", "alert_rules") == 25
        assert quotas.tier_limit("PREMIUM", "alert_rules") == -1
        assert quotas.tier_limit("PRO", "mirror_portfolios") == 5

    def test_unknown_tier_defaults_to_free(self):
        assert quotas.tier_limit("BOGUS", "alert_rules") == 3

    def test_accepts_enum_like_value(self):
        assert quotas.tier_limit(SimpleNamespace(value="PRO"), "mirror_portfolios") == 5


class TestEnforceQuota:
    def _user(self, tier):
        return SimpleNamespace(id="u1", subscription_tier=tier)

    @pytest.mark.asyncio
    async def test_under_limit_passes(self, monkeypatch):
        async def fake(_s, _u, _r):
            return 2
        monkeypatch.setattr(quotas, "current_usage", fake)
        await quotas.enforce_quota(None, self._user("FREE"), "alert_rules")  # 2 < 3

    @pytest.mark.asyncio
    async def test_at_limit_raises_403(self, monkeypatch):
        async def fake(_s, _u, _r):
            return 3
        monkeypatch.setattr(quotas, "current_usage", fake)
        with pytest.raises(HTTPException) as ei:
            await quotas.enforce_quota(None, self._user("FREE"), "alert_rules")
        assert ei.value.status_code == 403
        assert "limit" in ei.value.detail.lower()

    @pytest.mark.asyncio
    async def test_unlimited_never_raises(self, monkeypatch):
        async def fake(_s, _u, _r):
            return 9999
        monkeypatch.setattr(quotas, "current_usage", fake)
        await quotas.enforce_quota(None, self._user("PREMIUM"), "alert_rules")  # -1

    @pytest.mark.asyncio
    async def test_free_cannot_create_mirror(self, monkeypatch):
        async def fake(_s, _u, _r):
            return 0
        monkeypatch.setattr(quotas, "current_usage", fake)
        with pytest.raises(HTTPException):  # FREE mirror limit is 0
            await quotas.enforce_quota(None, self._user("FREE"), "mirror_portfolios")
