"""
SQLAlchemy ORM models for CapitolScope database.

Enhanced models with social integrations, monetization features, and ML preparation.
This module defines all the database models using SQLAlchemy ORM for async Supabase.
"""

from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, DateTime, 
    Decimal as SQLDecimal, BigInteger, ForeignKey, CheckConstraint,
    UniqueConstraint, Index, ARRAY, Float
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
    category = Column(String(50))  # stocks, bonds, alternatives, crypto
    risk_level = Column(Integer)  # 1-5 risk scoring for ML
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    securities = relationship("Security", back_populates="asset_type")

class Sector(Base):
    __tablename__ = 'sectors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    gics_code = Column(String(10))
    parent_sector_id = Column(Integer, ForeignKey('sectors.id'))  # For sub-sectors
    market_sensitivity = Column(Float)  # ML feature: market beta
    volatility_score = Column(Float)  # ML feature: historical volatility
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    securities = relationship("Security", back_populates="sector")
    parent_sector = relationship("Sector", remote_side=[id])

class Exchange(Base):
    __tablename__ = 'exchanges'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(10), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    country = Column(String(3), nullable=False)  # ISO 3166-1 alpha-3
    timezone = Column(String(50), nullable=False)
    trading_hours = Column(JSONB)  # Store market hours
    market_cap_rank = Column(Integer)  # Global exchange ranking
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
    
    # Identifiers
    isin = Column(String(12))  # International Securities Identification Number
    cusip = Column(String(9))  # Committee on Uniform Securities Identification Procedures
    figi = Column(String(12))  # Financial Instrument Global Identifier
    
    # ML Features
    beta = Column(Float)  # Market beta
    pe_ratio = Column(Float)  # Price-to-earnings ratio
    dividend_yield = Column(Float)  # Annual dividend yield
    volatility_30d = Column(Float)  # 30-day volatility
    volume_avg_30d = Column(BigInteger)  # 30-day average volume
    
    # ESG and Social Impact (monetizable premium feature)
    esg_score = Column(Float)  # Environmental, Social, Governance score
    controversy_score = Column(Float)  # News sentiment/controversy tracking
    
    # Metadata
    metadata = Column(JSONB)  # Flexible additional data
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
# CONGRESSIONAL DATA WITH SOCIAL & RESEARCH INTEGRATION
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
    
    # Official IDs
    bioguide_id = Column(String(10), unique=True)
    congress_gov_id = Column(String(20))
    fec_id = Column(String(20))  # Federal Election Commission ID
    
    # Term Information
    is_active = Column(Boolean, default=True)
    term_start = Column(Date)
    term_end = Column(Date)
    seniority_years = Column(Integer)
    
    # Social Media & Research Links (RAG Network Ready)
    twitter_handle = Column(String(50))
    linkedin_url = Column(String(200))
    facebook_url = Column(String(200))
    instagram_handle = Column(String(50))
    youtube_channel = Column(String(200))
    website_url = Column(String(200))
    wikipedia_url = Column(String(200))
    ballotpedia_url = Column(String(200))
    opensecrets_url = Column(String(200))  # Campaign finance data
    
    # Committee & Position Information
    committee_memberships = Column(JSONB)  # Current committees
    leadership_positions = Column(JSONB)  # Leadership roles
    
    # ML & Analytics Features
    influence_score = Column(Float)  # Calculated influence metric
    media_mentions_30d = Column(Integer)  # Recent media coverage
    social_followers_count = Column(Integer)  # Total social media followers
    sentiment_score = Column(Float)  # News sentiment analysis
    trading_frequency_score = Column(Float)  # How often they trade
    avg_trade_size = Column(Integer)  # Average trade size in cents
    
    # Premium Features (Monetizable)
    voting_record_summary = Column(JSONB)  # Key votes and positions
    lobbying_connections = Column(JSONB)  # Lobbying relationships
    campaign_finance_summary = Column(JSONB)  # Top donors, expenditures
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    congressional_trades = relationship("CongressionalTrade", back_populates="member")
    member_portfolios = relationship("MemberPortfolio", back_populates="member")
    portfolio_performance = relationship("PortfolioPerformance", back_populates="member")
    member_alerts = relationship("MemberAlert", back_populates="member")
    
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
    
    # ML & Analytics Features
    market_impact_score = Column(Float)  # Calculated market impact
    timing_score = Column(Float)  # Timing relative to market events
    performance_1d = Column(Float)  # 1-day performance after trade
    performance_7d = Column(Float)  # 7-day performance after trade
    performance_30d = Column(Float)  # 30-day performance after trade
    
    # Social Features
    viral_score = Column(Float)  # How much social media attention it got
    reddit_mentions = Column(Integer)  # Reddit discussions
    twitter_mentions = Column(Integer)  # Twitter mentions
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    member = relationship("CongressMember", back_populates="congressional_trades")
    security = relationship("Security", back_populates="congressional_trades")
    trade_discussions = relationship("TradeDiscussion", back_populates="trade")
    trade_social_posts = relationship("TradeSocialPost", back_populates="trade")
    
    __table_args__ = (
        CheckConstraint(owner.in_(['SP', 'JT', 'DC', 'C']), name='check_owner'),
        CheckConstraint(transaction_type.in_(['P', 'S', 'E']), name='check_transaction_type'),
        CheckConstraint(filing_status.in_(['N', 'P', 'A']), name='check_filing_status'),
    )

