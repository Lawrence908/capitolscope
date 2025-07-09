"""
SQLAlchemy ORM models for CapitolScope database.

This module defines all the database models using SQLAlchemy ORM,
corresponding to the schema defined in database_schema.sql.
"""

from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, DateTime, 
    Decimal as SQLDecimal, BigInteger, ForeignKey, CheckConstraint,
    UniqueConstraint, Index, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

# ============================================================================
# SECURITIES MASTER DATA
# ============================================================================

class AssetType(Base):
    __tablename__ = 'asset_types'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(5), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    securities = relationship("Security", back_populates="asset_type")

class Sector(Base):
    __tablename__ = 'sectors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    gics_code = Column(String(10))
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    securities = relationship("Security", back_populates="sector")

class Exchange(Base):
    __tablename__ = 'exchanges'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(10), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    country = Column(String(3), nullable=False)  # ISO 3166-1 alpha-3
    timezone = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    securities = relationship("Security", back_populates="exchange")

class Security(Base):
    __tablename__ = 'securities'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False)
    name = Column(String(200), nullable=False)
    asset_type_id = Column(Integer, ForeignKey('asset_types.id'))
    sector_id = Column(Integer, ForeignKey('sectors.id'))
    exchange_id = Column(Integer, ForeignKey('exchanges.id'))
    currency = Column(String(3), default='USD')
    market_cap = Column(BigInteger)  # in cents
    shares_outstanding = Column(BigInteger)
    is_active = Column(Boolean, default=True)
    isin = Column(String(12))  # International Securities Identification Number
    cusip = Column(String(9))  # Committee on Uniform Securities Identification Procedures
    figi = Column(String(12))  # Financial Instrument Global Identifier
    metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    asset_type = relationship("AssetType", back_populates="securities")
    sector = relationship("Sector", back_populates="securities")
    exchange = relationship("Exchange", back_populates="securities")
    congressional_trades = relationship("CongressionalTrade", back_populates="security")
    daily_prices = relationship("DailyPrice", back_populates="security")
    corporate_actions = relationship("CorporateAction", back_populates="security")
    member_portfolios = relationship("MemberPortfolio", back_populates="security")
    
    __table_args__ = (
        UniqueConstraint('ticker', 'exchange_id'),
    )

# ============================================================================
# CONGRESSIONAL DATA
# ============================================================================

class CongressMember(Base):
    __tablename__ = 'congress_members'
    
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    full_name = Column(String(200), nullable=False)
    party = Column(String(1))  # D, R, I
    chamber = Column(String(6))  # House, Senate
    state = Column(String(2))  # Two-letter state code
    district = Column(String(10))  # For House members
    bioguide_id = Column(String(10), unique=True)
    congress_gov_id = Column(String(20))
    is_active = Column(Boolean, default=True)
    term_start = Column(Date)
    term_end = Column(Date)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    congressional_trades = relationship("CongressionalTrade", back_populates="member")
    member_portfolios = relationship("MemberPortfolio", back_populates="member")
    portfolio_performance = relationship("PortfolioPerformance", back_populates="member")
    
    __table_args__ = (
        CheckConstraint(party.in_(['D', 'R', 'I']), name='check_party'),
        CheckConstraint(chamber.in_(['House', 'Senate']), name='check_chamber'),
    )

class CongressionalTrade(Base):
    __tablename__ = 'congressional_trades'
    
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey('congress_members.id'), nullable=False)
    security_id = Column(Integer, ForeignKey('securities.id'))
    doc_id = Column(String(50), nullable=False)
    owner = Column(String(10))  # SP, JT, DC, C
    raw_asset_description = Column(Text)
    ticker = Column(String(20))
    transaction_type = Column(String(2))  # P, S, E
    transaction_date = Column(Date, nullable=False)
    notification_date = Column(Date, nullable=False)
    amount_min = Column(Integer)  # in cents
    amount_max = Column(Integer)  # in cents
    amount_exact = Column(Integer)  # in cents
    filing_status = Column(String(1))  # N, P, A
    comment = Column(Text)
    cap_gains_over_200 = Column(Boolean, default=False)
    
    # Data quality tracking
    ticker_confidence = Column(SQLDecimal(3, 2))
    amount_confidence = Column(SQLDecimal(3, 2))
    parsed_successfully = Column(Boolean, default=True)
    parsing_notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    member = relationship("CongressMember", back_populates="congressional_trades")
    security = relationship("Security", back_populates="congressional_trades")
    trade_discussions = relationship("TradeDiscussion", back_populates="trade")
    
    __table_args__ = (
        CheckConstraint(owner.in_(['SP', 'JT', 'DC', 'C']), name='check_owner'),
        CheckConstraint(transaction_type.in_(['P', 'S', 'E']), name='check_transaction_type'),
        CheckConstraint(filing_status.in_(['N', 'P', 'A']), name='check_filing_status'),
    )

