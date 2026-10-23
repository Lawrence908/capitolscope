"""
Thin async DB loaders that turn rows into the plain card dataclasses.

Read-only SELECTs. Amounts stay in CENTS. Late-filing stats exclude amended
filings (filing_status 'A') and negative lags (bad source dates).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .formatting import DISCLOSURE_LIMIT_DAYS, MemberCardData, TradeCardData, clean_asset_name


def parse_uuid(value: str) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


_TRADE_SQL = text(
    """
    SELECT t.ticker, s.ticker AS security_ticker, s.name AS security_name,
           t.asset_name, t.raw_asset_description, t.transaction_type,
           t.amount_min, t.amount_max, t.amount_exact,
           t.transaction_date, t.notification_date, t.filing_status,
           t.member_id,
           m.full_name, m.chamber, m.party, m.state, m.district
    FROM congressional_trades t
    JOIN congress_members m ON m.id = t.member_id
    LEFT JOIN securities s ON s.id = t.security_id
    WHERE t.id = :id
    """
)


@dataclass(frozen=True)
class LoadedTrade:
    card: TradeCardData
    member_id: str


async def load_trade(session: AsyncSession, trade_id: uuid.UUID) -> Optional[LoadedTrade]:
    row = (await session.execute(_TRADE_SQL, {"id": trade_id})).mappings().first()
    if row is None:
        return None
    ticker = (row["ticker"] or row["security_ticker"] or "").strip().upper() or None
    # Prefer the matched security's name; disclosure-parsed names are often garbled.
    name = row["security_name"] or clean_asset_name(row["raw_asset_description"]) or row["asset_name"]
    card = TradeCardData(
        member_name=row["full_name"] or "Unknown member",
        chamber=row["chamber"],
        party=row["party"],
        state=row["state"],
        district=row["district"],
        ticker=ticker,
        asset_name=clean_asset_name(name),
        transaction_type=row["transaction_type"],
        amount_min=row["amount_min"],
        amount_max=row["amount_max"],
        amount_exact=row["amount_exact"],
        transaction_date=row["transaction_date"],
        notification_date=row["notification_date"],
        filing_status=row["filing_status"],
    )
    return LoadedTrade(card=card, member_id=str(row["member_id"]))


_MEMBER_SQL = text(
    """
    SELECT m.full_name, m.chamber, m.party, m.state, m.district,
           (SELECT COUNT(*) FROM congressional_trades t WHERE t.member_id = m.id) AS trades,
           (SELECT AVG(t.notification_date - t.transaction_date)
              FROM congressional_trades t
             WHERE t.member_id = m.id
               AND COALESCE(t.filing_status, 'N') <> 'A'
               AND t.notification_date >= t.transaction_date) AS avg_days,
           (SELECT COUNT(*) FROM congressional_trades t
             WHERE t.member_id = m.id
               AND COALESCE(t.filing_status, 'N') <> 'A'
               AND t.notification_date - t.transaction_date > :limit) AS late,
           (SELECT MAX(t.notification_date) FROM congressional_trades t WHERE t.member_id = m.id) AS last_disclosed
    FROM congress_members m
    WHERE m.id = :id
    """
)


async def load_member(session: AsyncSession, member_id: uuid.UUID) -> Optional[MemberCardData]:
    row = (
        await session.execute(_MEMBER_SQL, {"id": member_id, "limit": DISCLOSURE_LIMIT_DAYS})
    ).mappings().first()
    if row is None:
        return None
    avg = row["avg_days"]
    return MemberCardData(
        name=row["full_name"] or "Unknown member",
        chamber=row["chamber"],
        party=row["party"],
        state=row["state"],
        district=row["district"],
        trade_count=int(row["trades"] or 0),
        avg_days=round(float(avg), 1) if avg is not None else None,
        late_count=int(row["late"] or 0),
        last_disclosed=row["last_disclosed"],
    )


@dataclass(frozen=True)
class AssetSummary:
    ticker: str
    name: Optional[str]
    trade_count: int
    member_count: int
    last_disclosed: Optional[date]


_ASSET_SQL = text(
    """
    SELECT COUNT(*) AS trades,
           COUNT(DISTINCT t.member_id) AS members,
           MAX(t.notification_date) AS last_disclosed,
           (SELECT s.name FROM securities s WHERE s.ticker = :ticker ORDER BY s.is_active DESC LIMIT 1) AS name
    FROM congressional_trades t
    WHERE t.ticker = :ticker
    """
)


async def load_asset(session: AsyncSession, ticker: str) -> Optional[AssetSummary]:
    row = (await session.execute(_ASSET_SQL, {"ticker": ticker})).mappings().first()
    if row is None or (not row["trades"] and not row["name"]):
        return None
    return AssetSummary(
        ticker=ticker,
        name=clean_asset_name(row["name"]),
        trade_count=int(row["trades"] or 0),
        member_count=int(row["members"] or 0),
        last_disclosed=row["last_disclosed"],
    )
