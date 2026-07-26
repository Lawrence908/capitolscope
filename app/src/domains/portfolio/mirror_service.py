"""
Mirror portfolio service.

A "mirror portfolio" combines the congressional trades of one or more members
into a single synthetic portfolio. Congressional disclosures report a
transaction type (P/S/E) and a dollar *range*, never share counts, so positions
are reconstructed as follows (the "shares-from-price" model):

  * midpoint dollars of each trade / the security's price on the transaction
    date  ->  an approximate share delta
  * purchases add shares + cost basis; sales remove shares (proportional cost)
  * remaining shares are valued at the latest known price

This is necessarily an approximation (ranges, disclosure lag, only the ~37% of
trades matched to a security_id can be priced), but it yields a combined
holdings list and portfolio-level return that mirror how "copy congress"
products present the data.

The compute core (PriceBook, replay_positions, build_holdings) is pure and unit
tested; MirrorPortfolioService wires it to the database.
"""

import bisect
import logging
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Shares below this are treated as a closed position (float noise / dust).
_SHARE_EPSILON = 1e-6


# ---------------------------------------------------------------------------
# Pure compute core (no DB) -------------------------------------------------
# ---------------------------------------------------------------------------

class PriceBook:
    """In-memory price lookup keyed by security_id.

    Built from ``(security_id, price_date, close_price)`` rows. NOTE: in this
    schema ``daily_prices.close_price`` is stored as **whole dollars** (e.g.
    MSFT = 382), not cents, so prices are returned as-is. (Trade amounts, by
    contrast, are in cents — see ``midpoint_dollars``.)
    """

    def __init__(self, rows: List[tuple]):
        # security_id -> sorted list of (date, close_price_dollars)
        self._series: Dict[Any, List[tuple]] = {}
        for sid, d, close_price in rows:
            self._series.setdefault(sid, []).append((d, close_price))
        for sid in self._series:
            self._series[sid].sort(key=lambda x: x[0])

    def price_on_or_before(self, security_id, on_date: date) -> Optional[float]:
        """Close price (dollars) on ``on_date`` or the most recent prior day."""
        series = self._series.get(security_id)
        if not series:
            return None
        # index of the last entry with date <= on_date
        idx = bisect.bisect_right([d for d, _ in series], on_date) - 1
        if idx < 0:
            return None
        return float(series[idx][1])

    def latest(self, security_id) -> Optional[float]:
        """Most recent close price (dollars) for a security."""
        series = self._series.get(security_id)
        if not series:
            return None
        return float(series[-1][1])


def midpoint_dollars(trade) -> float:
    """Best available point estimate (dollars) of a trade's size from its range."""
    if getattr(trade, "amount_exact", None):
        return trade.amount_exact / 100.0
    lo = getattr(trade, "amount_min", None)
    hi = getattr(trade, "amount_max", None)
    if lo and hi:
        return (lo + hi) / 2 / 100.0
    if hi:
        return hi / 100.0
    if lo:
        return lo / 100.0
    return 0.0


def replay_positions(trades, pricebook: PriceBook) -> Dict[Any, Dict[str, Any]]:
    """Replay trades chronologically into net share positions per security.

    ``trades`` must expose ``security_id``, ``transaction_type`` (P/S/E),
    ``transaction_date`` and the amount fields. Exchanges (E) are ignored for
    valuation. Trades with no priceable date or zero dollars are skipped.
    """
    positions: Dict[Any, Dict[str, Any]] = {}

    for t in sorted(trades, key=lambda x: (x.transaction_date or date.min)):
        sid = t.security_id
        if sid is None:
            continue
        price = pricebook.price_on_or_before(sid, t.transaction_date)
        if not price or price <= 0:
            continue
        dollars = midpoint_dollars(t)
        if dollars <= 0:
            continue

        shares = dollars / price
        pos = positions.setdefault(sid, {"shares": 0.0, "cost_basis": 0.0, "realized": 0.0})
        ttype = (t.transaction_type or "").upper()

        if ttype == "P":
            pos["shares"] += shares
            pos["cost_basis"] += dollars
        elif ttype == "S":
            if pos["shares"] <= 0:
                continue  # a sale with nothing held (partial history) — ignore
            sold = min(shares, pos["shares"])
            avg_cost = pos["cost_basis"] / pos["shares"] if pos["shares"] else 0.0
            pos["cost_basis"] -= avg_cost * sold
            pos["shares"] -= sold
            pos["realized"] += (price - avg_cost) * sold
        # E (exchange) is intentionally neutral

    return positions


