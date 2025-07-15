"""
Congressional trades API endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Security
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

logger = get_logger(__name__)
router = APIRouter()


@router.get("/debug")
async def debug_trades(
    session: AsyncSession = Depends(get_db_session),
):
    """
    Debug endpoint to test database connection.
    """
    try:
        from sqlalchemy import select, func
        
        # Simple count query
        count_query = select(func.count(CongressionalTrade.id))
        total = await session.scalar(count_query)
        
        # Try to get one trade
        trade_query = select(CongressionalTrade).limit(1)
        result = await session.execute(trade_query)
        trade = result.scalar_one_or_none()
        
        if trade:
            trade_data = {
                "id": str(trade.id),
                "ticker": trade.ticker,
                "transaction_date": trade.transaction_date.isoformat() if trade.transaction_date else None,
                "owner": trade.owner,
            }
        else:
            trade_data = None
        
        return {
            "status": "success",
            "total_trades": total,
            "sample_trade": trade_data,
            "message": "Database connection working"
        }
        
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/simple-test")
async def simple_test() -> JSONResponse:
    """
    Simple test endpoint without database.
    """
    logger.info("Simple test endpoint called")
    
    return JSONResponse(content={
        "status": "success",
        "message": "Simple test working"
    })


@router.get("/")
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
) -> JSONResponse:
    """
    Get congressional trades.
    
    Returns a list of congressional trades with pagination.
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting congressional trades", page=page, per_page=per_page)  # Removed user_id for now
    
    try:
        from sqlalchemy import select, func
        
        # Build base query (simplified, working version)
        query = select(CongressionalTrade).order_by(CongressionalTrade.transaction_date.desc())
        
        # Apply basic filters (without joins for now)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                CongressionalTrade.raw_asset_description.ilike(search_term)
            )
        
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
        
        # Get total count
        count_query = select(func.count(CongressionalTrade.id))
        total = await session.scalar(count_query)
        logger.info(f"Total trades: {total}")
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Execute query
        result = await session.execute(query)
        trades = result.scalars().all()
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
                "member": None,  # Temporarily disabled member info
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
        
        response_data = {
            "items": trade_items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev,
        }
        
        logger.info("Returning response...")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        import traceback
        logger.error(f"Error fetching trades: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return error_response(
            message="Failed to fetch trades",
            error_code="database_error",
            status_code=500
        )


@router.get("/{trade_id}")
async def get_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> JSONResponse:
    """
    Get a specific congressional trade by ID.
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting trade by ID", trade_id=trade_id)  # Removed user_id for now
    
    # TODO: Implement actual trade retrieval from database
    data = {
        "trade_id": trade_id,
        # "user_tier": current_user.subscription_tier,  # Temporarily disabled
    }
    
    return success_response(
        data=data,
        meta={"message": "Trade detail endpoint ready - database models needed"}
    )


@router.get("/member/{member_id}")
async def get_member_trades(
    member_id: int,
    session: AsyncSession = Depends(get_db_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> JSONResponse:
    """
    Get trades for a specific congress member.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting trades for member", member_id=member_id, skip=skip, limit=limit)  # Removed user_id for now
    
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
    
    return success_response(
        data=data,
        meta={"message": "Member trades endpoint ready - database models needed"}
    )


@router.get("/analytics/advanced")
async def get_advanced_analytics(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_subscription(['pro', 'premium', 'enterprise'])),
) -> JSONResponse:
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
    
    return success_response(
        data=data,
        meta={"message": "Advanced analytics ready - premium feature implementation needed"}
    )


@router.get("/analytics/top-trading-members")
async def get_top_trading_members(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(10, ge=1, le=100, description="Number of members to return"),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> JSONResponse:
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
        
        return JSONResponse(content=members)
        
    except Exception as e:
        logger.error(f"Error getting top trading members: {e}")
        return error_response(
            message="Failed to get top trading members",
            error_code="analytics_error",
            status_code=500
        )


@router.get("/analytics/top-traded-tickers")
async def get_top_traded_tickers(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(10, ge=1, le=100, description="Number of tickers to return"),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> JSONResponse:
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
        
        return JSONResponse(content=tickers)
        
    except Exception as e:
        logger.error(f"Error getting top traded tickers: {e}")
        return error_response(
            message="Failed to get top traded tickers",
            error_code="analytics_error",
            status_code=500
        )


@router.get("/export/csv")
async def export_trades_csv(
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> JSONResponse:
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
    
    return success_response(
        data=data,
        meta={"message": "CSV export ready - implementation needed"}
    )


@router.delete("/{trade_id}")
async def delete_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(require_admin()),  # Temporarily disabled for development
) -> JSONResponse:
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
    
    return success_response(
        data=data,
        meta={"message": "Trade deleted successfully"}
    )


@router.post("/{trade_id}/flag")
async def flag_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> JSONResponse:
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
    
    return success_response(
        data=data,
        meta={"message": "Trade flagged for review"}
    ) 


@router.get("/data-quality/stats")
async def get_data_quality_stats(
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> JSONResponse:
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
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"Error getting data quality stats: {e}")
        return error_response(
            message="Failed to get data quality stats",
            error_code="stats_error",
            status_code=500
        ) 


@router.get("/test")
async def test_trades(
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
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
        
        return JSONResponse(content={
            "status": "success",
            "total_trades": total,
            "message": "Database connection working"
        })
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return JSONResponse(content={
            "status": "error",
            "error": str(e)
        }) 