# ============================================================================
# PRICE DATA WITH ML FEATURES
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
    
    # ML Features
    rsi_14 = Column(Float)  # 14-day RSI
    macd = Column(Float)  # MACD indicator
    bollinger_upper = Column(Integer)  # Bollinger band upper
    bollinger_lower = Column(Integer)  # Bollinger band lower
    volatility = Column(Float)  # Daily volatility
    
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
    
    # Impact tracking for ML
    price_impact_1d = Column(Float)  # 1-day price impact
    volume_impact_1d = Column(Float)  # 1-day volume impact
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    security = relationship("Security", back_populates="corporate_actions")
    
    __table_args__ = (
        CheckConstraint(action_type.in_(['split', 'dividend', 'spinoff', 'merger']), name='check_action_type'),
    )

# ============================================================================
# PORTFOLIO TRACKING WITH PERFORMANCE ANALYTICS
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
    
    # Performance Analytics (Premium Feature)
    sharpe_ratio = Column(Float)  # Risk-adjusted return
    max_drawdown = Column(Float)  # Maximum drawdown percentage
    holding_period_return = Column(Float)  # Total return percentage
    
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
    
    # Advanced Performance Metrics (Premium)
    alpha = Column(Float)  # Alpha vs benchmark
    beta = Column(Float)  # Beta vs benchmark
    sharpe_ratio = Column(Float)  # Sharpe ratio
    sortino_ratio = Column(Float)  # Sortino ratio
    max_drawdown = Column(Float)  # Maximum drawdown
    calmar_ratio = Column(Float)  # Calmar ratio
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    member = relationship("CongressMember", back_populates="portfolio_performance")
    
    __table_args__ = (
        UniqueConstraint('member_id', 'date'),
    )

# ============================================================================
# USER MANAGEMENT WITH SOCIAL INTEGRATION
# ============================================================================

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    username = Column(String(50), unique=True)  # Public username
    
    # Account Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    subscription_tier = Column(String(20), default='free')
    
    # User Profile
    bio = Column(Text)
    avatar_url = Column(String(500))
    location = Column(String(100))
    website = Column(String(200))
    
    # Social Integration OAuth Tokens (Encrypted)
    twitter_oauth_token = Column(Text)  # Encrypted OAuth token
    linkedin_oauth_token = Column(Text)
    discord_oauth_token = Column(Text)
    telegram_oauth_token = Column(Text)
    reddit_oauth_token = Column(Text)
    
    # Social Sharing Preferences
    auto_share_trades = Column(Boolean, default=False)
    share_on_twitter = Column(Boolean, default=False)
    share_on_linkedin = Column(Boolean, default=False)
    share_on_discord = Column(Boolean, default=False)
    share_on_telegram = Column(Boolean, default=False)
    share_on_reddit = Column(Boolean, default=False)
    
    # User Behavior Analytics (for ML/recommendations)
    login_count = Column(Integer, default=0)
    page_views = Column(Integer, default=0)
    trades_viewed = Column(Integer, default=0)
    members_followed = Column(Integer, default=0)
    
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
    member_follows = relationship("MemberFollow", back_populates="user")
    user_alerts = relationship("UserAlert", back_populates="user")
    social_posts = relationship("TradeSocialPost", back_populates="user")
    
    __table_args__ = (
        CheckConstraint(subscription_tier.in_(['free', 'pro', 'premium', 'enterprise']), name='check_subscription_tier'),
    )

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    plan_name = Column(String(50), nullable=False)
    status = Column(String(20), default='active')
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Payment Integration
    stripe_subscription_id = Column(String(100), unique=True)
    stripe_customer_id = Column(String(100))
    amount = Column(Integer, nullable=False)  # in cents
    currency = Column(String(3), default='USD')
    
    # Feature Access (for different tiers)
    api_calls_limit = Column(Integer, default=1000)  # Monthly API limit
    real_time_alerts = Column(Boolean, default=False)
    advanced_analytics = Column(Boolean, default=False)
    social_automation = Column(Boolean, default=False)
    white_label_access = Column(Boolean, default=False)
    
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
    
    # Notification Preferences
    email_notifications = Column(Boolean, default=True)
    trade_alerts = Column(Boolean, default=False)
    newsletter_frequency = Column(String(20), default='weekly')
    alert_threshold = Column(Integer, default=100000)  # in cents
    
    # Following & Watchlists
    watchlist_members = Column(ARRAY(Integer))
    favorite_sectors = Column(ARRAY(Integer))
    blocked_members = Column(ARRAY(Integer))
    
    # Social Sharing Templates
    twitter_template = Column(Text)  # Custom sharing template
    linkedin_template = Column(Text)
    discord_template = Column(Text)
    
    # Analytics Preferences
    preferred_timezone = Column(String(50), default='UTC')
    dashboard_layout = Column(JSONB)  # Custom dashboard configuration
    default_charts = Column(ARRAY(String(50)))  # Preferred chart types
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_preferences")
    
    __table_args__ = (
        UniqueConstraint('user_id'),
        CheckConstraint(newsletter_frequency.in_(['none', 'daily', 'weekly', 'monthly']), name='check_newsletter_frequency'),
    )

