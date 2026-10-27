"""
Admin review queue for the public X account (admin role only).

Drafts are produced by background.social_tasks.draft_social_posts. In review
mode nothing is posted until an admin approves it here.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import require_admin
from core.database import get_db_session
from domains.social.composer import X_LIMIT, x_length
from domains.social.models import POST_STATUSES, SocialPost, SocialPostTrade
from domains.users.models import User
from schemas.base import create_response

router = APIRouter()

_EDITABLE = ("draft", "approved", "failed")


def _serialize(post: SocialPost, trade_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "id": str(post.id),
        "platform": post.platform,
        "kind": post.kind,
        "status": post.status,
        "score": post.score,
        "reasons": post.reasons or [],
        "text": post.text,
        "x_length": x_length(post.text),
        "thread": post.thread or [],
        "link_url": post.link_url,
        "image_url": post.image_url,
        "member_id": str(post.member_id) if post.member_id else None,
        "external_id": post.external_id,
        "external_url": f"https://x.com/i/status/{post.external_id}" if post.external_id else None,
        "error": post.error,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "approved_at": post.approved_at.isoformat() if post.approved_at else None,
        "posted_at": post.posted_at.isoformat() if post.posted_at else None,
        "trade_ids": trade_ids or [],
    }


async def _get(session: AsyncSession, post_id: UUID) -> SocialPost:
    post = await session.get(SocialPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.get("/status")
async def social_status(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin()),
):
    from domains.social.service import mode
    from domains.social.x_client import x_enabled

    counts = dict((await session.execute(select(SocialPost.status, func.count()).group_by(SocialPost.status))).all())
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    posted_24h = (
        await session.execute(select(func.count()).select_from(SocialPost).where(SocialPost.posted_at >= since))
    ).scalar_one()
    return create_response(
        data={
            "mode": mode(),
            "x_enabled": x_enabled(),
            "daily_cap": int(os.getenv("SOCIAL_DAILY_CAP", "12")),
            "window_utc": os.getenv("SOCIAL_WINDOW_UTC", "12-3"),
            "posted_24h": posted_24h,
            "counts": {s: counts.get(s, 0) for s in POST_STATUSES},
        }
    )


@router.get("/posts")
async def list_posts(
    status: Optional[str] = Query(None, description="draft|approved|posted|rejected|failed|skipped"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin()),
):
    q = select(SocialPost).order_by(SocialPost.created_at.desc()).limit(limit)
    if status:
        if status not in POST_STATUSES:
            raise HTTPException(status_code=422, detail="Unknown status")
        q = q.where(SocialPost.status == status)
    posts = (await session.execute(q)).scalars().all()
    ids = [p.id for p in posts]
    trade_map: Dict[str, List[str]] = {}
    if ids:
        for post_id, trade_id in (
            await session.execute(select(SocialPostTrade.post_id, SocialPostTrade.trade_id).where(SocialPostTrade.post_id.in_(ids)))
        ).all():
            trade_map.setdefault(str(post_id), []).append(str(trade_id))
    return create_response(data=[_serialize(p, trade_map.get(str(p.id))) for p in posts])


@router.patch("/posts/{post_id}")
async def edit_post(
    post_id: UUID,
    text: str = Body(..., embed=True, min_length=1),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin()),
):
    post = await _get(session, post_id)
    if post.status not in _EDITABLE:
        raise HTTPException(status_code=409, detail=f"Cannot edit a {post.status} post")
    if x_length(text) > X_LIMIT:
        raise HTTPException(status_code=422, detail=f"Post is {x_length(text)} characters; the limit is {X_LIMIT}")
    post.text = text.strip()
    await session.commit()
    return create_response(data=_serialize(post))


@router.post("/posts/{post_id}/approve")
async def approve_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin()),
):
    post = await _get(session, post_id)
    if post.status not in _EDITABLE:
        raise HTTPException(status_code=409, detail=f"Cannot approve a {post.status} post")
    post.status, post.error = "approved", None
    post.approved_by, post.approved_at = current_user.id, datetime.now(timezone.utc)
    await session.commit()
    return create_response(data=_serialize(post))


@router.post("/posts/{post_id}/reject")
async def reject_post(
    post_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin()),
):
    post = await _get(session, post_id)
    if post.status not in _EDITABLE:
        raise HTTPException(status_code=409, detail=f"Cannot reject a {post.status} post")
    post.status = "rejected"
    await session.commit()
    return create_response(data=_serialize(post))


@router.post("/draft-now")
async def draft_now(
    kind: str = Query("trades", pattern="^(trades|weekly)$"),
    current_user: User = Depends(require_admin()),
):
    """Queue a drafting run now: new-trade posts (normally after each sync) or the weekly recap."""
    from background.social_tasks import draft_social_posts, draft_weekly_recap

    task = (draft_weekly_recap if kind == "weekly" else draft_social_posts).delay()
    return create_response(data={"task_id": task.id, "kind": kind})
