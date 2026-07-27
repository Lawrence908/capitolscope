"""
Congressional trades API endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Security, Path
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import joinedload
from datetime import datetime

from core.database import get_db_session
import logging
logger = logging.getLogger(__name__)
from core.responses import success_response, error_response, paginated_response
from core.auth import get_current_active_user, require_subscription, require_admin
from domains.users.models import User
from domains.congressional.models import CongressionalTrade, CongressMember
from domains.congressional.schemas import (
    CongressionalTradeSummary, CongressionalTradeDetail, 
    CongressionalTradeListResponse, CongressionalTradeDetailResponse,
    TradingStatistics, MarketPerformanceComparison
)
from schemas.base import ResponseEnvelope, PaginatedResponse, PaginationMeta, create_response
from domains.congressional.schemas import CongressionalTradeQuery

router = APIRouter()

# TODO: Update frontend TradeFilters to match CongressionalTradeQuery model
@router.get(
    "",
    response_model=ResponseEnvelope[PaginatedResponse[CongressionalTradeSummary]],
    responses={
        200: {"description": "Congressional trades retrieved successfully"},
        400: {"description": "Invalid parameters"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_trades(
    filters: CongressionalTradeQuery = Depends(),
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[PaginatedResponse[CongressionalTradeSummary]]:
    """
    Get congressional trades.
    Returns a list of congressional trades with pagination.
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting congressional trades: filters={filters.dict()}")
    logger.info(f"transaction_types received in endpoint: {filters.transaction_types} (type: {type(filters.transaction_types)})")
    try:
        from domains.congressional.crud import CongressionalTradeRepository
        from domains.congressional.models import CongressionalTrade, CongressMember
        
        # Use the service layer instead of direct CRUD calls
        from domains.congressional.services import CongressionalTradeService
        from domains.congressional.crud import CongressionalTradeRepository, CongressMemberRepository
        
        # Create repositories
        trade_repo = CongressionalTradeRepository(session)
        member_repo = CongressMemberRepository(session)
        
        # Create service
        trade_service = CongressionalTradeService(trade_repo, member_repo)
        
        logger.info(f"Calling trade_service.get_trades_with_filters with transaction_types: {filters.transaction_types}")
        trades, total_count = await trade_service.get_trades_with_filters(filters)
        logger.info(f"Service returned {len(trades)} trades (total_count={total_count}) for transaction_types: {filters.transaction_types}")
        
        # Calculate pagination
        pages = (total_count + filters.limit - 1) // filters.limit
        has_next = filters.page < pages
        has_prev = filters.page > 1
        
        # Create pagination meta
        pagination_meta = PaginationMeta(
            page=filters.page,
            per_page=filters.limit,
            total=total_count,
            pages=pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
        response = PaginatedResponse[
            CongressionalTradeSummary
        ](
            items=trades,
            meta=pagination_meta
        )
        return create_response(response)
    except Exception as e:
        import traceback
        logger.error(f"Error fetching trades: {e}")
        logger.error(traceback.format_exc())
        print(traceback.format_exc())  # Also print to console for Docker logs
        raise HTTPException(status_code=500, detail="Failed to fetch trades.")


@router.get(
    "/analytics/advanced",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Advanced analytics retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient subscription"},
        500: {"description": "Internal server error"}
    }
)
async def get_advanced_analytics(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_subscription(['PRO', 'PREMIUM', 'ENTERPRISE'])),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Get advanced trading analytics.
    
    **Premium Feature**: Requires Pro, Premium, or Enterprise subscription.
    """
    logger.info(f"Getting advanced analytics: user_id={current_user.id}")
    
    # TODO: Implement advanced analytics
    data = {
        "user_id": current_user.id,
        "subscription_tier": current_user.subscription_tier,
        "analytics": {
            "total_volume": 0,
            "performance_metrics": {},
            "correlation_analysis": {},
            "risk_assessment": {}
        },
    }
    
    return create_response(data=data)


@router.get(
    "/analytics/top-trading-members",
    response_model=ResponseEnvelope[List[TradingStatistics]],
    responses={
        200: {"description": "Top trading members retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_top_trading_members(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(10, ge=1, le=100, description="Number of members to return"),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[List[TradingStatistics]]:
    """
    Get top trading members by number of trades.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting top trading members: limit={limit}")  # Removed user_id for now
    
    try:
        from sqlalchemy import select, func, and_, or_
        
        # Query top trading members
        query = select(
            CongressMember.id,
            CongressMember.full_name,
            CongressMember.party,
            CongressMember.state,
            CongressMember.chamber,
            func.count(CongressionalTrade.id).label('trade_count'),
            func.sum(
                func.coalesce(
                    CongressionalTrade.amount_exact,
                    (CongressionalTrade.amount_min + CongressionalTrade.amount_max) / 2
                )
            ).label('total_value')
        ).join(CongressionalTrade).group_by(
            CongressMember.id,
            CongressMember.full_name,
            CongressMember.party,
            CongressMember.state,
            CongressMember.chamber
        ).order_by(func.count(CongressionalTrade.id).desc()).limit(limit)
        
        result = await session.execute(query)
        members = []
        
        for row in result:
            # Convert to TradingStatistics schema
            stats = TradingStatistics(
                member_id=row.id,
                member_name=row.full_name,
                member_party=row.party,
                member_chamber=row.chamber,
                member_state=row.state,
                total_trades=row.trade_count,
                total_value=int(row.total_value or 0),
                purchase_count=0,  # TODO: Calculate from actual data
                sale_count=0,      # TODO: Calculate from actual data
                purchase_value=0,   # TODO: Calculate from actual data
                sale_value=0       # TODO: Calculate from actual data
            )
            members.append(stats)
        
        return create_response(data=members)
        
    except Exception as e:
        logger.error(f"Error getting top trading members: {e}")
        return create_response(data=[], error="Failed to get top trading members")


