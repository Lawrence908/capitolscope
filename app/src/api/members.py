"""
Congressional members API endpoints.
"""

from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
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


# ============================================================================
# PUBLIC MEMBER DIRECTORY + DISCLOSURE STATS
#
# Member pages are public: the list, detail, per-member trades and per-member
# disclosure stats below take no user dependency, so anonymous requests work.
# Anything user-specific (alerts, mirrors, legislation) stays authenticated.
# ============================================================================

# STOCK Act: periodic transaction reports are due within 45 days of the trade.
DISCLOSURE_LIMIT_DAYS = 45

_MEMBER_SORTS = {"name", "trades", "last_filing", "avg_days", "late", "volume", "state", "chamber", "party"}


class MemberDirectoryItem(CongressMemberSummary):
    """Directory row: member summary plus disclosure aggregates."""
    last_filing_date: Optional[date] = None
    last_trade_date: Optional[date] = None
    avg_days_to_disclose: Optional[float] = None
    late_count: Optional[int] = None


def _split_multi(values: Optional[List[str]]) -> List[str]:
    """Flatten repeated and comma-separated query values (?a=x&a=y or ?a=x,y)."""
    out: List[str] = []
    for v in values or []:
        out.extend(x.strip() for x in str(v).split(",") if x.strip())
    return out


def normalize_member_filters(
    parties: Optional[List[str]],
    chambers: Optional[List[str]],
    states: Optional[List[str]],
) -> Tuple[List[str], List[str], List[str]]:
    """Normalize directory filters to DB values: party D/R/I, chamber House/Senate, state XX."""
    party_codes = sorted({p[0].upper() for p in _split_multi(parties) if p[0].upper() in ("D", "R", "I")})
    chamber_vals = sorted({c.capitalize() for c in _split_multi(chambers) if c.lower() in ("house", "senate")})
    state_vals = sorted({s.upper() for s in _split_multi(states) if len(s) == 2})
    return party_codes, chamber_vals, state_vals


def _is_amended(filing_status: Optional[str]) -> bool:
    return (filing_status or "").strip().upper().startswith("A")


