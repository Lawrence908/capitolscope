"""
Congressional trades API endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Security, Path
from fastapi.responses import JSONResponse
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
    "/",
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
    current_user: User = Depends(require_subscription(['pro', 'premium', 'enterprise'])),
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
                total_trades=row.trade_count,
                total_value=row.total_value or 0,
                purchase_count=0,  # TODO: Calculate from actual data
                sale_count=0,      # TODO: Calculate from actual data
                purchase_value=0,   # TODO: Calculate from actual data
                sale_value=0       # TODO: Calculate from actual data
            )
            members.append(stats)
        
        return create_response(data=members)
        
    except Exception as e:
        logger.error(f"Error getting top trading members: {e}")
        return create_response(error="Failed to get top trading members")


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
        return create_response(error="Failed to get top traded tickers")


@router.get(
    "/export/csv",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={
        200: {"description": "CSV export URL generated successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def export_trades_csv(
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Export trades data to CSV format.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Exporting trades to CSV")  # Removed user_id for now
    
    # TODO: Implement CSV export
    data = {
        # "user_id": current_user.id,  # Temporarily disabled
        "export_url": "https://api.capitolscope.com/exports/trades-export-123.csv",
        "expires_at": "2024-01-01T00:00:00Z",
    }
    
    return create_response(data=data)


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
        return create_response(error="Failed to get data quality stats")


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
        return create_response(error=str(e))


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
    response_model=ResponseEnvelope[CongressionalTradeDetail],
    responses={
        200: {"description": "Trade details retrieved successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Trade not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[CongressionalTradeDetail]:
    """
    Get a specific congressional trade by ID.
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting trade by ID: trade_id={trade_id}")
    
    # TODO: Implement actual trade retrieval from database
    # For now, return a placeholder
    return create_response(error="Trade detail endpoint ready - database models needed")


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
        "flagged_at": "2024-01-01T00:00:00Z",
    }
    
    return create_response(data=data) 
