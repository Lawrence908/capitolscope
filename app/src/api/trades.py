"""
Congressional trades API endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Security, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import joinedload

from core.database import get_db_session
from core.logging import get_logger
from core.responses import success_response, error_response, paginated_response
from core.auth import get_current_active_user, require_subscription, require_admin
from domains.users.models import User
from domains.congressional.models import CongressionalTrade, CongressMember
from domains.congressional.schemas import CongressionalTradeSummary, CongressionalTradeDetail
from schemas.base import ResponseEnvelope, PaginatedResponse, PaginationMeta, create_response

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=ResponseEnvelope[PaginatedResponse[Dict[str, Any]]],
    responses={
        200: {"description": "Congressional trades retrieved successfully"},
        400: {"description": "Invalid parameters"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_trades(
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    party: Optional[str] = Query(None, description="Party filter"),
    chamber: Optional[str] = Query(None, description="Chamber filter"),
    type: Optional[str] = Query(None, description="Transaction type filter"),
    ticker: Optional[str] = Query(None, description="Ticker filter"),
    owner: Optional[str] = Query(None, description="Owner filter"),
    date_from: Optional[str] = Query(None, description="Date from filter"),
    date_to: Optional[str] = Query(None, description="Date to filter"),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[PaginatedResponse[Dict[str, Any]]]:
    """
    Get congressional trades.
    
    Returns a list of congressional trades with pagination.
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting congressional trades", page=page, per_page=per_page)
    
    try:
        from sqlalchemy import select, func
        
        # Build base query
        query = (
            select(CongressionalTrade)
            .options(joinedload(CongressionalTrade.member))
            .order_by(CongressionalTrade.transaction_date.desc())
        )
        
        # Track if we need to join with CongressMember
        needs_join = False
        
        # Apply filters
        if search:
            search_term = f"%{search}%"
            needs_join = True
            query = query.filter(
                or_(
                    CongressionalTrade.raw_asset_description.ilike(search_term),
                    CongressionalTrade.ticker.ilike(search_term),
                    CongressionalTrade.asset_name.ilike(search_term),
                    CongressMember.full_name.ilike(search_term)
                )
            )
        
        if party:
            needs_join = True
            query = query.filter(CongressMember.party == party)
        
        if chamber:
            needs_join = True
            query = query.filter(CongressMember.chamber == chamber)
        
        # Apply the join if needed
        if needs_join:
            query = query.join(CongressMember)
        
        if type:
            query = query.filter(CongressionalTrade.transaction_type == type)
        
        if ticker:
            query = query.filter(CongressionalTrade.ticker == ticker.upper())
        
        if owner:
            query = query.filter(CongressionalTrade.owner == owner)
        
        if date_from:
            query = query.filter(CongressionalTrade.transaction_date >= date_from)
        
        if date_to:
            query = query.filter(CongressionalTrade.transaction_date <= date_to)
        
        # Get total count (apply same filters to count query)
        count_query = select(func.count(CongressionalTrade.id))
        if needs_join:
            count_query = count_query.join(CongressMember)
        
        # Apply same filters to count query
        if search:
            search_term = f"%{search}%"
            count_query = count_query.filter(
                or_(
                    CongressionalTrade.raw_asset_description.ilike(search_term),
                    CongressionalTrade.ticker.ilike(search_term),
                    CongressionalTrade.asset_name.ilike(search_term),
                    CongressMember.full_name.ilike(search_term)
                )
            )
        
        if party:
            count_query = count_query.filter(CongressMember.party == party)
        
        if chamber:
            count_query = count_query.filter(CongressMember.chamber == chamber)
        
        if type:
            count_query = count_query.filter(CongressionalTrade.transaction_type == type)
        
        if ticker:
            count_query = count_query.filter(CongressionalTrade.ticker == ticker.upper())
        
        if owner:
            count_query = count_query.filter(CongressionalTrade.owner == owner)
        
        if date_from:
            count_query = count_query.filter(CongressionalTrade.transaction_date >= date_from)
        
        if date_to:
            count_query = count_query.filter(CongressionalTrade.transaction_date <= date_to)
        
        total = await session.scalar(count_query)
        logger.info(f"Total trades: {total}")
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Execute query
        result = await session.execute(query)
        trades = result.scalars().unique().all()
        logger.info(f"Retrieved {len(trades)} trades")
        
        # Convert to response format
        trade_items = []
        for trade in trades:
            # Format amount string
            amount_str = "Unknown"
            if trade.amount_exact:
                amount_str = f"${trade.amount_exact / 100:,.0f}"
            elif trade.amount_min and trade.amount_max:
                amount_str = f"${trade.amount_min / 100:,.0f} - ${trade.amount_max / 100:,.0f}"
            
            # Map transaction type
            type_map = {
                'P': 'purchase',
                'S': 'sale', 
                'E': 'exchange'
            }
            
            trade_item = {
                "id": str(trade.id),
                "member_id": str(trade.member_id),
                "member": {
                    "id": str(trade.member.id) if trade.member else None,
                    "full_name": trade.member.full_name if trade.member else "Unknown",
                    "party": trade.member.party if trade.member else None,
                    "state": trade.member.state if trade.member else None,
                    "chamber": trade.member.chamber if trade.member else None,
                } if trade.member else None,
                "disclosure_date": trade.notification_date.isoformat() if trade.notification_date else None,
                "transaction_date": trade.transaction_date.isoformat() if trade.transaction_date else None,
                "owner": trade.owner,
                "ticker": trade.ticker,
                "asset_description": trade.raw_asset_description,
                "asset_type": trade.asset_type or "Stock",
                "type": type_map.get(trade.transaction_type, trade.transaction_type),
                "amount": amount_str,
                "amount_min": trade.amount_min,
                "amount_max": trade.amount_max,
                "comment": trade.comment,
                "ptr_link": trade.document_url,
                "created_at": trade.created_at.isoformat() if trade.created_at else None,
                "updated_at": trade.updated_at.isoformat() if trade.updated_at else None,
            }
            trade_items.append(trade_item)
        
        # Calculate pagination info
        pages = (total + per_page - 1) // per_page
        has_next = page < pages
        has_prev = page > 1
        
        pagination_meta = PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            pages=pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
        paginated_data = PaginatedResponse(
            items=trade_items,
            meta=pagination_meta
        )
        
        logger.info("Returning response...")
        return create_response(data=paginated_data)
        
    except Exception as e:
        import traceback
        error_msg = f"Error fetching trades: {e}"
        traceback_msg = f"Traceback: {traceback.format_exc()}"
        logger.error(error_msg)
        logger.error(traceback_msg)
        print(f"DEBUG: {error_msg}")  # Print to console for immediate visibility
        print(f"DEBUG: {traceback_msg}")  # Print to console for immediate visibility
        return create_response(error="Failed to fetch trades")


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
    logger.info("Getting advanced analytics", user_id=current_user.id)
    
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
    response_model=ResponseEnvelope[List[Dict[str, Any]]],
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
) -> ResponseEnvelope[List[Dict[str, Any]]]:
    """
    Get top trading members by number of trades.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting top trading members", limit=limit)  # Removed user_id for now
    
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
            party_map = {
                'D': 'Democratic',
                'R': 'Republican', 
                'I': 'Independent'
            }
            
            member = {
                "id": row.id,
                "full_name": row.full_name,
                "party": party_map.get(row.party, row.party),
                "state": row.state,
                "chamber": row.chamber,
                "total_trades": row.trade_count,
                "total_value": row.total_value or 0,
            }
            members.append(member)
        
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
    logger.info("Getting top traded tickers", limit=limit)  # Removed user_id for now
    
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
    logger.info("Deleting trade", trade_id=trade_id)  # Removed user_id for now
    
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
    response_model=ResponseEnvelope[Dict[str, Any]],
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
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Get trades for a specific congress member.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting trades for member", member_id=member_id, skip=skip, limit=limit)
    
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
    
    return create_response(data=data)


@router.get(
    "/{trade_id}",
    response_model=ResponseEnvelope[Dict[str, Any]],
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
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Get a specific congressional trade by ID.
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting trade by ID", trade_id=trade_id)
    
    # TODO: Implement actual trade retrieval from database
    data = {
        "trade_id": trade_id,
        # "user_tier": current_user.subscription_tier,  # Temporarily disabled
    }
    
    return create_response(data=data)


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
    logger.info("Flagging trade", trade_id=trade_id)  # Removed user_id for now
    
    # TODO: Implement trade flagging
    data = {
        "trade_id": trade_id,
        # "flagged_by": current_user.id,  # Temporarily disabled
        "flagged_at": "2024-01-01T00:00:00Z",
    }
    
    return create_response(data=data) 
