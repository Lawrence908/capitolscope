"""
Server-rendered HTML shells for link previews.

The SPA is client-rendered, so crawlers (X, Slack, iMessage, Facebook) only
ever see index.html's static meta. Caddy rewrites GET /t/{id},
/members/{id} and /assets/{ticker} to these handlers (see
docs/deploy/caddy-share-routing.md); each one fetches the built SPA
index.html from the frontend container, swaps in page-specific <title>,
description, Open Graph, Twitter and canonical tags, and returns it with 200.
Humans get the same document and the SPA boots as usual. Unknown ids get the
SPA shell with its default meta so the SPA renders its own not-found.

Every interpolated value is HTML-escaped (member names and asset
descriptions are untrusted disclosure text).
"""

from __future__ import annotations

import asyncio
import html
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from domains.social import card_cache
from domains.social.formatting import (
    member_description,
    member_line,
    plural,
    public_base_url,
    public_domain,
    trade_description,
    trade_headline,
    fmt_date,
)
from domains.social.loader import load_asset, load_member, load_trade, parse_uuid

logger = logging.getLogger(__name__)

router = APIRouter()

SITE_NAME = "CapitolScope"
DEFAULT_TITLE = "CapitolScope - Congressional Trading Transparency"
DEFAULT_DESCRIPTION = (
    "Stock trades disclosed by members of Congress, and how long each one took to disclose."
)
TICKER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]{0,19}$")
MAX_DESCRIPTION = 300

# HTML-only responses; the SPA shell must revalidate so new deploys (new
# hashed bundles) are picked up immediately, as nginx does for index.html.
HTML_CACHE_CONTROL = "no-cache"


def frontend_index_url() -> str:
    return os.getenv("CAPITOLSCOPE_FRONTEND_INDEX_URL", "http://capitolscope-frontend:5173/index.html")


def index_ttl_seconds() -> float:
    try:
        return float(os.getenv("CAPITOLSCOPE_SHARE_INDEX_TTL", "120"))
    except ValueError:
        return 120.0


# ---------------------------------------------------------------------------
# SPA index.html (fetched from the frontend container, cached in memory)
# ---------------------------------------------------------------------------
FALLBACK_INDEX = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CapitolScope</title>
  </head>
  <body>
    <div id="root"><p><a href="/">CapitolScope</a></p></div>
  </body>
</html>
"""


class _IndexCache:
    def __init__(self) -> None:
        self.body: Optional[str] = None
        self.etag: Optional[str] = None
        self.fetched_at: float = 0.0
        self.lock = asyncio.Lock()

    def reset(self) -> None:
        self.body, self.etag, self.fetched_at = None, None, 0.0


_index = _IndexCache()


async def get_index_html() -> str:
    """The built SPA index.html, cached for a short TTL and revalidated by ETag."""
    now = time.monotonic()
    if _index.body is not None and now - _index.fetched_at < index_ttl_seconds():
        return _index.body
    async with _index.lock:
        if _index.body is not None and time.monotonic() - _index.fetched_at < index_ttl_seconds():
            return _index.body
        headers = {"If-None-Match": _index.etag} if (_index.etag and _index.body) else {}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(frontend_index_url(), headers=headers)
            if resp.status_code == 304 and _index.body is not None:
                _index.fetched_at = time.monotonic()
            elif resp.status_code == 200 and "<head" in resp.text.lower():
                _index.body = resp.text
                _index.etag = resp.headers.get("etag")
                _index.fetched_at = time.monotonic()
            else:
                logger.warning("share: index.html fetch returned %s", resp.status_code)
        except httpx.HTTPError as exc:
            logger.warning("share: index.html fetch failed: %s", exc)
        # On failure serve the stale copy (or a bare fallback); retry next request.
        return _index.body or FALLBACK_INDEX


# ---------------------------------------------------------------------------
# Meta injection
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PageMeta:
    title: str
    description: str
    url: str
    image: str
    image_alt: str
    og_type: str = "website"
    image_width: int = 1200
    image_height: int = 630


_STRIP_RE = re.compile(
    r"""<title\b[^>]*>.*?</title\s*>\s*"""
    r"""|<meta\b[^>]*\b(?:name|property)\s*=\s*["'](?:description|og:[^"']*|twitter:[^"']*)["'][^>]*>\s*"""
    r"""|<link\b[^>]*\brel\s*=\s*["']canonical["'][^>]*>\s*""",
    re.IGNORECASE | re.DOTALL,
)
_CHARSET_RE = re.compile(r"<meta\b[^>]*\bcharset\s*=[^>]*>", re.IGNORECASE)
_HEAD_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)


def _clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rsplit(" ", 1)[0].rstrip(" ,.;:") + "..."


