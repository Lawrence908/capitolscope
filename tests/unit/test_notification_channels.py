"""
Tests for Phase 4 multichannel bits: cadence normalization and the tier-gated
channel dispatcher's no-op behavior when unconfigured. No DB is used — the
dispatcher short-circuits before touching the session in these paths.
"""

from types import SimpleNamespace

import pytest

import schemas  # noqa: F401  (resolve circular-import ordering)
from domains.notifications.subscription_service import normalize_cadence

pytestmark = pytest.mark.unit


class TestNormalizeCadence:
    def test_valid_pass_through(self):
        assert normalize_cadence("instant") == "instant"
        assert normalize_cadence("daily") == "daily"
        assert normalize_cadence("weekly") == "weekly"

    def test_invalid_or_missing_defaults_to_instant(self):
        assert normalize_cadence("monthly") == "instant"  # legacy value, not a trade cadence
        assert normalize_cadence(None) == "instant"
        assert normalize_cadence("") == "instant"


class TestDispatcherGating:
    @pytest.mark.asyncio
    async def test_non_premium_is_skipped(self):
        from domains.notifications.channels import ChannelDispatcher

        d = ChannelDispatcher(session=None)  # session unused on these paths
        user = SimpleNamespace(id="u", is_premium=False)
        sub = SimpleNamespace(push_enabled=True, sms_enabled=True)
        assert await d.dispatch(user, sub, "t", "m") == {"push": "skipped", "sms": "skipped"}

    @pytest.mark.asyncio
    async def test_premium_enabled_but_unconfigured(self):
        from domains.notifications.channels import ChannelDispatcher

        d = ChannelDispatcher(session=None)
        user = SimpleNamespace(id="u", is_premium=True)
        sub = SimpleNamespace(push_enabled=True, sms_enabled=True)
        # No VAPID/Twilio creds in the test settings -> graceful no-op, not an error.
        result = await d.dispatch(user, sub, "t", "m")
        assert result["push"] in {"unconfigured", "lib_missing"}
        assert result["sms"] in {"unconfigured", "lib_missing"}

    @pytest.mark.asyncio
    async def test_channels_off_are_skipped(self):
        from domains.notifications.channels import ChannelDispatcher

        d = ChannelDispatcher(session=None)
        user = SimpleNamespace(id="u", is_premium=True)
        sub = SimpleNamespace(push_enabled=False, sms_enabled=False)
        assert await d.dispatch(user, sub, "t", "m") == {"push": "skipped", "sms": "skipped"}
