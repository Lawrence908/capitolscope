"""
Congressional members API endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from core.logging import get_logger
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

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=CongressMemberListResponse)
async def get_members(
    session: AsyncSession = Depends(get_db_session),
    skip: int = Query(0, ge=0, description="Number of members to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of members to return"),
    chamber: Optional[str] = Query(None, description="Filter by chamber (House/Senate)"),
    party: Optional[str] = Query(None, description="Filter by party (D/R/I)"),
    state: Optional[str] = Query(None, description="Filter by state code"),
    search: Optional[str] = Query(None, description="Search by name"),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    Get congressional members with filtering and pagination.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting congressional members", skip=skip, limit=limit, 
               chamber=chamber, party=party, state=state, search=search, user_id=current_user.id)
    
    try:
        # Initialize repository
        member_repo = CongressMemberRepository(session)
        
        # Build query
        from domains.congressional.schemas import Chamber, PoliticalParty
        
        query = MemberQuery(
            page=(skip // limit) + 1,
            limit=limit,
            chambers=[Chamber(chamber)] if chamber else None,
            parties=[PoliticalParty(party)] if party else None,
            states=[state.upper()] if state else None,
            search=search,
            include_trade_stats=current_user.is_premium
        )
        
        # Get members
        members, total = member_repo.list_members(query)
        
        data = {
            "members": [member.dict() for member in members],
            "total": total,
            "page": query.page,
            "limit": query.limit,
            "filters": {
                "chamber": chamber,
                "party": party,
                "state": state,
                "search": search
            },
            "user_tier": current_user.subscription_tier,
            "premium_features": current_user.is_premium
        }
        
        return success_response(
            data=data,
            meta={"message": f"Retrieved {len(members)} of {total} members"}
        )
        
    except Exception as e:
        logger.error(f"Error retrieving members: {e}")
        return error_response(
            message="Failed to retrieve congressional members",
            error_code="members_retrieval_failed"
        )


@router.get("/{member_id}", response_model=CongressMemberDetailResponse)
async def get_member(
    member_id: int = Path(..., description="Member ID"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    Get detailed information about a specific congressional member.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting member by ID", member_id=member_id, user_id=current_user.id)
    
    try:
        # Initialize repository
        member_repo = CongressMemberRepository(session)
        
        # Get member profile
        member = member_repo.get_by_id(member_id)
        if not member:
            return error_response(
                message="Member not found",
                error_code="member_not_found",
                status_code=404
            )
        
        # Get analytics for premium users (placeholder for now)
        analytics = None
        if current_user.is_premium:
            # TODO: Implement analytics retrieval
            analytics = {
                "trade_count": 0,
                "total_trade_value": 0,
                "portfolio_value": 0
            }
        
        data = {
            "member": member.dict(),
            "analytics": analytics if analytics else None,
            "user_tier": current_user.subscription_tier,
            "premium_features": current_user.is_premium
        }
        
        return success_response(
            data=data,
            meta={"message": "Member details retrieved successfully"}
        )
        
    except Exception as e:
        logger.error(f"Error retrieving member {member_id}: {e}")
        return error_response(
            message="Failed to retrieve member details",
            error_code="member_not_found",
            status_code=404 if "not found" in str(e).lower() else 500
        )


@router.get("/search")
async def search_members(
    q: str = Query(..., min_length=1, description="Search query"),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    Search congressional members by name or other criteria.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Searching members", query=q, limit=limit, user_id=current_user.id)
    
    try:
        # Initialize repository
        member_repo = CongressMemberRepository(session)
        
        # Perform search
        members = member_repo.search_members(q, limit=limit)
        
        data = {
            "query": q,
            "results": [member.dict() for member in members],
            "total": len(members),
            "limit": limit,
            "user_tier": current_user.subscription_tier,
        }
        
        return success_response(
            data=data,
            meta={"message": f"Found {len(members)} members matching '{q}'"}
        )
        
    except Exception as e:
        logger.error(f"Error searching members: {e}")
        return error_response(
            message="Failed to search members",
            error_code="search_failed"
        )


@router.get("/state/{state_code}")
async def get_members_by_state(
    state_code: str = Path(..., description="Two-letter state code"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    Get all congressional members from a specific state.
    
    **Authenticated Feature**: Requires user authentication.
    """
    logger.info("Getting members by state", state_code=state_code, user_id=current_user.id)
    
    try:
        # Initialize repository
        member_repo = CongressMemberRepository(session)
        
        # Get members by state
        members = member_repo.get_members_by_state(state_code.upper())
        
        data = {
            "state_code": state_code.upper(),
            "members": [member.dict() for member in members],
            "total": len(members),
            "user_tier": current_user.subscription_tier,
        }
        
        return success_response(
            data=data,
            meta={"message": f"Retrieved {len(members)} members from {state_code.upper()}"}
        )
        
    except Exception as e:
        logger.error(f"Error retrieving members for state {state_code}: {e}")
        return error_response(
            message=f"Failed to retrieve members for state {state_code}",
            error_code="state_members_failed"
        )