# ============================================================================
# SOCIAL FEATURES & MONETIZATION
# ============================================================================

class MemberFollow(Base):
    """Users can follow specific congress members for updates."""
    __tablename__ = 'member_follows'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    member_id = Column(Integer, ForeignKey('congress_members.id'), nullable=False)
    notification_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="member_follows")
    member = relationship("CongressMember", back_populates="member_alerts")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'member_id'),
    )

class TradeSocialPost(Base):
    """Social media posts about trades (user-generated or automated)."""
    __tablename__ = 'trade_social_posts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    trade_id = Column(Integer, ForeignKey('congressional_trades.id'), nullable=False)
    platform = Column(String(20), nullable=False)  # twitter, linkedin, discord, etc.
    post_content = Column(Text, nullable=False)
    external_post_id = Column(String(100))  # Platform-specific post ID
    posted_at = Column(DateTime(timezone=True))
    engagement_metrics = Column(JSONB)  # likes, shares, comments, etc.
    status = Column(String(20), default='draft')  # draft, posted, failed
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="social_posts")
    trade = relationship("CongressionalTrade", back_populates="trade_social_posts")
    
    __table_args__ = (
        CheckConstraint(platform.in_(['twitter', 'linkedin', 'discord', 'telegram', 'reddit', 'facebook']), name='check_platform'),
        CheckConstraint(status.in_(['draft', 'scheduled', 'posted', 'failed']), name='check_status'),
    )

class UserAlert(Base):
    """Customizable alerts for users."""
    __tablename__ = 'user_alerts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = Column(String(200), nullable=False)
    alert_type = Column(String(50), nullable=False)  # new_trade, price_movement, performance, etc.
    conditions = Column(JSONB, nullable=False)  # Alert conditions
    is_active = Column(Boolean, default=True)
    delivery_methods = Column(ARRAY(String(20)))  # email, push, discord, etc.
    
    # Premium features
    is_premium = Column(Boolean, default=False)
    priority_level = Column(Integer, default=1)  # 1-5, higher gets faster delivery
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_alerts")

class MemberAlert(Base):
    """System-generated alerts about congress members."""
    __tablename__ = 'member_alerts'
    
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey('congress_members.id'), nullable=False)
    alert_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    severity = Column(String(20), default='info')  # info, warning, critical
    metadata = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    member = relationship("CongressMember", back_populates="member_alerts")
    
    __table_args__ = (
        CheckConstraint(severity.in_(['info', 'warning', 'critical']), name='check_severity'),
    )

# ============================================================================
# MACHINE LEARNING & ANALYTICS
# ============================================================================

class MLModel(Base):
    """Track ML models and their performance."""
    __tablename__ = 'ml_models'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    model_type = Column(String(50), nullable=False)  # classification, regression, clustering
    version = Column(String(20), nullable=False)
    purpose = Column(String(200))  # What this model predicts
    
    # Model Metadata
    features_used = Column(ARRAY(String(100)))  # Feature names
    training_data_period = Column(String(50))  # Training period
    accuracy_score = Column(Float)
    precision_score = Column(Float)
    recall_score = Column(Float)
    f1_score = Column(Float)
    
    # Deployment Info
    is_active = Column(Boolean, default=False)
    deployed_at = Column(DateTime(timezone=True))
    model_file_path = Column(String(500))
    api_endpoint = Column(String(200))
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