# ============================================================================
# PRICE DATA
# ============================================================================

class DailyPrice(Base):
    __tablename__ = 'daily_prices'
    
    id = Column(BigInteger, primary_key=True)
    security_id = Column(Integer, ForeignKey('securities.id'), nullable=False)
    date = Column(Date, nullable=False)
    open_price = Column(Integer, nullable=False)  # in cents
    high_price = Column(Integer, nullable=False)
    low_price = Column(Integer, nullable=False)
    close_price = Column(Integer, nullable=False)
    adjusted_close = Column(Integer)  # split/dividend adjusted
    volume = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    security = relationship("Security", back_populates="daily_prices")
    
    __table_args__ = (
        UniqueConstraint('security_id', 'date'),
    )

class CorporateAction(Base):
    __tablename__ = 'corporate_actions'
    
    id = Column(Integer, primary_key=True)
    security_id = Column(Integer, ForeignKey('securities.id'), nullable=False)
    action_type = Column(String(20), nullable=False)  # split, dividend, spinoff, merger
    ex_date = Column(Date, nullable=False)
    record_date = Column(Date)
    payment_date = Column(Date)
    ratio = Column(SQLDecimal(10, 6))  # For splits
    amount = Column(Integer)  # Dividend amount in cents
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    security = relationship("Security", back_populates="corporate_actions")
    
    __table_args__ = (
        CheckConstraint(action_type.in_(['split', 'dividend', 'spinoff', 'merger']), name='check_action_type'),
    )

# ============================================================================
# PORTFOLIO TRACKING
# ============================================================================

class MemberPortfolio(Base):
    __tablename__ = 'member_portfolios'
    
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey('congress_members.id'), nullable=False)
    security_id = Column(Integer, ForeignKey('securities.id'), nullable=False)
    shares = Column(SQLDecimal(15, 6), nullable=False, default=0)
    cost_basis = Column(Integer, nullable=False, default=0)  # in cents
    avg_cost_per_share = Column(Integer)  # in cents
    first_purchase_date = Column(Date)
    last_transaction_date = Column(Date)
    unrealized_gain_loss = Column(Integer)  # in cents
    realized_gain_loss = Column(Integer, default=0)  # in cents
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    member = relationship("CongressMember", back_populates="member_portfolios")
    security = relationship("Security", back_populates="member_portfolios")
    
    __table_args__ = (
        UniqueConstraint('member_id', 'security_id'),
    )

class PortfolioPerformance(Base):
    __tablename__ = 'portfolio_performance'
    
    id = Column(BigInteger, primary_key=True)
    member_id = Column(Integer, ForeignKey('congress_members.id'), nullable=False)
    date = Column(Date, nullable=False)
    total_value = Column(Integer, nullable=False)  # in cents
    total_cost_basis = Column(Integer, nullable=False)
    unrealized_gain_loss = Column(Integer, nullable=False)
    realized_gain_loss = Column(Integer, nullable=False)
    daily_return = Column(SQLDecimal(8, 6))
    benchmark_return = Column(SQLDecimal(8, 6))  # S&P 500 return
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    member = relationship("CongressMember", back_populates="portfolio_performance")
    
    __table_args__ = (
        UniqueConstraint('member_id', 'date'),
    )

# ============================================================================
# USER MANAGEMENT
# ============================================================================

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    subscription_tier = Column(String(20), default='free')
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="user")
    user_preferences = relationship("UserPreference", back_populates="user", uselist=False)
    email_sends = relationship("EmailSend", back_populates="user")
    discussion_topics = relationship("DiscussionTopic", back_populates="created_by_user")
    discussion_posts = relationship("DiscussionPost", back_populates="user")
    api_usage = relationship("APIUsage", back_populates="user")
    
    __table_args__ = (
        CheckConstraint(subscription_tier.in_(['free', 'pro', 'premium']), name='check_subscription_tier'),
    )

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    plan_name = Column(String(50), nullable=False)
    status = Column(String(20), default='active')
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    stripe_subscription_id = Column(String(100), unique=True)
    stripe_customer_id = Column(String(100))
    amount = Column(Integer, nullable=False)  # in cents
    currency = Column(String(3), default='USD')
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    
    __table_args__ = (
        CheckConstraint(status.in_(['active', 'cancelled', 'expired', 'past_due']), name='check_status'),
    )