# Administrative endpoints
@router.post("/sync")
async def sync_members_from_api(
    background_tasks: BackgroundTasks,
    action: str = Query("sync-all", description="Sync action (sync-all, sync-state, enrich-existing)"),
    state: Optional[str] = Query(None, description="State code for sync-state action"),
    current_user: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Trigger sync of congressional members from Congress.gov API.
    
    **Admin Only**: Requires administrator permissions.
    """
    logger.info("Triggering member sync", action=action, state=state, user_id=current_user.id)
    
    try:
        # Add background task for sync
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
        
        return success_response(
            data=data,
            meta={"message": "Sync task queued successfully"}
        )
        
    except Exception as e:
        logger.error(f"Error queuing sync task: {e}")
        return error_response(
            message="Failed to queue sync task",
            error_code="sync_queue_failed"
        )


@router.post("/sync/{bioguide_id}")
async def sync_specific_member(
    background_tasks: BackgroundTasks,
    bioguide_id: str = Path(..., description="Bioguide ID of member to sync"),
    current_user: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Sync a specific member from Congress.gov API.
    
    **Admin Only**: Requires administrator permissions.
    """
    logger.info("Triggering specific member sync", bioguide_id=bioguide_id, user_id=current_user.id)
    
    try:
        # Add background task for specific member sync
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
        
        return success_response(
            data=data,
            meta={"message": "Member sync task queued successfully"}
        )
        
    except Exception as e:
        logger.error(f"Error queuing member sync for {bioguide_id}: {e}")
        return error_response(
            message=f"Failed to queue sync for member {bioguide_id}",
            error_code="member_sync_queue_failed"
        )


@router.post("/comprehensive-ingestion")
async def trigger_comprehensive_ingestion(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin()),
) -> JSONResponse:
    """
    Trigger comprehensive data ingestion workflow.
    
    This endpoint starts the complete data ingestion process that includes:
    1. Syncing congressional members from Congress.gov
    2. Enriching member data with legislation
    3. Updating stock prices
    4. Recalculating portfolios
    
    **Admin Only**: Requires administrator permissions.
    """
    logger.info("Triggering comprehensive data ingestion", user_id=current_user.id)
    
    try:
        from background.tasks import comprehensive_data_ingestion
        
        # Add background task for comprehensive ingestion
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
        
        return success_response(
            data=data,
            meta={"message": "Comprehensive ingestion workflow queued successfully"}
        )
        
    except Exception as e:
        logger.error(f"Error queuing comprehensive ingestion: {e}")
        return error_response(
            message="Failed to queue comprehensive ingestion workflow",
            error_code="comprehensive_ingestion_queue_failed"
        )


@router.post("/health-check")
async def health_check_apis(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin()),
) -> JSONResponse:
    """
    Run health checks on external APIs.
    
    **Admin Only**: Requires administrator permissions.
    """
    logger.info("Triggering API health checks", user_id=current_user.id)
    
    try:
        from background.tasks import health_check_congress_api
        
        # Add background task for health check
        task_result = health_check_congress_api.delay()
        
        data = {
            "task_id": task_result.id,
            "action": "health-check",
            "status": "queued",
            "message": "API health check has been queued for processing"
        }
        
        return success_response(
            data=data,
            meta={"message": "Health check task queued successfully"}
        )
        
    except Exception as e:
        logger.error(f"Error queuing health check: {e}")
        return error_response(
            message="Failed to queue health check",
            error_code="health_check_queue_failed"
        )


@router.get("/{member_id}/legislation")
async def get_member_legislation(
    member_id: int = Path(..., description="Member ID"),
    session: AsyncSession = Depends(get_db_session),
    legislation_type: str = Query("sponsored", description="Type: sponsored or cosponsored"),
    limit: int = Query(20, ge=1, le=100, description="Number of bills to return"),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    Get legislation sponsored or cosponsored by a member.
    
    **Premium Feature**: Enhanced data for premium users.
    """
    logger.info("Getting member legislation", member_id=member_id, 
               legislation_type=legislation_type, user_id=current_user.id)
    
    if not current_user.is_premium:
        return error_response(
            message="This feature requires a premium subscription",
            error_code="premium_required",
            status_code=403
        )
    
    try:
        # Initialize services
        member_repo = CongressMemberRepository(session)
        api_service = CongressAPIService(member_repo)
        
        # Get member
        member = member_repo.get_by_id(member_id)
        if not member or not member.bioguide_id:
            return error_response(
                message="Member not found or missing bioguide ID",
                error_code="member_not_found",
                status_code=404
            )
        
        # Get legislation data
        legislation_data = await api_service.enrich_member_with_legislation(member_id)
        
        # Extract the requested type
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
        
        return success_response(
            data=data,
            meta={"message": f"Retrieved {legislation_type} legislation for {member.full_name}"}
        )
        
    except Exception as e:
        logger.error(f"Error retrieving legislation for member {member_id}: {e}")
        return error_response(
            message="Failed to retrieve member legislation",
            error_code="legislation_retrieval_failed"
        ) 