class Prediction(Base):
    """Store ML model predictions."""
    __tablename__ = 'predictions'
    
    id = Column(BigInteger, primary_key=True)
    model_id = Column(Integer, ForeignKey('ml_models.id'), nullable=False)
    entity_type = Column(String(50), nullable=False)  # trade, member, security
    entity_id = Column(Integer, nullable=False)
    prediction_type = Column(String(50), nullable=False)  # price_movement, performance, etc.
    
    # Prediction Results
    predicted_value = Column(Float)
    confidence_score = Column(Float)
    probability_distribution = Column(JSONB)  # For classification models
    
    # Validation
    actual_value = Column(Float)  # Filled in later for model validation
    prediction_error = Column(Float)  # |predicted - actual|
    
    prediction_date = Column(DateTime(timezone=True), default=func.now())
    target_date = Column(DateTime(timezone=True))  # When prediction is for
    
    # Relationships
    model = relationship("MLModel")

# ============================================================================
# EMAIL NOTIFICATIONS (Enhanced)
# ============================================================================

class EmailCampaign(Base):
    __tablename__ = 'email_campaigns'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    template_id = Column(String(100))
    
    # Campaign Type & Targeting
    campaign_type = Column(String(50), default='newsletter')  # newsletter, alert, promotion
    target_audience = Column(JSONB)  # Targeting criteria
    personalization_data = Column(JSONB)  # Personalization variables
    
    # Scheduling
    scheduled_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    
    # Metrics
    recipient_count = Column(Integer, default=0)
    open_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    conversion_count = Column(Integer, default=0)  # Conversions to paid plans
    
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
    
    # Tracking
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    opened_at = Column(DateTime(timezone=True))
    clicked_at = Column(DateTime(timezone=True))
    bounced_at = Column(DateTime(timezone=True))
    
    # Personalization
    personalized_content = Column(JSONB)  # User-specific content
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    campaign = relationship("EmailCampaign", back_populates="email_sends")
    user = relationship("User", back_populates="email_sends")
    
    __table_args__ = (
        CheckConstraint(status.in_(['pending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed']), name='check_status'),
    )

# ============================================================================
# COMMUNITY FEATURES (Enhanced)
# ============================================================================

class DiscussionTopic(Base):
    __tablename__ = 'discussion_topics'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(50), default='general')
    tags = Column(ARRAY(String(50)))  # Topic tags
    
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    is_pinned = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    
    # Engagement Metrics
    post_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    last_post_at = Column(DateTime(timezone=True))
    
    # Premium Features
    is_premium_only = Column(Boolean, default=False)
    expert_verified = Column(Boolean, default=False)
    
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
    
    # Content Management
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime(timezone=True))
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True))
    
    # Engagement
    like_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    
    # Moderation
    is_flagged = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)  # Expert/verified user posts
    
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
# SYSTEM TABLES (Enhanced)
# ============================================================================

class IngestionLog(Base):
    __tablename__ = 'ingestion_logs'
    
    id = Column(BigInteger, primary_key=True)
    source = Column(String(50), nullable=False)
    batch_id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    
    # Processing Stats
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Execution Info
    status = Column(String(20), default='running')
    error_message = Column(Text)
    execution_time_seconds = Column(Float)
    
    # Rich Metadata
    metadata = Column(JSONB)
    performance_metrics = Column(JSONB)  # Memory usage, CPU time, etc.
    
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
    
    # Request Details
    ip_address = Column(INET)
    user_agent = Column(Text)
    request_size_bytes = Column(Integer)
    response_size_bytes = Column(Integer)
    
    # Rate Limiting
    rate_limit_key = Column(String(100))  # For rate limiting groups
    is_rate_limited = Column(Boolean, default=False)
    
    # Premium Features
    api_key_used = Column(String(100))  # For API key tracking
    plan_tier = Column(String(20))  # User's plan at time of request
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="api_usage")

# ============================================================================
# REVENUE & ANALYTICS TRACKING
# ============================================================================

class RevenueEvent(Base):
    """Track revenue events for analytics."""
    __tablename__ = 'revenue_events'
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    event_type = Column(String(50), nullable=False)  # subscription, upgrade, addon, etc.
    amount = Column(Integer, nullable=False)  # in cents
    currency = Column(String(3), default='USD')
    
    # Event Details
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'))
    plan_from = Column(String(50))  # Previous plan
    plan_to = Column(String(50))  # New plan
    
    # Attribution
    referral_source = Column(String(100))
    campaign_id = Column(String(100))
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User")
    subscription = relationship("Subscription")

class UserEngagement(Base):
    """Track user engagement for ML and analytics."""
    __tablename__ = 'user_engagement'
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    date = Column(Date, nullable=False)
    
    # Engagement Metrics
    page_views = Column(Integer, default=0)
    time_spent_seconds = Column(Integer, default=0)
    trades_viewed = Column(Integer, default=0)
    members_viewed = Column(Integer, default=0)
    searches_performed = Column(Integer, default=0)
    alerts_created = Column(Integer, default=0)
    social_shares = Column(Integer, default=0)
    
    # Feature Usage
    features_used = Column(ARRAY(String(50)))
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'date'),
    ) 