"""
Per-tier usage quotas (Phase 7b monetization).

The Stripe lifecycle keeps ``user.subscription_tier`` current; this module turns
that tier into enforceable caps on how many of a resource a user may create.
``-1`` means unlimited. Enforced at the API create endpoints via ``enforce_quota``.
"""

import logging
from typing import Dict

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Initial caps (no explicit numbers in PRICING_TIERS yet — sensible defaults that
# let Free users try alerts but create upgrade pressure). -1 = unlimited.
TIER_LIMITS: Dict[str, Dict[str, int]] = {
    "FREE": {"alert_rules": 3, "mirror_portfolios": 0},
    "PRO": {"alert_rules": 25, "mirror_portfolios": 5},
    "PREMIUM": {"alert_rules": -1, "mirror_portfolios": -1},
    "ENTERPRISE": {"alert_rules": -1, "mirror_portfolios": -1},
}


def _tier_key(tier) -> str:
    """Normalize a SubscriptionTier enum / string to an uppercase key."""
    return str(getattr(tier, "value", tier)).upper()


def tier_limit(tier, resource: str) -> int:
    """The cap for ``resource`` at ``tier`` (-1 = unlimited, defaults to FREE)."""
    return TIER_LIMITS.get(_tier_key(tier), TIER_LIMITS["FREE"]).get(resource, 0)


async def current_usage(session: AsyncSession, user_id, resource: str) -> int:
    """Count how many of ``resource`` the user currently owns."""
    if resource == "alert_rules":
        from domains.notifications.models import TradeAlertRule
        model = TradeAlertRule
    elif resource == "mirror_portfolios":
        from domains.portfolio.models import MirrorPortfolio
        model = MirrorPortfolio
    else:
        return 0
    return int((await session.execute(
        select(func.count()).select_from(model).where(model.user_id == user_id)
    )).scalar() or 0)


async def enforce_quota(session: AsyncSession, user, resource: str) -> None:
    """Raise 403 if creating another ``resource`` would exceed the user's tier cap."""
    limit = tier_limit(user.subscription_tier, resource)
    if limit < 0:
        return  # unlimited
    used = await current_usage(session, user.id, resource)
    if used >= limit:
        tier = _tier_key(user.subscription_tier)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"You've reached your {tier.title()} plan limit of {limit} "
                f"{resource.replace('_', ' ')}. Upgrade to create more."
            ),
        )


async def usage_summary(session: AsyncSession, user) -> Dict[str, Dict[str, int]]:
    """Per-resource {used, limit} for the current user (for the frontend paywall UX)."""
    out: Dict[str, Dict[str, int]] = {}
    for resource in ("alert_rules", "mirror_portfolios"):
        out[resource] = {
            "used": await current_usage(session, user.id, resource),
            "limit": tier_limit(user.subscription_tier, resource),
        }
    return out
