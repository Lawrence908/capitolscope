"""
Drafting and publishing posts for the public X account (sync, for Celery).

Flow: ingestion lands trades -> draft_posts() turns notable new trades into
social_posts drafts -> (review mode) an admin approves them -> publish_next()
posts one at a time, paced, inside a daytime window, under a daily cap.

Env (all optional):
  SOCIAL_MODE              review (default) | auto
  SOCIAL_DAILY_CAP         max posts per rolling 24h (default 12)
  SOCIAL_MIN_GAP_MINUTES   minimum minutes between posts (default 20)
  SOCIAL_WINDOW_UTC        posting hours, "12-3" = 12:00 to 03:00 UTC (8am to 11pm ET)
  SOCIAL_LOOKBACK_HOURS    how far back draft_posts looks at newly ingested trades (default 72)
  SOCIAL_DRAFT_TTL_HOURS   unposted drafts older than this are skipped (default 72)
  PUBLIC_BASE_URL          site origin used in links (default https://capitolscope.chrislawrence.ca)
  SOCIAL_INTERNAL_API_URL  where the worker fetches card images (default http://capitolscope:8000)
  SOCIAL_REVIEW_EMAIL      who is told about new drafts (default INGESTION_ALERT_EMAIL)
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .composer import compose
from .models import SocialPost, SocialPostTrade
from .selector import TradeFacts, select_candidates

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def mode() -> str:
    return "auto" if os.getenv("SOCIAL_MODE", "review").strip().lower() == "auto" else "review"


def base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "https://capitolscope.chrislawrence.ca").rstrip("/")


def in_window(now: datetime, spec: Optional[str] = None) -> bool:
    """True if now (UTC) is inside the posting window "start-end" (hours, may wrap midnight)."""
    spec = spec or os.getenv("SOCIAL_WINDOW_UTC", "12-3")
    try:
        start, end = (int(x) for x in spec.split("-", 1))
    except ValueError:
        return True
    h = now.astimezone(timezone.utc).hour
    return start <= h < end if start < end else (h >= start or h < end)


# -- loading ---------------------------------------------------------------


def load_new_trades(session: Session, since: datetime) -> List[TradeFacts]:
    from domains.analytics.conflicts import jurisdiction_sectors
    from domains.congressional.models import CongressMember, CongressionalTrade
    from domains.securities.models import Sector, Security

    rows = session.execute(
        select(CongressionalTrade, CongressMember, Sector.name, Security.name)
        .join(CongressMember, CongressMember.id == CongressionalTrade.member_id)
        .outerjoin(Security, Security.id == CongressionalTrade.security_id)
        .outerjoin(Sector, Sector.gics_code == Security.sector_gics_code)
        .where(CongressionalTrade.created_at >= since)
    ).all()

    facts: List[TradeFacts] = []
    for t, m, sector, security_name in rows:
        facts.append(
            TradeFacts(
                trade_id=str(t.id),
                member_id=str(m.id),
                member_name=m.full_name or f"{m.first_name} {m.last_name}".strip(),
                party=m.party,
                state=m.state,
                chamber=m.chamber,
                district=m.district,
                doc_id=t.doc_id,
                ticker=(t.ticker or None),
                asset_name=t.asset_name or t.raw_asset_description,
                transaction_type=t.transaction_type,
                transaction_date=t.transaction_date,
                notification_date=t.notification_date,
                amount_min=t.amount_min,
                amount_max=t.amount_max,
                owner=t.owner,
                filing_status=t.filing_status,
                parsed_successfully=t.parsed_successfully,
                ticker_confidence=float(t.ticker_confidence) if t.ticker_confidence is not None else None,
                sector=sector,
                security_name=security_name,
                committee_sectors=frozenset(jurisdiction_sectors(m.committees)),
                leadership=bool(m.leadership_roles),
            )
        )
    return facts


def _already_posted(session: Session, trade_ids: List[str]) -> set:
    if not trade_ids:
        return set()
    rows = session.execute(select(SocialPostTrade.trade_id).where(SocialPostTrade.trade_id.in_(trade_ids))).scalars()
    return {str(r) for r in rows}


# -- drafting ----------------------------------------------------------------


def draft_posts(session: Session, now: Optional[datetime] = None, max_new: int = 25) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(hours=_env_int("SOCIAL_LOOKBACK_HOURS", 72))
    trades = load_new_trades(session, since)
    posted = _already_posted(session, [t.trade_id for t in trades])
    candidates = select_candidates(trades, today=now.date(), already_posted=posted)[:max_new]

    created: List[SocialPost] = []
    for c in candidates:
        text, link = compose(c, base_url(), now.date())
        image = (
            f"/api/v1/og/trade/{c.lead.trade_id}.png" if c.kind == "trade" else f"/api/v1/og/member/{c.lead.member_id}.png"
        )
        post = SocialPost(
            platform="x",
            kind=c.kind,
            status="draft",
            score=c.score,
            reasons=c.reasons,
            text=text,
            link_url=link,
            image_url=image,
            member_id=c.lead.member_id,
        )
        session.add(post)
        session.flush()
        for t in c.trades:
            session.add(SocialPostTrade(post_id=post.id, trade_id=t.trade_id))
        created.append(post)
    session.commit()

    if created and mode() == "review":
        _notify_reviewers(created)
    logger.info("social drafts: %d new from %d trades (%d already posted)", len(created), len(trades), len(posted))
    return {"drafted": len(created), "trades_considered": len(trades), "mode": mode()}


def _notify_reviewers(posts: List[SocialPost]) -> None:
    try:
        from core.config import get_settings
        from core.email import EmailService
        from core.email_templates import email_heading, email_panel, p, render_email
        from domains.congressional.fetch.alerts import parse_recipients
        import html as _html

        settings = get_settings()
        recipients = parse_recipients(os.getenv("SOCIAL_REVIEW_EMAIL") or getattr(settings, "INGESTION_ALERT_EMAIL", None))
        if not recipients:
            return
        body = email_heading(f"{len(posts)} new post draft{'s' if len(posts) != 1 else ''} to review")
        for post in posts[:10]:
            body += email_panel(f"<pre style='white-space:pre-wrap;margin:0'>{_html.escape(post.text)}</pre>")
        body += p(f'Review them at <a href="{base_url()}/admin/social">{base_url()}/admin/social</a>.')
        html = render_email(title="CapitolScope post drafts", body_html=body)
        text = "\n\n---\n\n".join(post.text for post in posts) + f"\n\nReview: {base_url()}/admin/social"
        service = EmailService()
        for to in recipients:
            service._send_smtp_email(to, "Reviewer", f"[CapitolScope] {len(posts)} post drafts to review", html, text)
    except Exception as exc:  # notification must never break drafting
        logger.warning("social review email failed: %s", exc)


# -- publishing --------------------------------------------------------------


def _fetch_image(path: Optional[str]) -> Optional[bytes]:
    if not path:
        return None
    url = os.getenv("SOCIAL_INTERNAL_API_URL", "http://capitolscope:8000").rstrip("/") + path
    try:
        r = httpx.get(url, timeout=30.0)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
            return r.content
        logger.warning("card image %s returned %s", url, r.status_code)
    except httpx.HTTPError as exc:
        logger.warning("card image %s failed: %s", url, exc)
    return None


def publish_next(session: Session, now: Optional[datetime] = None, client=None) -> Dict[str, Any]:
    """Post at most one queued post, respecting window, gap and daily cap."""
    from .x_client import XClient, XPostError, XRateLimited, x_enabled

    now = now or datetime.now(timezone.utc)

    # Expire stale drafts so a backlog never floods the feed.
    ttl = timedelta(hours=_env_int("SOCIAL_DRAFT_TTL_HOURS", 72))
    for stale in session.execute(
        select(SocialPost).where(SocialPost.status.in_(("draft", "approved")), SocialPost.created_at < now - ttl)
    ).scalars():
        stale.status, stale.error = "skipped", "expired before posting"
    session.commit()

    if not x_enabled():
        return {"status": "disabled"}
    if not in_window(now):
        return {"status": "outside_window"}
    posted_24h = session.execute(
        select(func.count()).select_from(SocialPost).where(SocialPost.posted_at >= now - timedelta(hours=24))
    ).scalar_one()
    if posted_24h >= _env_int("SOCIAL_DAILY_CAP", 12):
        return {"status": "daily_cap", "posted_24h": posted_24h}
    last = session.execute(select(func.max(SocialPost.posted_at))).scalar_one()
    if last and now - last < timedelta(minutes=_env_int("SOCIAL_MIN_GAP_MINUTES", 20)):
        return {"status": "min_gap"}

    statuses = ("approved", "draft") if mode() == "auto" else ("approved",)
    post = session.execute(
        select(SocialPost)
        .where(SocialPost.status.in_(statuses), SocialPost.platform == "x")
        .order_by(SocialPost.score.desc(), SocialPost.created_at)
        .limit(1)
    ).scalars().first()
    if post is None:
        return {"status": "queue_empty"}

    client = client or XClient()
    try:
        ids = client.post_thread(post.text, post.thread or [], image=_fetch_image(post.image_url))
    except XRateLimited as exc:
        logger.warning("social publish rate limited: %s", exc)
        return {"status": "rate_limited", "reset_at": exc.reset_at.isoformat() if exc.reset_at else None}
    except XPostError as exc:
        post.status, post.error = "failed", str(exc)[:1000]
        session.commit()
        logger.error("social publish failed for %s: %s", post.id, exc)
        return {"status": "failed", "post_id": str(post.id), "error": str(exc)}

    post.status, post.external_id, post.posted_at, post.error = "posted", ids[0], now, None
    session.commit()
    logger.info("posted %s to X as %s", post.id, ids[0])
    return {"status": "posted", "post_id": str(post.id), "tweet_id": ids[0]}


def today_utc() -> date:
    return datetime.now(timezone.utc).date()
