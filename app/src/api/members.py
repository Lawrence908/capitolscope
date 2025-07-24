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
from domains.congressional.models import CongressMember
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
        from sqlalchemy import select, func, and_, or_
        from sqlalchemy.orm import joinedload
        
        # Build base query
        query = select(CongressMember)
        
        # Apply filters
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    CongressMember.full_name.ilike(search_term),
                    CongressMember.first_name.ilike(search_term),
                    CongressMember.last_name.ilike(search_term)
                )
            )
        
        if filters.party:
            query = query.filter(CongressMember.party == filters.party)
        
        if filters.chamber:
            query = query.filter(CongressMember.chamber == filters.chamber)
        
        if filters.state:
            query = query.filter(CongressMember.state == filters.state.upper())
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query)
        
        # Apply pagination
        offset = (filters.page - 1) * filters.limit
        query = query.offset(offset).limit(filters.limit)
        
        # Execute query
        result = await session.execute(query)
        members = result.scalars().unique().all()
        
        # Convert to response format
        member_items = []
        for member in members:
            # Map party values
            party_map = {
                'D': 'Democratic',
                'R': 'Republican', 
                'I': 'Independent'
            }
            
            member_item = CongressMemberSummary(
                id=member.id,
                bioguide_id=member.bioguide_id or "",
                first_name=member.first_name,
                last_name=member.last_name,
                full_name=member.full_name,
                party=party_map.get(member.party, member.party),
                state=member.state,
                district=member.district,
                chamber=member.chamber,
                office=getattr(member, 'office', None),
                phone=member.phone,
                url=member.website_url,
                image_url=member.image_url,
                twitter_account=member.twitter_handle,
                facebook_account=member.facebook_url,
                youtube_account=None,
                in_office=getattr(member, 'is_active', True),
                next_election=getattr(member, 'next_election', None),
                total_trades=getattr(member, 'total_trades', None),
                total_value=getattr(member, 'total_value', None),
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
    member_id: int = Path(..., description="Member ID"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ResponseEnvelope[CongressMemberDetail]:
    """
    Get detailed information about a specific congressional member.
    """
    logger.info(f"Getting member by ID: member_id={member_id}, user_id={current_user.id}")
    try:
        member_repo = CongressMemberRepository(session)
        member = member_repo.get_by_id(member_id)
        if not member:
            return create_response(None, error="Member not found")
        analytics = None
        if current_user.is_premium:
            analytics = {
                "trade_count": 0,
                "total_trade_value": 0,
                "portfolio_value": 0
            }
        member_detail = CongressMemberDetail(
            member=member.dict(),
            analytics=analytics,
            user_tier=current_user.subscription_tier,
            premium_features=current_user.is_premium
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