def build_holdings(
    positions: Dict[Any, Dict[str, Any]],
    pricebook: PriceBook,
    security_meta: Dict[Any, Dict[str, str]],
) -> Dict[str, Any]:
    """Value open positions at the latest price and roll up portfolio totals.

    ``security_meta`` maps security_id -> {"ticker", "name"}.
    """
    holdings: List[Dict[str, Any]] = []
    total_mv = 0.0
    total_cost = 0.0
    total_realized = 0.0

    for sid, pos in positions.items():
        total_realized += pos["realized"]
        if pos["shares"] <= _SHARE_EPSILON:
            continue
        last = pricebook.latest(sid)
        if not last:
            continue
        market_value = pos["shares"] * last
        cost_basis = pos["cost_basis"]
        unrealized = market_value - cost_basis
        return_pct = (unrealized / cost_basis * 100.0) if cost_basis > 0 else None
        meta = security_meta.get(sid, {})
        holdings.append({
            "security_id": str(sid),
            "ticker": meta.get("ticker"),
            "name": meta.get("name"),
            "shares": round(pos["shares"], 4),
            "cost_basis": round(cost_basis, 2),
            "current_price": round(last, 2),
            "market_value": round(market_value, 2),
            "unrealized_gain": round(unrealized, 2),
            "return_pct": round(return_pct, 2) if return_pct is not None else None,
        })
        total_mv += market_value
        total_cost += cost_basis

    holdings.sort(key=lambda h: h["market_value"], reverse=True)
    total_unrealized = total_mv - total_cost
    total_return = (total_unrealized / total_cost * 100.0) if total_cost > 0 else None

    return {
        "holdings": holdings,
        "totals": {
            "market_value": round(total_mv, 2),
            "cost_basis": round(total_cost, 2),
            "unrealized_gain": round(total_unrealized, 2),
            "realized_gain": round(total_realized, 2),
            "return_pct": round(total_return, 2) if total_return is not None else None,
            "holdings_count": len(holdings),
        },
    }


# ---------------------------------------------------------------------------
# DB-backed service ---------------------------------------------------------
# ---------------------------------------------------------------------------

class MirrorPortfolioService:
    """CRUD + on-the-fly holdings/returns computation for mirror portfolios."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---- CRUD -----------------------------------------------------------

    async def create(self, user_id, name: str, description: Optional[str],
                     member_ids: List[str]) -> "MirrorPortfolio":
        from domains.portfolio.models import MirrorPortfolio, MirrorPortfolioMember

        mirror = MirrorPortfolio(user_id=user_id, name=name, description=description)
        self.session.add(mirror)
        await self.session.flush()  # get mirror.id

        for mid in _dedupe(member_ids):
            self.session.add(MirrorPortfolioMember(mirror_portfolio_id=mirror.id, member_id=mid))

        await self.session.commit()
        await self.session.refresh(mirror)
        logger.info(f"Created mirror portfolio {mirror.id} for user {user_id} with {len(member_ids)} members")
        return mirror

    async def get(self, mirror_id, user_id) -> Optional["MirrorPortfolio"]:
        from sqlalchemy.orm import selectinload
        from domains.portfolio.models import MirrorPortfolio, MirrorPortfolioMember

        result = await self.session.execute(
            select(MirrorPortfolio)
            .where(and_(MirrorPortfolio.id == mirror_id, MirrorPortfolio.user_id == user_id))
            .options(selectinload(MirrorPortfolio.members).selectinload(MirrorPortfolioMember.member))
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id) -> List["MirrorPortfolio"]:
        from sqlalchemy.orm import selectinload
        from domains.portfolio.models import MirrorPortfolio, MirrorPortfolioMember

        result = await self.session.execute(
            select(MirrorPortfolio)
            .where(MirrorPortfolio.user_id == user_id)
            .options(selectinload(MirrorPortfolio.members).selectinload(MirrorPortfolioMember.member))
            .order_by(MirrorPortfolio.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, mirror_id, user_id) -> bool:
        mirror = await self.get(mirror_id, user_id)
        if not mirror:
            return False
        await self.session.delete(mirror)
        await self.session.commit()
        return True

    async def set_members(self, mirror_id, user_id, member_ids: List[str]) -> Optional["MirrorPortfolio"]:
        """Replace the member set of a mirror portfolio."""
        from domains.portfolio.models import MirrorPortfolioMember

        mirror = await self.get(mirror_id, user_id)
        if not mirror:
            return None
        for existing in list(mirror.members):
            await self.session.delete(existing)
        await self.session.flush()
        for mid in _dedupe(member_ids):
            self.session.add(MirrorPortfolioMember(mirror_portfolio_id=mirror.id, member_id=mid))
        await self.session.commit()
        return await self.get(mirror_id, user_id)

    # ---- Computation ----------------------------------------------------

    async def compute_holdings(self, member_ids: List) -> Dict[str, Any]:
        """Load the members' priced trades and reconstruct combined holdings."""
        from domains.congressional.models import CongressionalTrade
        from domains.securities.models import Security, DailyPrice

        if not member_ids:
            return build_holdings({}, PriceBook([]), {})

        trades = (await self.session.execute(
            select(CongressionalTrade).where(
                and_(
                    CongressionalTrade.member_id.in_(member_ids),
                    CongressionalTrade.security_id.isnot(None),
                )
            )
        )).scalars().all()
        if not trades:
            return build_holdings({}, PriceBook([]), {})

        security_ids = list({t.security_id for t in trades})

        price_rows = (await self.session.execute(
            select(DailyPrice.security_id, DailyPrice.price_date, DailyPrice.close_price)
            .where(DailyPrice.security_id.in_(security_ids))
        )).all()
        pricebook = PriceBook([(r.security_id, r.price_date, r.close_price) for r in price_rows])

        sec_rows = (await self.session.execute(
            select(Security.id, Security.ticker, Security.name).where(Security.id.in_(security_ids))
        )).all()
        security_meta = {r.id: {"ticker": r.ticker, "name": r.name} for r in sec_rows}

        positions = replay_positions(trades, pricebook)
        result = build_holdings(positions, pricebook, security_meta)
        result["meta"] = {
            "member_count": len(set(member_ids)),
            "priced_trades": len(trades),
        }
        return result


def _dedupe(seq: List) -> List:
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