def compute_disclosure_stats(rows: List[Any], today: date) -> Dict[str, Any]:
    """
    Per-member disclosure statistics from that member's trade rows.

    Each row needs transaction_date, notification_date, amount_min, amount_max,
    amount_exact (cents), filing_status and transaction_type.

    Rules: trades dated in the future (transaction_date > today) are dropped as
    parse errors. Timing stats (average/median days, late count) use original
    filings only; amendments (filing_status 'A') are re-filings whose dates
    measure the amendment, not the trade disclosure. The reported volume range
    is the sum of the disclosed lower and upper bounds; an open-ended top band
    (no amount_max) contributes its lower bound and flags the range as open.
    """
    valid = [r for r in rows if r.transaction_date and r.transaction_date <= today]
    year_ago = today - timedelta(days=365)

    def _days(r) -> Optional[int]:
        if not r.notification_date or not r.transaction_date:
            return None
        return max(0, (r.notification_date - r.transaction_date).days)

    timed = [(r, _days(r)) for r in valid if not _is_amended(r.filing_status)]
    timed = [(r, d) for r, d in timed if d is not None]
    all_days = [d for _, d in timed]
    recent_days = [d for r, d in timed if r.transaction_date >= year_ago]

    def _avg(xs: List[int]) -> Optional[float]:
        return round(sum(xs) / len(xs), 1) if xs else None

    def _median(xs: List[int]) -> Optional[float]:
        if not xs:
            return None
        ys = sorted(xs)
        mid = len(ys) // 2
        return float(ys[mid]) if len(ys) % 2 else (ys[mid - 1] + ys[mid]) / 2

    vol_min = 0
    vol_max = 0
    open_ended = False
    for r in valid:
        if r.amount_exact is not None:
            vol_min += r.amount_exact
            vol_max += r.amount_exact
            continue
        lo = r.amount_min
        hi = r.amount_max
        if lo is None and hi is None:
            continue
        vol_min += lo if lo is not None else hi
        if hi is None:
            open_ended = True
            vol_max += lo
        else:
            vol_max += hi

    late = [d for d in all_days if d > DISCLOSURE_LIMIT_DAYS]
    ttypes = [(r.transaction_type or "").upper() for r in valid]
    tdates = [r.transaction_date for r in valid]
    fdates = [r.notification_date for r in valid if r.notification_date]

    return {
        "total_trades": len(valid),
        "purchase_count": sum(1 for t in ttypes if t.startswith("P")),
        "sale_count": sum(1 for t in ttypes if t.startswith("S")),
        "exchange_count": sum(1 for t in ttypes if t.startswith("E")),
        "amended_count": sum(1 for r in valid if _is_amended(r.filing_status)),
        "trades_last_12_months": sum(1 for d in tdates if d >= year_ago),
        "first_trade_date": min(tdates).isoformat() if tdates else None,
        "last_trade_date": max(tdates).isoformat() if tdates else None,
        "first_filing_date": min(fdates).isoformat() if fdates else None,
        "last_filing_date": max(fdates).isoformat() if fdates else None,
        "timed_trades": len(all_days),
        "avg_days_to_disclose": _avg(all_days),
        "median_days_to_disclose": _median(all_days),
        "max_days_to_disclose": max(all_days) if all_days else None,
        "avg_days_last_12_months": _avg(recent_days),
        "median_days_last_12_months": _median(recent_days),
        "late_count": len(late),
        "late_pct": round(len(late) / len(all_days) * 100, 1) if all_days else None,
        "late_count_last_12_months": sum(1 for d in recent_days if d > DISCLOSURE_LIMIT_DAYS),
        "volume_min": vol_min,
        "volume_max": vol_max,
        "volume_open_ended": open_ended,
        "disclosure_limit_days": DISCLOSURE_LIMIT_DAYS,
    }


