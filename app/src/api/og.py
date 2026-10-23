"""
Open Graph / X card images (anonymous).

    GET /api/v1/og/trade/{trade_id}.png    1200x675 trade card
    GET /api/v1/og/member/{member_id}.png  1200x630 member card
    GET /api/v1/og/default.png             1200x630 site card

PNGs are rendered by domains.social.cards and cached on disk (see
domains.social.card_cache) keyed by id + a hash of the card's input data, so a
changed trade/member re-renders automatically. Unknown or malformed ids 404.
"""

from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from core.database import get_db_session
from domains.social import card_cache
from domains.social.cards import render_default_card, render_member_card, render_trade_card
from domains.social.formatting import public_domain
from domains.social.loader import load_member, load_trade, parse_uuid

router = APIRouter()

CACHE_CONTROL = "public, max-age=86400"


async def _png_response(request: Request, kind: str, ident: str, data, render: Callable[[], bytes]) -> Response:
    domain = public_domain()
    digest = card_cache.content_hash(data, domain)
    etag = f'"{kind}-{digest}"'
    headers = {"Cache-Control": CACHE_CONTROL, "ETag": etag}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    png, _ = await run_in_threadpool(card_cache.get_or_render, kind, ident, digest, render)
    return Response(content=png, media_type="image/png", headers=headers)


@router.api_route("/trade/{trade_id}.png", methods=["GET", "HEAD"], include_in_schema=True)
async def trade_card(trade_id: str, request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    tid = parse_uuid(trade_id)
    if tid is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    loaded = await load_trade(session, tid)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    domain = public_domain()
    return await _png_response(
        request, "trade", str(tid), loaded.card, lambda: render_trade_card(loaded.card, domain)
    )


@router.api_route("/member/{member_id}.png", methods=["GET", "HEAD"])
async def member_card(member_id: str, request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    mid = parse_uuid(member_id)
    if mid is None:
        raise HTTPException(status_code=404, detail="Member not found")
    data = await load_member(session, mid)
    if data is None:
        raise HTTPException(status_code=404, detail="Member not found")
    domain = public_domain()
    return await _png_response(request, "member", str(mid), data, lambda: render_member_card(data, domain))


@router.api_route("/default.png", methods=["GET", "HEAD"])
async def default_card(request: Request) -> Response:
    domain = public_domain()
    return await _png_response(request, "site", "default", {"card": "default"}, lambda: render_default_card(domain))
