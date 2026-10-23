"""
Social posting: drafts and published posts for the public X account.

Every post goes through this table. In review mode drafts wait for an admin
to approve them; in auto mode the publisher posts drafts directly. A trade
can be included in at most one post ever (social_post_trades.trade_id is
unique), which is the dedup guarantee.
"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from domains.base.models import CapitolScopeBaseModel

POST_STATUSES = ("draft", "approved", "posted", "rejected", "failed", "skipped")
POST_KINDS = ("trade", "rollup", "digest", "weekly")


class SocialPost(CapitolScopeBaseModel):
    __tablename__ = "social_posts"

    platform = Column(String(20), nullable=False, default="x")
    kind = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="draft", index=True)
    score = Column(Integer, nullable=False, default=0)
    reasons = Column(JSON, nullable=True)       # why it was selected, for the reviewer
    text = Column(Text, nullable=False)         # lead post
    thread = Column(JSON, nullable=True)        # optional replies, in order
    link_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)  # card rendered by /api/v1/og/...
    member_id = Column(UUID(as_uuid=True), ForeignKey("congress_members.id"), nullable=True, index=True)
    external_id = Column(String(64), nullable=True)  # tweet id once posted
    error = Column(Text, nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True, index=True)


class SocialPostTrade(CapitolScopeBaseModel):
    """Which trades a post covers. trade_id is unique: never post a trade twice."""

    __tablename__ = "social_post_trades"

    post_id = Column(UUID(as_uuid=True), ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    trade_id = Column(UUID(as_uuid=True), ForeignKey("congressional_trades.id"), nullable=False, unique=True)