def _parse_member_uuid(member_id: str) -> UUID:
    try:
        return UUID(member_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Member not found")


@router.get(
    "/",
    response_model=ResponseEnvelope[PaginatedResponse[MemberDirectoryItem]],
    responses={
        200: {"description": "Congressional members retrieved successfully"},
        400: {"description": "Invalid parameters"},
        500: {"description": "Internal server error"}
    }
)
async def get_members(
    search: Optional[str] = Query(None, max_length=100, description="Name search (or a two-letter state code)"),
    parties: Optional[List[str]] = Query(None, description="Party codes or names (D, R, I); repeat or comma-separate"),
    chambers: Optional[List[str]] = Query(None, description="House and/or Senate"),
    states: Optional[List[str]] = Query(None, description="Two-letter state codes"),
    has_trades: bool = Query(False, description="Only members with at least one disclosed trade"),
    sort_by: str = Query("name", description="name, trades, last_filing, avg_days, late, volume, state, chamber, party"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[PaginatedResponse[MemberDirectoryItem]]:
    """
    Public member directory with filtering, sorting and per-member disclosure
    aggregates (trade count, last filing date, average days to disclose, late
    filings). Future-dated trades are excluded; amendments are excluded from
    timing and late counts.

    **Public**: no authentication required.
    """
    from sqlalchemy import select, func, case, and_, or_, asc as _asc, desc as _desc

    T = CongressionalTrade
    M = CongressMember
    party_codes, chamber_vals, state_vals = normalize_member_filters(parties, chambers, states)
    if sort_by not in _MEMBER_SORTS:
        sort_by = "name"

    try:
        days = T.notification_date - T.transaction_date
        original = func.coalesce(T.filing_status, "N") != "A"
        agg = (
            select(
                T.member_id.label("member_id"),
                func.count(T.id).label("trade_count"),
                func.sum(
                    func.coalesce(T.amount_exact, (T.amount_min + T.amount_max) / 2)
                ).label("total_value"),
                func.max(T.notification_date).label("last_filing_date"),
                func.max(T.transaction_date).label("last_trade_date"),
                func.avg(case((original, days))).label("avg_days"),
                func.count(case((and_(original, days > DISCLOSURE_LIMIT_DAYS), 1))).label("late_count"),
            )
            .where(T.transaction_date <= date.today())
            .group_by(T.member_id)
            .subquery()
        )

        conds = []
        if party_codes:
            conds.append(M.party.in_(party_codes))
        if chamber_vals:
            conds.append(M.chamber.in_(chamber_vals))
        if state_vals:
            conds.append(M.state.in_(state_vals))
        if search and search.strip():
            term = f"%{search.strip()}%"
            name_match = or_(M.full_name.ilike(term), M.first_name.ilike(term), M.last_name.ilike(term))
            if len(search.strip()) == 2 and search.strip().isalpha():
                name_match = or_(name_match, M.state == search.strip().upper())
            conds.append(name_match)
        if has_trades:
            conds.append(agg.c.trade_count > 0)

        base = select(M, agg).outerjoin(agg, agg.c.member_id == M.id)
        if conds:
            base = base.where(and_(*conds))

        total = (await session.execute(
            select(func.count()).select_from(base.with_only_columns(M.id).subquery())
        )).scalar() or 0

        direction = _desc if sort_order == "desc" else _asc
        sort_cols = {
            "name": [M.last_name, M.first_name],
            "trades": [func.coalesce(agg.c.trade_count, 0)],
            "last_filing": [agg.c.last_filing_date],
            "avg_days": [agg.c.avg_days],
            "late": [func.coalesce(agg.c.late_count, 0)],
            "volume": [func.coalesce(agg.c.total_value, 0)],
            "state": [M.state, M.district],
            "chamber": [M.chamber],
            "party": [M.party],
        }[sort_by]
        order = [direction(c).nulls_last() for c in sort_cols]
        order += [_asc(M.last_name), _asc(M.first_name), _asc(M.id)]

        rows = (await session.execute(
            base.order_by(*order).offset((page - 1) * limit).limit(limit)
        )).all()

        items = []
        for row in rows:
            member = row[0]
            items.append(MemberDirectoryItem(
                id=member.id,
                bioguide_id=member.bioguide_id,
                first_name=member.first_name,
                last_name=member.last_name,
                full_name=member.full_name,
                prefix=member.prefix,
                party=member.party,
                state=member.state,
                district=member.district,
                chamber=member.chamber,
                url=member.website_url,
                website_url=member.website_url,
                image_url=member.image_url,
                in_office=member.is_active,
                trade_count=int(row.trade_count or 0),
                total_trade_value=int(row.total_value or 0),
                last_filing_date=row.last_filing_date,
                last_trade_date=row.last_trade_date,
                avg_days_to_disclose=round(float(row.avg_days), 1) if row.avg_days is not None else None,
                late_count=int(row.late_count or 0),
                created_at=member.created_at,
                updated_at=member.updated_at,
            ))

        pages = (total + limit - 1) // limit
        paginated = PaginatedResponse[MemberDirectoryItem](
            items=items,
            meta=PaginationMeta(
                page=page, per_page=limit, total=total, pages=pages,
                has_next=page < pages, has_prev=page > 1,
            ),
        )
        return create_response(paginated)

    except Exception as e:
        logger.error(f"Error retrieving members: {e}", exc_info=True)
        return create_response(None, error="Failed to retrieve congressional members")


@router.get(
    "/{member_id}/stats",
    response_model=ResponseEnvelope[Dict[str, Any]],
    responses={200: {"description": "Member disclosure statistics"}, 404: {"description": "Member not found"}},
)
async def get_member_disclosure_stats(
    member_id: str = Path(..., description="Member UUID"),
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[Dict[str, Any]]:
    """
    Disclosure statistics for one member: totals, first/last trade and filing
    dates, average and median days to disclose, late filings (past the 45-day
    limit, amendments excluded) and the reported volume range (cents).

    **Public**: no authentication required.
    """
    from sqlalchemy import select
    from core.cache import cached

    member_uuid = _parse_member_uuid(member_id)
    exists = (await session.execute(
        select(CongressMember.id).where(CongressMember.id == member_uuid)
    )).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="Member not found")

    async def _compute() -> Dict[str, Any]:
        T = CongressionalTrade
        rows = (await session.execute(
            select(
                T.transaction_date, T.notification_date, T.amount_min, T.amount_max,
                T.amount_exact, T.filing_status, T.transaction_type,
            ).where(T.member_id == member_uuid)
        )).all()
        return compute_disclosure_stats(rows, date.today())

    data = await cached(f"member:stats:{member_uuid}", _compute, ttl=1800)
    return create_response(data={**data, "member_id": str(member_uuid)})


@router.get(
    "/{member_id}/trades",
    response_model=ResponseEnvelope[PaginatedResponse[Dict[str, Any]]],
    responses={200: {"description": "Member trades, newest filing first"}, 404: {"description": "Member not found"}},
)
async def get_member_trades(
    member_id: str = Path(..., description="Member UUID"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[PaginatedResponse[Dict[str, Any]]]:
    """
    A member's disclosed trades, newest filing first (then newest trade).
    Future-dated transactions are excluded.

    **Public**: no authentication required.
    """
    from sqlalchemy import select, func, desc as _desc

    member_uuid = _parse_member_uuid(member_id)
    member = (await session.execute(
        select(CongressMember).where(CongressMember.id == member_uuid)
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    T = CongressionalTrade
    where = [T.member_id == member_uuid, T.transaction_date <= date.today()]
    total = (await session.execute(select(func.count(T.id)).where(*where))).scalar() or 0
    trades = (await session.execute(
        select(T).where(*where)
        .order_by(_desc(T.notification_date), _desc(T.transaction_date), _desc(T.id))
        .offset((page - 1) * limit).limit(limit)
    )).scalars().all()

    items = [
        {
            "id": str(t.id),
            "member_id": str(member.id),
            "member_name": member.full_name,
            "member_party": member.party,
            "member_chamber": member.chamber,
            "member_state": member.state,
            "doc_id": t.doc_id,
            "document_url": t.document_url,
            "ticker": t.ticker,
            "asset_name": t.asset_name or t.raw_asset_description,
            "security_id": str(t.security_id) if t.security_id else None,
            "asset_type": t.asset_type,
            "owner": t.owner,
            "transaction_type": t.transaction_type,
            "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
            "notification_date": t.notification_date.isoformat() if t.notification_date else None,
            "amount_min": t.amount_min,
            "amount_max": t.amount_max,
            "amount_exact": t.amount_exact,
            "filing_status": t.filing_status,
        }
        for t in trades
    ]
    from api.trades import apply_security_names  # local import: avoid router import cycles

    await apply_security_names(session, items)
    pages = (total + limit - 1) // limit
    return create_response(PaginatedResponse[Dict[str, Any]](
        items=items,
        meta=PaginationMeta(
            page=page, per_page=limit, total=total, pages=pages,
            has_next=page < pages, has_prev=page > 1,
        ),
    ))


@router.get(
    "/{member_id}",
    response_model=ResponseEnvelope[CongressMemberDetail],
    responses={
        200: {"description": "Member details retrieved successfully"},
        400: {"description": "Invalid member ID"},
        404: {"description": "Member not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_member(
    member_id: str = Path(..., description="Member ID"),
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[CongressMemberDetail]:
    """
    Get detailed information about a specific congressional member.

    **Public**: no authentication required.
    """
    logger.info(f"Getting member by ID: member_id={member_id}")
    try:
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
        ).where(
            CongressionalTrade.member_id == member_uuid,
            CongressionalTrade.transaction_date <= date.today(),
        )
        
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