@router.get(
    "/analytics/top-traded-tickers",
    response_model=ResponseEnvelope[List[Dict[str, Any]]],
    responses={
        200: {"description": "Top traded tickers retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_top_traded_tickers(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(10, ge=1, le=100, description="Number of tickers to return"),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[List[Dict[str, Any]]]:
    """
    Get top traded tickers by number of trades.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting top traded tickers: limit={limit}")  # Removed user_id for now
    
    try:
        from sqlalchemy import select, func, and_, or_
        
        # Query top traded tickers
        query = select(
            CongressionalTrade.ticker,
            func.count(CongressionalTrade.id).label('count'),
            func.sum(
                func.coalesce(
                    CongressionalTrade.amount_exact,
                    (CongressionalTrade.amount_min + CongressionalTrade.amount_max) / 2
                )
            ).label('total_value')
        ).filter(
            CongressionalTrade.ticker.isnot(None)
        ).group_by(CongressionalTrade.ticker).order_by(
            func.count(CongressionalTrade.id).desc()
        ).limit(limit)
        
        result = await session.execute(query)
        tickers = []
        
        for row in result:
            ticker = {
                "ticker": row.ticker,
                "count": row.count,
                "total_value": row.total_value or 0,
            }
            tickers.append(ticker)
        
        return create_response(data=tickers)
        
    except Exception as e:
        logger.error(f"Error getting top traded tickers: {e}")
        return create_response(data=None, error="Failed to get top traded tickers")


@router.get(
    "/analytics/party-distribution",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Party distribution retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_party_distribution(
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Get trading activity distribution by political party.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting party distribution")
    
    try:
        from sqlalchemy import select, func, and_, or_
        
        # Query party distribution
        query = select(
            CongressMember.party,
            func.count(CongressionalTrade.id).label('count')
        ).join(CongressionalTrade).group_by(CongressMember.party).order_by(
            func.count(CongressionalTrade.id).desc()
        )
        
        result = await session.execute(query)
        party_distribution = {}
        
        for row in result:
            party = row.party or 'Unknown'
            party_distribution[party] = row.count
        
        return create_response(data=party_distribution)
        
    except Exception as e:
        logger.error(f"Error getting party distribution: {e}")
        return create_response(data=None, error="Failed to get party distribution")


@router.get(
    "/analytics/chamber-distribution",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Chamber distribution retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_chamber_distribution(
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Get trading activity distribution by congressional chamber.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting chamber distribution")
    
    try:
        from sqlalchemy import select, func, and_, or_
        
        # Query chamber distribution
        query = select(
            CongressMember.chamber,
            func.count(CongressionalTrade.id).label('count')
        ).join(CongressionalTrade).group_by(CongressMember.chamber).order_by(
            func.count(CongressionalTrade.id).desc()
        )
        
        result = await session.execute(query)
        chamber_distribution = {}
        
        for row in result:
            chamber = row.chamber or 'Unknown'
            chamber_distribution[chamber] = row.count
        
        return create_response(data=chamber_distribution)
        
    except Exception as e:
        logger.error(f"Error getting chamber distribution: {e}")
        return create_response(data=None, error="Failed to get chamber distribution")


@router.get(
    "/analytics/amount-distribution",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Amount distribution retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_amount_distribution(
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Get trading activity distribution by amount ranges.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting amount distribution")
    
    try:
        from sqlalchemy import select, func, and_, or_, case
        
        # Define amount ranges
        amount_ranges = [
            (0, 1000, "$1 - $1,000"),
            (1001, 15000, "$1,001 - $15,000"),
            (15001, 50000, "$15,001 - $50,000"),
            (50001, 100000, "$50,001 - $100,000"),
            (100001, 250000, "$100,001 - $250,000"),
            (250001, 500000, "$250,001 - $500,000"),
            (500001, 1000000, "$500,001 - $1,000,000"),
            (1000001, None, "$1,000,001+")
        ]
        
        # Build case statement for amount ranges
        amount_case = case(
            *[
                (and_(
                    func.coalesce(CongressionalTrade.amount_exact, 
                                (CongressionalTrade.amount_min + CongressionalTrade.amount_max) / 2) >= min_val,
                    func.coalesce(CongressionalTrade.amount_exact, 
                                (CongressionalTrade.amount_min + CongressionalTrade.amount_max) / 2) <= (max_val or 999999999)
                ), label)
                for min_val, max_val, label in amount_ranges
            ],
            else_="Unknown"
        )
        
        # Query amount distribution
        query = select(
            amount_case.label('amount_range'),
            func.count(CongressionalTrade.id).label('count')
        ).group_by(amount_case).order_by(
            func.count(CongressionalTrade.id).desc()
        )
        
        result = await session.execute(query)
        amount_distribution = {}
        
        for row in result:
            amount_distribution[row.amount_range] = row.count
        
        return create_response(data=amount_distribution)
        
    except Exception as e:
        logger.error(f"Error getting amount distribution: {e}")
        return create_response(data=None, error="Failed to get amount distribution")


@router.get(
    "/analytics/volume-over-time",
    response_model=ResponseEnvelope[List[Dict[str, Any]]],
    responses={
        200: {"description": "Volume over time retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_volume_over_time(
    session: AsyncSession = Depends(get_db_session),
    period: str = Query('daily', description="Time period: daily, weekly, monthly"),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[List[Dict[str, Any]]]:
    """
    Get trading volume over time.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting volume over time: period={period}")
    
    try:
        from sqlalchemy import select, func, and_, or_, extract
        
        # Determine date truncation based on period
        if period == 'daily':
            date_trunc = func.date_trunc('day', CongressionalTrade.transaction_date)
        elif period == 'weekly':
            date_trunc = func.date_trunc('week', CongressionalTrade.transaction_date)
        elif period == 'monthly':
            date_trunc = func.date_trunc('month', CongressionalTrade.transaction_date)
        else:
            date_trunc = func.date_trunc('day', CongressionalTrade.transaction_date)
        
        # Query volume over time
        query = select(
            date_trunc.label('date'),
            func.count(CongressionalTrade.id).label('count'),
            func.sum(
                func.coalesce(
                    CongressionalTrade.amount_exact,
                    (CongressionalTrade.amount_min + CongressionalTrade.amount_max) / 2
                )
            ).label('volume')
        ).group_by(date_trunc).order_by(date_trunc.desc()).limit(30)
        
        result = await session.execute(query)
        volume_data = []
        
        for row in result:
            volume_data.append({
                "date": row.date.isoformat() if row.date else None,
                "count": row.count,
                "volume": int(row.volume or 0)
            })
        
        return create_response(data=volume_data)
        
    except Exception as e:
        logger.error(f"Error getting volume over time: {e}")
        return create_response(data=None, error="Failed to get volume over time")


@router.get(
    "/export/csv",
    responses={200: {"content": {"text/csv": {}}, "description": "CSV stream of trades"}},
)
async def export_trades_csv(
    member_id: Optional[str] = Query(None, description="Filter by congress member UUID"),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    limit: int = Query(5000, ge=1, le=50000, description="Max rows to export"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_subscription(['PRO', 'PREMIUM', 'ENTERPRISE'])),
):
    """Stream congressional trades as a CSV download. **Pro+**."""
    import csv
    import io
    from datetime import date as _date
    from uuid import UUID as _UUID
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from domains.congressional.models import CongressionalTrade

    logger.info(f"Exporting trades CSV: user={current_user.id} member={member_id} ticker={ticker} limit={limit}")

    q = (
        select(CongressionalTrade)
        .options(selectinload(CongressionalTrade.member))
        .order_by(CongressionalTrade.transaction_date.desc())
    )
    if member_id:
        try:
            _UUID(member_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="member_id must be a valid UUID")
        q = q.where(CongressionalTrade.member_id == member_id)
    if ticker:
        q = q.where(CongressionalTrade.ticker == ticker.upper())

    rows = (await session.execute(q.limit(limit))).scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "transaction_date", "notification_date", "member", "party", "chamber", "state",
        "ticker", "asset_name", "asset_type", "transaction_type", "owner",
        "amount_min_usd", "amount_max_usd", "amount_exact_usd",
    ])
    for t in rows:
        m = getattr(t, "member", None)
        writer.writerow([
            t.transaction_date.isoformat() if t.transaction_date else "",
            t.notification_date.isoformat() if t.notification_date else "",
            getattr(m, "display_name", None) or getattr(m, "full_name", "") or "",
            getattr(m, "party", "") or "",
            getattr(m, "chamber", "") or "",
            getattr(m, "state", "") or "",
            t.ticker or "",
            t.asset_name or "",
            t.asset_type or "",
            t.transaction_type or "",
            t.owner or "",
            t.amount_min / 100 if t.amount_min else "",
            t.amount_max / 100 if t.amount_max else "",
            t.amount_exact / 100 if t.amount_exact else "",
        ])

    filename = f"capitolscope-trades-{_date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete(
    "/{trade_id}",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Trade deleted successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Trade not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(require_admin()),  # Temporarily disabled for development
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Delete a congressional trade record.
    
    **Admin Only**: Requires enterprise subscription (admin privileges).
    """
    logger.info(f"Deleting trade: trade_id={trade_id}")  # Removed user_id for now
    
    # TODO: Implement trade deletion
    data = {
        "trade_id": trade_id,
        # "deleted_by": current_user.id,  # Temporarily disabled
    }
    
    return create_response(data=data)


@router.get(
    "/data-quality/stats",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Data quality statistics retrieved successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_data_quality_stats(
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Get data quality statistics for congressional trades.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting data quality stats")  # Removed user_id for now
    
    try:
        from sqlalchemy import select, func, and_, or_
        
        # Get total trades
        total_trades_query = select(func.count(CongressionalTrade.id))
        total_trades = await session.scalar(total_trades_query)
        
        # Get trades with ticker
        trades_with_ticker_query = select(func.count(CongressionalTrade.id)).filter(CongressionalTrade.ticker.isnot(None))
        trades_with_ticker = await session.scalar(trades_with_ticker_query)
        
        # Get trades without ticker
        trades_without_ticker = total_trades - trades_with_ticker
        
        # Calculate null ticker percentage
        null_ticker_percentage = (trades_without_ticker / total_trades * 100) if total_trades > 0 else 0
        
        # Get unique members
        unique_members_query = select(func.count(func.distinct(CongressionalTrade.member_id)))
        unique_members = await session.scalar(unique_members_query)
        
        # Get unique tickers
        unique_tickers_query = select(func.count(func.distinct(CongressionalTrade.ticker))).filter(CongressionalTrade.ticker.isnot(None))
        unique_tickers = await session.scalar(unique_tickers_query)
        
        # Get amount ranges distribution
        amount_ranges = {}
        if total_trades > 0:
            # Simple amount range analysis
            amount_ranges = {
                "$1,001 - $15,000": 0,
                "$15,001 - $50,000": 0,
                "$50,001 - $100,000": 0,
                "$100,001 - $250,000": 0,
                "$250,001 - $500,000": 0,
                "$500,001 - $1,000,000": 0,
                "$1,000,001 - $5,000,000": 0,
            }
        
        # Get party distribution
        party_distribution_query = select(
            CongressMember.party,
            func.count(CongressionalTrade.id)
        ).join(CongressMember).group_by(CongressMember.party)
        
        party_distribution = {}
        party_result = await session.execute(party_distribution_query)
        for party, count in party_result:
            party_name = "Democratic" if party == "D" else "Republican" if party == "R" else "Independent"
            party_distribution[party_name] = count
        
        # Get chamber distribution
        chamber_distribution_query = select(
            CongressMember.chamber,
            func.count(CongressionalTrade.id)
        ).join(CongressMember).group_by(CongressMember.chamber)
        
        chamber_distribution = {}
        chamber_result = await session.execute(chamber_distribution_query)
        for chamber, count in chamber_result:
            chamber_distribution[chamber] = count
        
        stats = {
            "total_trades": total_trades,
            "trades_with_ticker": trades_with_ticker,
            "trades_without_ticker": trades_without_ticker,
            "null_ticker_percentage": round(null_ticker_percentage, 2),
            "unique_members": unique_members,
            "unique_tickers": unique_tickers,
            "amount_ranges": amount_ranges,
            "party_distribution": party_distribution,
            "chamber_distribution": chamber_distribution,
        }
        
        return create_response(data=stats)
        
    except Exception as e:
        logger.error(f"Error getting data quality stats: {e}")
        return create_response(data=None, error="Failed to get data quality stats")


@router.get(
    "/data-quality/coverage",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Security-matching coverage retrieved successfully"},
        500: {"description": "Internal server error"},
    },
)
async def get_security_coverage(
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Security-matching coverage: how many trades are linked to a priced security
    (the ceiling on portfolio/mirror/signal accuracy), broken down by asset type.
    """
    try:
        from sqlalchemy import select, func

        total = await session.scalar(select(func.count(CongressionalTrade.id))) or 0
        matched = await session.scalar(
            select(func.count(CongressionalTrade.id)).where(CongressionalTrade.security_id.isnot(None))
        ) or 0
        untickered = await session.scalar(
            select(func.count(CongressionalTrade.id)).where(
                (CongressionalTrade.ticker.is_(None)) | (CongressionalTrade.ticker == "")
            )
        ) or 0

        # Per asset-type totals and matched counts.
        rows = (await session.execute(
            select(
                func.coalesce(CongressionalTrade.asset_type, "Unknown").label("asset_type"),
                func.count(CongressionalTrade.id).label("total"),
                func.count(CongressionalTrade.security_id).label("matched"),
            ).group_by(CongressionalTrade.asset_type)
        )).all()
        by_asset_type = sorted(
            [
                {
                    "asset_type": r.asset_type,
                    "total": int(r.total),
                    "matched": int(r.matched),
                    "match_rate": round(r.matched / r.total * 100, 1) if r.total else None,
                }
                for r in rows
            ],
            key=lambda x: x["total"],
            reverse=True,
        )

        from domains.securities.models import Security, DailyPrice
        securities_total = await session.scalar(select(func.count(Security.id))) or 0
        securities_priced = await session.scalar(
            select(func.count(func.distinct(DailyPrice.security_id)))
        ) or 0

        return create_response(data={
            "total_trades": int(total),
            "matched_trades": int(matched),
            "match_rate": round(matched / total * 100, 1) if total else 0.0,
            "untickered_trades": int(untickered),
            "securities_total": int(securities_total),
            "securities_priced": int(securities_priced),
            "by_asset_type": by_asset_type,
        })
    except Exception as e:
        logger.error(f"Error getting security coverage: {e}")
        return create_response(data=None, error="Failed to get security coverage")


@router.get(
    "/test",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Test successful"},
        500: {"description": "Test failed"}
    }
)
async def test_trades(
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Test endpoint to check database connectivity.
    """
    logger.info("Testing trades endpoint...")
    
    try:
        # Simple count query
        from sqlalchemy import select, func
        count_query = select(func.count(CongressionalTrade.id))
        total = await session.scalar(count_query)
        
        logger.info(f"Test successful - total trades: {total}")
        
        data = {
            "status": "success",
            "total_trades": total,
            "message": "Database connection working"
        }
        
        return create_response(data=data)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return create_response(data=None, error=str(e))


@router.get(
    "/member/{member_id}",
    response_model=ResponseEnvelope[PaginatedResponse[CongressionalTradeSummary]],
    responses={
        200: {"description": "Member trades retrieved successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Member not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_member_trades(
    member_id: str,  # Changed from int to str to accept UUID
    session: AsyncSession = Depends(get_db_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[PaginatedResponse[CongressionalTradeSummary]]:
    """
    Get trades for a specific congress member.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting trades for member: member_id={member_id}, skip={skip}, limit={limit}")
    
    # Enhanced features for authenticated users
    # premium_features = current_user.is_premium  # Temporarily disabled
    
    # TODO: Implement actual member trade retrieval from database
    data = {
        "member_id": member_id,
        "trades": [],
        "total": 0,
        "skip": skip,
        "limit": limit,
        # "premium_features": premium_features,  # Temporarily disabled
        # "user_tier": current_user.subscription_tier,  # Temporarily disabled
    }
    
    # Create pagination meta
    pagination_meta = PaginationMeta(
        page=1,
        per_page=limit,
        total=0,
        pages=1,
        has_next=False,
        has_prev=False
    )
    
    paginated_data = PaginatedResponse(
        items=[],
        meta=pagination_meta
    )
    
    return create_response(data=paginated_data)


@router.get(
    "/{trade_id}",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Trade details retrieved successfully"},
        404: {"description": "Trade not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_trade(
    trade_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[Dict[str, Any]]:
    """Get a single congressional trade by its UUID, with the member's details."""
    logger.info(f"Getting trade by ID: trade_id={trade_id}")
    from uuid import UUID as _UUID
    try:
        _UUID(trade_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Trade not found")

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from domains.congressional.models import CongressionalTrade

    row = (await session.execute(
        select(CongressionalTrade)
        .options(selectinload(CongressionalTrade.member))
        .where(CongressionalTrade.id == trade_id)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Trade not found")

    m = getattr(row, "member", None)
    return create_response(data={
        "id": str(row.id),
        "member_id": str(row.member_id),
        "member_name": getattr(m, "display_name", None) or getattr(m, "full_name", None),
        "party": getattr(m, "party", None),
        "state": getattr(m, "state", None),
        "chamber": getattr(m, "chamber", None),
        "ticker": row.ticker,
        "asset_name": row.asset_name,
        "asset_type": row.asset_type,
        "raw_asset_description": row.raw_asset_description,
        "transaction_type": row.transaction_type,
        "transaction_date": row.transaction_date.isoformat() if row.transaction_date else None,
        "notification_date": row.notification_date.isoformat() if row.notification_date else None,
        "amount_min": row.amount_min,
        "amount_max": row.amount_max,
        "amount_exact": row.amount_exact,
        "owner": row.owner,
        "document_url": row.document_url,
        "security_id": str(row.security_id) if row.security_id else None,
    })


@router.post(
    "/{trade_id}/flag",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "Trade flagged successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Trade not found"},
        500: {"description": "Internal server error"}
    }
)
async def flag_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Flag a trade for review.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Flagging trade: trade_id={trade_id}")  # Removed user_id for now
    
    # TODO: Implement trade flagging
    data = {
        "trade_id": trade_id,
        # "flagged_by": current_user.id,  # Temporarily disabled
        "flagged_at": "2025-01-01T00:00:00Z",
    }
    
    return create_response(data=data) 