def render_meta(meta: PageMeta) -> str:
    e = lambda v: html.escape(str(v), quote=True)  # noqa: E731
    title = _clip(meta.title, 200)
    desc = _clip(meta.description, MAX_DESCRIPTION)
    tags = [
        f"<title>{e(title)}</title>",
        f'<meta name="description" content="{e(desc)}" />',
        f'<link rel="canonical" href="{e(meta.url)}" />',
        f'<meta property="og:site_name" content="{e(SITE_NAME)}" />',
        f'<meta property="og:type" content="{e(meta.og_type)}" />',
        f'<meta property="og:title" content="{e(title)}" />',
        f'<meta property="og:description" content="{e(desc)}" />',
        f'<meta property="og:url" content="{e(meta.url)}" />',
        f'<meta property="og:image" content="{e(meta.image)}" />',
        '<meta property="og:image:type" content="image/png" />',
        f'<meta property="og:image:width" content="{meta.image_width}" />',
        f'<meta property="og:image:height" content="{meta.image_height}" />',
        f'<meta property="og:image:alt" content="{e(_clip(meta.image_alt, 400))}" />',
        '<meta name="twitter:card" content="summary_large_image" />',
        f'<meta name="twitter:title" content="{e(title)}" />',
        f'<meta name="twitter:description" content="{e(desc)}" />',
        f'<meta name="twitter:image" content="{e(meta.image)}" />',
        f'<meta name="twitter:image:alt" content="{e(_clip(meta.image_alt, 400))}" />',
    ]
    return "\n    ".join(tags)


def inject_meta(index_html: str, meta: PageMeta) -> str:
    """Replace the shell's title/description/og/twitter/canonical tags with ``meta``."""
    doc = _STRIP_RE.sub("", index_html)
    block = "\n    " + render_meta(meta) + "\n"
    m = _CHARSET_RE.search(doc) or _HEAD_RE.search(doc)
    if m is None:
        return block + doc
    return doc[: m.end()] + block + doc[m.end():]


def default_meta(path: str = "/") -> PageMeta:
    base = public_base_url()
    return PageMeta(
        title=DEFAULT_TITLE,
        description=DEFAULT_DESCRIPTION,
        url=base + path,
        image=f"{base}/api/v1/og/default.png",
        image_alt="CapitolScope: congressional stock trades and how long they took to disclose.",
    )


def _html(doc: str) -> HTMLResponse:
    return HTMLResponse(content=doc, status_code=200, headers={"Cache-Control": HTML_CACHE_CONTROL})


async def _page(meta: PageMeta) -> HTMLResponse:
    return _html(inject_meta(await get_index_html(), meta))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.api_route("/t/{trade_id}", methods=["GET", "HEAD"], include_in_schema=False)
async def share_trade(trade_id: str, session: AsyncSession = Depends(get_db_session)) -> HTMLResponse:
    base = public_base_url()
    tid = parse_uuid(trade_id)
    loaded = await load_trade(session, tid) if tid else None
    if loaded is None:
        return await _page(default_meta(f"/t/{quote(trade_id, safe='')}"))
    card = loaded.card
    version = card_cache.content_hash(card, public_domain())[:10]
    headline = trade_headline(card)
    meta = PageMeta(
        title=f"{headline} | {SITE_NAME}",
        description=trade_description(card),
        url=f"{base}/t/{tid}",
        image=f"{base}/api/v1/og/trade/{tid}.png?v={version}",
        image_alt=f"{headline}. {trade_description(card)}",
        og_type="article",
        image_height=675,
    )
    return await _page(meta)


@router.api_route("/members/{member_id}", methods=["GET", "HEAD"], include_in_schema=False)
async def share_member(member_id: str, session: AsyncSession = Depends(get_db_session)) -> HTMLResponse:
    base = public_base_url()
    mid = parse_uuid(member_id)
    data = await load_member(session, mid) if mid else None
    if data is None:
        return await _page(default_meta(f"/members/{quote(member_id, safe='')}"))
    version = card_cache.content_hash(data, public_domain())[:10]
    who = member_line(data.name, data.chamber, data.party, data.state, data.district)
    meta = PageMeta(
        title=f"{who}: stock trades | {SITE_NAME}",
        description=member_description(data),
        url=f"{base}/members/{mid}",
        image=f"{base}/api/v1/og/member/{mid}.png?v={version}",
        image_alt=f"{who}. {member_description(data)}",
        og_type="profile",
    )
    return await _page(meta)


@router.api_route("/assets/{ticker}", methods=["GET", "HEAD"], include_in_schema=False)
async def share_asset(ticker: str, session: AsyncSession = Depends(get_db_session)) -> HTMLResponse:
    base = public_base_url()
    if not TICKER_RE.match(ticker or ""):
        return await _page(default_meta(f"/assets/{quote(ticker or '', safe='')}"))
    symbol = ticker.upper()
    summary = await load_asset(session, symbol)
    path = f"/assets/{quote(symbol, safe='')}"
    if summary is None:
        return await _page(default_meta(path))
    label = f"{summary.name} ({symbol})" if summary.name else symbol
    desc = (
        f"{plural(summary.trade_count, 'disclosed trade')} of {label} by "
        f"{plural(summary.member_count, 'member')} of Congress."
    )
    last = fmt_date(summary.last_disclosed)
    if last:
        desc += f" Most recent disclosure: {last}."
    meta = PageMeta(
        title=f"{symbol}: congressional trades | {SITE_NAME}",
        description=desc,
        url=base + path,
        image=f"{base}/api/v1/og/default.png",
        image_alt=f"Congressional trades in {label}.",
    )
    return await _page(meta)
