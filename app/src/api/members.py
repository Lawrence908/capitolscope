"""
Congressional members API endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
import logging
logger = logging.getLogger(__name__)
from core.responses import success_response, error_response, paginated_response
from core.auth import get_current_active_user, require_admin
from domains.users.models import User
from domains.congressional.services import CongressMemberService, CongressAPIService
from domains.congressional.crud import CongressMemberRepository
from domains.congressional.schemas import (
    MemberQuery, CongressMemberDetail, CongressMemberSummary,
    CongressMemberListResponse, CongressMemberDetailResponse
)
from background.tasks import (
    sync_congressional_members, 
    seed_securities_database,
    fetch_stock_data_enhanced,
    import_congressional_data_csvs,
    enrich_congressional_member_data
)
from domains.congressional.models import CongressMember, CongressionalTrade
from schemas.base import ResponseEnvelope, PaginatedResponse, PaginationMeta, create_response


router = APIRouter()


@router.get(
    "/",
    response_model=ResponseEnvelope[PaginatedResponse[CongressMemberSummary]],
    responses={
        200: {"description": "Congressional members retrieved successfully"},
        400: {"description": "Invalid parameters"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def get_members(
    filters: MemberQuery = Depends(),
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[PaginatedResponse[CongressMemberSummary]]:
    """
    Get congressional members with filtering and pagination.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info(f"Getting congressional members: filters={filters.dict()}")
    
    try:
        # Use the service layer instead of direct SQL queries
        from domains.congressional.crud import CongressMemberRepository, CongressionalTradeRepository, MemberPortfolioRepository, MemberPortfolioPerformanceRepository
        from domains.congressional.services import CongressMemberService
        
        # Create repositories
        member_repo = CongressMemberRepository(session)
        trade_repo = CongressionalTradeRepository(session)
        portfolio_repo = MemberPortfolioRepository(session)
        performance_repo = MemberPortfolioPerformanceRepository(session)
        
        # Create service
        member_service = CongressMemberService(member_repo, trade_repo, portfolio_repo, performance_repo)
        
        # Get members with filters
        members, total = await member_service.get_members_with_filters(filters)
        
        logger.info(f"Found {len(members)} members out of {total} total")
        
        # Convert to response format
        member_items = []
        for member in members:
            # Get trade statistics for this member
            trade_stats = await member_service.member_repo.get_trading_statistics(member.id)
            
            member_item = CongressMemberSummary(
                id=member.id,
                bioguide_id=member.bioguide_id or "",
                first_name=member.first_name,
                last_name=member.last_name,
                full_name=member.full_name,
                party=member.party,
                state=member.state,
                district=member.district,
                chamber=member.chamber,
                office=getattr(member, 'office', None),
                phone=getattr(member, 'phone', None),
                url=getattr(member, 'website_url', None),
                image_url=getattr(member, 'image_url', None),
                twitter_account=getattr(member, 'twitter_account', None),
                facebook_account=getattr(member, 'facebook_url', None),
                youtube_account=None,
                in_office=getattr(member, 'is_active', True),
                next_election=getattr(member, 'next_election', None),
                trade_count=trade_stats.total_trades if trade_stats else 0,
                total_trade_value=int(trade_stats.total_value or 0),
                created_at=member.created_at.isoformat() if member.created_at else None,
                updated_at=member.updated_at.isoformat() if member.updated_at else None,
            )
            member_items.append(member_item)
        
        # Calculate pagination info
        pages = (total + filters.limit - 1) // filters.limit
        has_next = filters.page < pages
        has_prev = filters.page > 1
        
        pagination_meta = PaginationMeta(
            page=filters.page,
            per_page=filters.limit,
            total=total,
            pages=pages,
            has_next=has_next,
            has_prev=has_prev
        )
        paginated = PaginatedResponse[CongressMemberSummary](
            items=member_items,
            meta=pagination_meta
        )
        
        return create_response(paginated)
        
    except Exception as e:
        logger.error(f"Error retrieving members: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return create_response(None, error="Failed to retrieve congressional members")


@router.get(
    "/{member_id}",
    response_model=ResponseEnvelope[CongressMemberDetail],
    responses={
        200: {"description": "Member details retrieved successfully"},
        400: {"description": "Invalid member ID"},
        401: {"description": "Not authenticated"},
        404: {"description": "Member not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_member(
    member_id: str = Path(..., description="Member ID"),
    session: AsyncSession = Depends(get_db_session),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for development
) -> ResponseEnvelope[CongressMemberDetail]:
    """
    Get detailed information about a specific congressional member.
    """
    logger.info(f"Getting member by ID: member_id={member_id}")
    try:
        from uuid import UUID
        member_uuid = UUID(member_id)
        
        member_repo = CongressMemberRepository(session)
        member = await member_repo.get_by_id(member_uuid)
        if not member:
            return create_response(None, error="Member not found")
        
        # Calculate trade statistics for this member
        from sqlalchemy import select, func
        from domains.congressional.models import CongressionalTrade
        
        trade_stats_query = select(
            func.count(CongressionalTrade.id).label('trade_count'),
            func.sum(
                func.coalesce(
                    CongressionalTrade.amount_exact,
                    (CongressionalTrade.amount_min + CongressionalTrade.amount_max) / 2
                )
            ).label('total_value')
        ).where(CongressionalTrade.member_id == member_uuid)
        
        trade_stats_result = await session.execute(trade_stats_query)
        trade_stats = trade_stats_result.first()
        
        # Create member detail with calculated stats
        member_detail = CongressMemberDetail(
            id=member.id,
            first_name=member.first_name,
            last_name=member.last_name,
            full_name=member.full_name,
            party=member.party,
            state=member.state,
            district=member.district,
            chamber=member.chamber,
            email=member.email,
            phone=member.phone,
            office_address=member.office_address,
            bioguide_id=member.bioguide_id,
            congress_gov_id=member.congress_gov_id,
            congress_gov_url=member.congress_gov_url,
            image_url=member.image_url,
            image_attribution=member.image_attribution,
            last_api_update=member.last_api_update,
            term_start=member.term_start,
            term_end=member.term_end,
            congress_number=member.congress_number,
            education=member.education,
            committees=member.committees,
            leadership_roles=member.leadership_roles,
            twitter_handle=member.twitter_handle,
            facebook_url=member.facebook_url,
            website_url=member.website_url,
            seniority_rank=member.seniority_rank,
            vote_percentage=member.vote_percentage,
            influence_score=member.influence_score,
            fundraising_total=member.fundraising_total,
            pac_contributions=member.pac_contributions,
            wikipedia_url=member.wikipedia_url,
            ballotpedia_url=member.ballotpedia_url,
            opensecrets_url=member.opensecrets_url,
            govtrack_id=member.govtrack_id,
            votesmart_id=member.votesmart_id,
            fec_id=member.fec_id,
            trade_count=trade_stats.trade_count if trade_stats else 0,
            total_trade_value=int(trade_stats.total_value or 0),
            portfolio_value=None,  # TODO: Calculate portfolio value
            created_at=member.created_at.isoformat() if member.created_at else None,
            updated_at=member.updated_at.isoformat() if member.updated_at else None,
        )
        return create_response(member_detail)
    except Exception as e:
        logger.error(f"Error retrieving member {member_id}: {e}")
        return create_response(None, error="Failed to retrieve member details")


@router.get(
    "/search",
    response_model=ResponseEnvelope[PaginatedResponse[CongressMemberSummary]],
    responses={
        200: {"description": "Search results for congressional members"},
        400: {"description": "Invalid search parameters"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error"}
    }
)
async def search_members(
    filters: MemberQuery = Depends(),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[PaginatedResponse[CongressMemberSummary]]:
    """
    Search congressional members by name or other criteria.
    """
    logger.info(f"Searching members: filters={filters.dict()}, user_id={current_user.id}")
    try:
        member_repo = CongressMemberRepository(session)
        members = member_repo.search_members(filters.search, limit=filters.limit)
        member_items = [CongressMemberSummary.from_orm(member) for member in members]
        pagination_meta = PaginationMeta(
            page=filters.page,
            per_page=filters.limit,
            total=len(members),
            pages=1,
            has_next=False,
            has_prev=False
        )
        paginated = PaginatedResponse[CongressMemberSummary](
            items=member_items,
            meta=pagination_meta
        )
        return create_response(paginated)
    except Exception as e:
        logger.error(f"Error searching members: {e}")
        return create_response(None, error="Failed to search members")


@router.get(
    "/state/{state_code}",
    response_model=ResponseEnvelope[PaginatedResponse[CongressMemberSummary]],
    responses={
        200: {"description": "Members by state retrieved successfully"},
        400: {"description": "Invalid state code"},
        401: {"description": "Not authenticated"},
        404: {"description": "State not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_members_by_state(
    state_code: str = Path(..., description="Two-letter state code"),
    filters: MemberQuery = Depends(),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[PaginatedResponse[CongressMemberSummary]]:
    """
    Get all congressional members from a specific state.
    """
    logger.info(f"Getting members by state: state_code={state_code}, filters={filters.dict()}, user_id={current_user.id}")
    try:
        member_repo = CongressMemberRepository(session)
        members = member_repo.get_members_by_state(state_code.upper())
        member_items = [CongressMemberSummary.from_orm(member) for member in members]
        pagination_meta = PaginationMeta(
            page=filters.page,
            per_page=filters.limit,
            total=len(members),
            pages=1,
            has_next=False,
            has_prev=False
        )
        paginated = PaginatedResponse[CongressMemberSummary](
            items=member_items,
            meta=pagination_meta
        )
        return create_response(paginated)
    except Exception as e:
        logger.error(f"Error retrieving members for state {state_code}: {e}")
        return create_response(None, error=f"Failed to retrieve members for state {state_code}")


# Administrative endpoints
@router.post("/sync")
async def sync_members_from_api(
    background_tasks: BackgroundTasks,
    action: str = Query("sync-all", description="Sync action (sync-all, sync-state, enrich-existing)"),
    state: Optional[str] = Query(None, description="State code for sync-state action"),
    current_user: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Trigger sync of congressional members from Congress.gov API.
    """
    logger.info(f"Triggering member sync: action={action}, state={state}, user_id={current_user.id}")
    try:
        kwargs = {}
        if action == "sync-state" and state:
            kwargs["state"] = state.upper()
        background_tasks.add_task(sync_congressional_members.delay, action, **kwargs)
        data = {
            "action": action,
            "parameters": kwargs,
            "status": "queued",
            "message": f"Member sync ({action}) has been queued for processing"
        }
        return create_response(data)
    except Exception as e:
        logger.error(f"Error queuing sync task: {e}")
        return create_response(None, error="Failed to queue sync task")


@router.post("/sync/{bioguide_id}")
async def sync_specific_member(
    background_tasks: BackgroundTasks,
    bioguide_id: str = Path(..., description="Bioguide ID of member to sync"),
    current_user: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Sync a specific member from Congress.gov API.
    """
    logger.info(f"Triggering specific member sync: bioguide_id={bioguide_id}, user_id={current_user.id}")
    try:
        background_tasks.add_task(
            sync_congressional_members.delay, 
            "sync-member", 
            bioguide_id=bioguide_id
        )
        data = {
            "bioguide_id": bioguide_id,
            "action": "sync-member",
            "status": "queued",
            "message": f"Member sync for {bioguide_id} has been queued for processing"
        }
        return create_response(data)
    except Exception as e:
        logger.error(f"Error queuing member sync for {bioguide_id}: {e}")
        return create_response(None, error=f"Failed to queue sync for member {bioguide_id}")


@router.post("/comprehensive-ingestion")
async def trigger_comprehensive_ingestion(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin()),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Trigger comprehensive data ingestion workflow.
    """
    logger.info(f"Triggering comprehensive data ingestion: user_id={current_user.id}")
    try:
        from background.tasks import comprehensive_data_ingestion
        task_result = comprehensive_data_ingestion.delay()
        data = {
            "task_id": task_result.id,
            "action": "comprehensive-ingestion",
            "status": "queued",
            "message": "Comprehensive data ingestion workflow has been queued for processing",
            "workflow_steps": [
                "1. Sync congressional members",
                "2. Enrich member data",
                "3. Update stock prices", 
                "4. Recalculate portfolios"
            ]
        }
        return create_response(data)
    except Exception as e:
        logger.error(f"Error queuing comprehensive ingestion: {e}")
        return create_response(None, error="Failed to queue comprehensive ingestion workflow")


@router.post("/health-check")
async def health_check_apis(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin()),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Run health checks on external APIs.
    """
    logger.info(f"Triggering API health checks: user_id={current_user.id}")
    try:
        from background.tasks import health_check_congress_api
        task_result = health_check_congress_api.delay()
        data = {
            "task_id": task_result.id,
            "action": "health-check",
            "status": "queued",
            "message": "API health check has been queued for processing"
        }
        return create_response(data)
    except Exception as e:
        logger.error(f"Error queuing health check: {e}")
        return create_response(None, error="Failed to queue health check")


@router.get("/{member_id}/legislation")
async def get_member_legislation(
    member_id: int = Path(..., description="Member ID"),
    session: AsyncSession = Depends(get_db_session),
    legislation_type: str = Query("sponsored", description="Type: sponsored or cosponsored"),
    limit: int = Query(20, ge=1, le=100, description="Number of bills to return"),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Get legislation sponsored or cosponsored by a member.
    """
    logger.info(f"Getting member legislation: member_id={member_id}, legislation_type={legislation_type}, user_id={current_user.id}")
    if not current_user.is_premium:
        return create_response(None, error="This feature requires a premium subscription")
    try:
        member_repo = CongressMemberRepository(session)
        api_service = CongressAPIService(member_repo)
        member = member_repo.get_by_id(member_id)
        if not member or not member.bioguide_id:
            return create_response(None, error="Member not found or missing bioguide ID")
        legislation_data = await api_service.enrich_member_with_legislation(member_id)
        if legislation_type == "sponsored":
            legislation = legislation_data.get("sponsored_legislation", {})
        else:
            legislation = legislation_data.get("cosponsored_legislation", {})
        data = {
            "member_id": member_id,
            "member_name": member.full_name,
            "bioguide_id": member.bioguide_id,
            "legislation_type": legislation_type,
            "legislation": legislation,
            "total_bills": len(legislation.get("bills", [])),
            "user_tier": current_user.subscription_tier
        }
        return create_response(data)
    except Exception as e:
        logger.error(f"Error retrieving legislation for member {member_id}: {e}")
        return create_response(None, error="Failed to retrieve member legislation") 