class UserPreference(Base):
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    email_notifications = Column(Boolean, default=True)
    trade_alerts = Column(Boolean, default=False)
    newsletter_frequency = Column(String(20), default='weekly')
    alert_threshold = Column(Integer, default=100000)  # in cents
    watchlist_members = Column(ARRAY(Integer))
    preferred_timezone = Column(String(50), default='UTC')
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_preferences")
    
    __table_args__ = (
        UniqueConstraint('user_id'),
        CheckConstraint(newsletter_frequency.in_(['none', 'daily', 'weekly', 'monthly']), name='check_newsletter_frequency'),
    )

# ============================================================================
# EMAIL NOTIFICATIONS
# ============================================================================

class EmailCampaign(Base):
    __tablename__ = 'email_campaigns'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    template_id = Column(String(100))
    scheduled_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    recipient_count = Column(Integer, default=0)
    open_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    status = Column(String(20), default='draft')
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    email_sends = relationship("EmailSend", back_populates="campaign")
    
    __table_args__ = (
        CheckConstraint(status.in_(['draft', 'scheduled', 'sending', 'sent', 'failed']), name='check_status'),
    )

class EmailSend(Base):
    __tablename__ = 'email_sends'
    
    id = Column(BigInteger, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('email_campaigns.id'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    email = Column(String(255), nullable=False)
    status = Column(String(20), default='pending')
    external_id = Column(String(100))  # SendGrid/Mailgun message ID
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    opened_at = Column(DateTime(timezone=True))
    clicked_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    campaign = relationship("EmailCampaign", back_populates="email_sends")
    user = relationship("User", back_populates="email_sends")
    
    __table_args__ = (
        CheckConstraint(status.in_(['pending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed']), name='check_status'),
    )

# ============================================================================
# COMMUNITY FEATURES
# ============================================================================

class DiscussionTopic(Base):
    __tablename__ = 'discussion_topics'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(50), default='general')
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    is_pinned = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    post_count = Column(Integer, default=0)
    last_post_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    created_by_user = relationship("User", back_populates="discussion_topics")
    discussion_posts = relationship("DiscussionPost", back_populates="topic")
    trade_discussions = relationship("TradeDiscussion", back_populates="topic")

class DiscussionPost(Base):
    __tablename__ = 'discussion_posts'
    
    id = Column(BigInteger, primary_key=True)
    topic_id = Column(Integer, ForeignKey('discussion_topics.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    content = Column(Text, nullable=False)
    parent_post_id = Column(BigInteger, ForeignKey('discussion_posts.id'))
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime(timezone=True))
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    topic = relationship("DiscussionTopic", back_populates="discussion_posts")
    user = relationship("User", back_populates="discussion_posts")
    parent_post = relationship("DiscussionPost", remote_side=[id])

class TradeDiscussion(Base):
    __tablename__ = 'trade_discussions'
    
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey('congressional_trades.id'), nullable=False)
    topic_id = Column(Integer, ForeignKey('discussion_topics.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    trade = relationship("CongressionalTrade", back_populates="trade_discussions")
    topic = relationship("DiscussionTopic", back_populates="trade_discussions")
    
    __table_args__ = (
        UniqueConstraint('trade_id'),
    )

# ============================================================================
# SYSTEM TABLES
# ============================================================================

class IngestionLog(Base):
    __tablename__ = 'ingestion_logs'
    
    id = Column(BigInteger, primary_key=True)
    source = Column(String(50), nullable=False)
    batch_id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    status = Column(String(20), default='running')
    error_message = Column(Text)
    metadata = Column(JSONB)
    started_at = Column(DateTime(timezone=True), default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        CheckConstraint(status.in_(['running', 'completed', 'failed', 'cancelled']), name='check_status'),
    )

class APIUsage(Base):
    __tablename__ = 'api_usage'
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer)
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="api_usage") 