"""
Congressional domain database models.

This module contains SQLAlchemy models for congress members, their trades,
and portfolio tracking. Supports CAP-10 (Transaction List) and CAP-11 (Member Profiles).
"""

import uuid
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, DateTime, 
    BigInteger, ForeignKey, CheckConstraint,
    UniqueConstraint, Index, ARRAY
)
from sqlalchemy.types import Numeric as SQLDecimal
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from domains.base.models import CapitolScopeBaseModel, ActiveRecordMixin, MetadataMixin, AuditMixin
from core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# CONGRESS MEMBERS
# ============================================================================

class CongressMember(CapitolScopeBaseModel, ActiveRecordMixin, MetadataMixin, AuditMixin):
    """Congress member model for representatives and senators."""
    
    __tablename__ = 'congress_members'
    
    # Basic Information
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    full_name = Column(String(200), nullable=False, index=True)
    prefix = Column(String(10), index=True)  # Honorifics like "Rep.", "Sen.", "Dr.", "Mr.", "Ms."
    party = Column(String(1), index=True)  # D, R, I
    chamber = Column(String(6), nullable=False, index=True)  # House, Senate
    
    # Geographic Information
    state = Column(String(2), nullable=False, index=True)  # Two-letter state code
    district = Column(String(10))  # For House members (e.g., "01", "02", "AL" for at-large)
    
    # Contact and Bio Information
    email = Column(String(255))
    phone = Column(String(20))
    office_address = Column(Text)
    
    # Congressional Identifiers
    bioguide_id = Column(String(10), unique=True, index=True)
    congress_gov_id = Column(String(20), unique=True, index=True)  # ID from Congress.gov API
    
    # Term Information
    term_start = Column(Date)
    term_end = Column(Date)
    congress_number = Column(Integer)  # e.g., 118 for 118th Congress
    
    # Professional Background
    age = Column(Integer)
    education = Column(Text)
    profession = Column(String(200))
    
    # Committee Information
    committees = Column(ARRAY(String))  # Array of committee names
    leadership_roles = Column(ARRAY(String))  # Array of leadership positions
    
    # Social Media and Links
    twitter_handle = Column(String(50))
    facebook_url = Column(String(255))
    website_url = Column(String(255))
    
    # Congressional Data
    seniority_rank = Column(Integer)
    vote_percentage = Column(SQLDecimal(5, 2))  # Voting participation percentage
    
    # Premium Features
    influence_score = Column(SQLDecimal(5, 2))  # Calculated influence score (0-100)
    fundraising_total = Column(BigInteger)  # Total fundraising in cents
    pac_contributions = Column(BigInteger)  # PAC contributions in cents
    
    # Research Links
    wikipedia_url = Column(String(255))
    ballotpedia_url = Column(String(255))
    opensecrets_url = Column(String(255))
    govtrack_id = Column(String(20))
    votesmart_id = Column(String(20))
    fec_id = Column(String(20))
    
    # Relationships
    congressional_trades = relationship("CongressionalTrade", back_populates="member", cascade="all, delete-orphan")
    member_portfolios = relationship("MemberPortfolio", back_populates="member", cascade="all, delete-orphan")
    member_portfolio_performance = relationship("MemberPortfolioPerformance", back_populates="member", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        CheckConstraint(party.in_(['D', 'R', 'I']), name='check_party'),
        CheckConstraint(chamber.in_(['House', 'Senate']), name='check_chamber'),
        Index('idx_congress_member_name', 'first_name', 'last_name'),
        Index('idx_congress_member_party_chamber', 'party', 'chamber'),
        Index('idx_congress_member_state_district', 'state', 'district'),
    )
    
    def __repr__(self):
        return f"<CongressMember(name={self.full_name}, party={self.party}, chamber={self.chamber})>"
    
    @property
    def display_name(self) -> str:
        """Return a formatted display name with title."""
        title = "Rep." if self.chamber == "House" else "Sen."
        return f"{title} {self.full_name}"
    
    @property
    def state_district(self) -> str:
        """Return formatted state and district."""
        if self.chamber == "House" and self.district:
            return f"{self.state}-{self.district}"
        return self.state
    
    @property
    def party_full_name(self) -> str:
        """Return full party name."""
        party_map = {
            'D': 'Democrat',
            'R': 'Republican', 
            'I': 'Independent'
        }
        return party_map.get(self.party, 'Unknown')
    
    def get_total_trade_value(self) -> int:
        """Calculate total trade value for this member."""
        total = 0
        for trade in self.congressional_trades:
            if trade.amount_exact:
                total += trade.amount_exact
            elif trade.amount_min and trade.amount_max:
                total += (trade.amount_min + trade.amount_max) // 2
        return total
    
    def get_trade_count(self) -> int:
        """Get total number of trades."""
        return len(self.congressional_trades)


# ============================================================================
# CONGRESSIONAL TRADES
# ============================================================================

class CongressionalTrade(CapitolScopeBaseModel, AuditMixin):
    """Congressional trade disclosure model."""
    
    __tablename__ = 'congressional_trades'
    
    # Member and Security References
    member_id = Column(UUID(as_uuid=True), ForeignKey('congress_members.id'), nullable=False, index=True)
    security_id = Column(UUID(as_uuid=True), ForeignKey('securities.id'), index=True)  # May be null if not matched
    
    # Document Information
    doc_id = Column(String(50), nullable=False, index=True)  # Disclosure document ID
    document_url = Column(String(500))  # URL to original document
    
    # Trade Details
    owner = Column(String(10))  # SP (Spouse), JT (Joint), DC (Dependent Child), C (Self)
    raw_asset_description = Column(Text, nullable=False)  # Original asset description from filing
    ticker = Column(String(20), index=True)  # Parsed ticker symbol
    asset_name = Column(String(300))  # Parsed asset name
    asset_type = Column(String(100))  # Stock, Bond, Option, etc.
    
    # Transaction Information
    transaction_type = Column(String(2), nullable=False, index=True)  # P (Purchase), S (Sale), E (Exchange)
    transaction_date = Column(Date, nullable=False, index=True)
    notification_date = Column(Date, nullable=False, index=True)  # Date disclosed
    
    # Amount Information (all in cents)
    amount_min = Column(BigInteger)  # Minimum amount from range
    amount_max = Column(BigInteger)  # Maximum amount from range  
    amount_exact = Column(BigInteger)  # Exact amount if disclosed
    
    # Filing Information
    filing_status = Column(String(1))  # N (New), P (Partial), A (Amendment)
    comment = Column(Text)
    cap_gains_over_200 = Column(Boolean, default=False)  # Capital gains over $200
    
    # Data Quality and Processing
    ticker_confidence = Column(SQLDecimal(3, 2))  # Confidence in ticker parsing (0-1)
    amount_confidence = Column(SQLDecimal(3, 2))  # Confidence in amount parsing (0-1)
    parsed_successfully = Column(Boolean, default=True)
    parsing_notes = Column(Text)
    
    # ML Features for Analysis
    market_cap_at_trade = Column(BigInteger)  # Market cap when trade occurred
    price_at_trade = Column(Integer)  # Security price when trade occurred (cents)
    volume_at_trade = Column(BigInteger)  # Trading volume when trade occurred
    
    # Performance Tracking
    price_change_1d = Column(SQLDecimal(8, 6))  # 1-day price change after trade
    price_change_7d = Column(SQLDecimal(8, 6))  # 7-day price change after trade
    price_change_30d = Column(SQLDecimal(8, 6))  # 30-day price change after trade
    
    # Relationships
    member = relationship("CongressMember", back_populates="congressional_trades")
    security = relationship("Security", foreign_keys=[security_id])  # From securities domain
    
    # Indexes and constraints
    __table_args__ = (
        CheckConstraint(owner.in_(['SP', 'JT', 'DC', 'C']), name='check_owner'),
        CheckConstraint(transaction_type.in_(['P', 'S', 'E']), name='check_transaction_type'),
        CheckConstraint(filing_status.in_(['N', 'P', 'A']), name='check_filing_status'),
        Index('idx_congressional_trade_member_date', 'member_id', 'transaction_date'),
        Index('idx_congressional_trade_ticker_date', 'ticker', 'transaction_date'),
        Index('idx_congressional_trade_security_date', 'security_id', 'transaction_date'),
        Index('idx_congressional_trade_type_date', 'transaction_type', 'transaction_date'),
    )
    
    def __repr__(self):
        return f"<CongressionalTrade(member_id={self.member_id}, ticker={self.ticker}, type={self.transaction_type}, date={self.transaction_date})>"
    
    @property
    def estimated_value(self) -> Optional[int]:
        """Get estimated trade value in cents."""
        if self.amount_exact:
            return self.amount_exact
        elif self.amount_min and self.amount_max:
            return (self.amount_min + self.amount_max) // 2
        return None
    
    @property
    def days_to_disclosure(self) -> Optional[int]:
        """Calculate days between trade and disclosure."""
        if self.transaction_date and self.notification_date:
            return (self.notification_date - self.transaction_date).days
        return None
    
    def get_formatted_amount(self) -> str:
        """Return formatted amount string."""
        if self.amount_exact:
            return f"${self.amount_exact / 100:,.2f}"
        elif self.amount_min and self.amount_max:
            return f"${self.amount_min / 100:,.0f} - ${self.amount_max / 100:,.0f}"
        return "Unknown"
    
    def get_transaction_type_display(self) -> str:
        """Return human-readable transaction type."""
        type_map = {
            'P': 'Purchase',
            'S': 'Sale',
            'E': 'Exchange'
        }
        return type_map.get(self.transaction_type, 'Unknown')
    
    def get_owner_display(self) -> str:
        """Return human-readable owner."""
        owner_map = {
            'SP': 'Spouse',
            'JT': 'Joint',
            'DC': 'Dependent Child',
            'C': 'Self'
        }
        return owner_map.get(self.owner, 'Unknown')


# ============================================================================
# MEMBER PORTFOLIOS
# ============================================================================

class MemberPortfolio(CapitolScopeBaseModel):
    """Member portfolio holdings tracking."""
    
    __tablename__ = 'member_portfolios'
    
    # References
    member_id = Column(UUID(as_uuid=True), ForeignKey('congress_members.id'), nullable=False, index=True)
    security_id = Column(UUID(as_uuid=True), ForeignKey('securities.id'), nullable=False, index=True)
    
    # Position Information
    shares = Column(SQLDecimal(15, 6), nullable=False, default=0)  # Number of shares held
    cost_basis = Column(BigInteger, nullable=False, default=0)  # Total cost basis in cents
    avg_cost_per_share = Column(BigInteger)  # Average cost per share in cents
    
    # Transaction History
    first_purchase_date = Column(Date, index=True)
    last_transaction_date = Column(Date, index=True)
    total_purchases = Column(Integer, default=0)  # Number of purchase transactions
    total_sales = Column(Integer, default=0)  # Number of sale transactions
    
    # Performance Tracking
    unrealized_gain_loss = Column(BigInteger)  # Current unrealized gain/loss in cents
    realized_gain_loss = Column(BigInteger, default=0)  # Total realized gain/loss in cents
    
    # Portfolio Analysis
    position_size_percent = Column(SQLDecimal(5, 2))  # Percentage of total portfolio
    holding_period_days = Column(Integer)  # Days since first purchase
    
    # Relationships
    member = relationship("CongressMember", back_populates="member_portfolios")
    security = relationship("Security", foreign_keys=[security_id])  # From securities domain
    
    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('member_id', 'security_id', name='unique_member_security'),
        Index('idx_member_portfolio_member', 'member_id'),
        Index('idx_member_portfolio_security', 'security_id'),
        Index('idx_member_portfolio_last_transaction', 'last_transaction_date'),
    )
    
    def __repr__(self):
        return f"<MemberPortfolio(member_id={self.member_id}, security_id={self.security_id}, shares={self.shares})>"
    
    @property
    def current_value(self) -> Optional[int]:
        """Calculate current position value."""
        if self.shares and self.security and hasattr(self.security, 'current_price'):
            return int(float(self.shares) * self.security.current_price)
        return None
    
    def calculate_unrealized_gain_loss_percent(self) -> Optional[float]:
        """Calculate unrealized gain/loss percentage."""
        if self.cost_basis and self.current_value and self.cost_basis > 0:
            return ((self.current_value - self.cost_basis) / self.cost_basis) * 100
        return None
    
    def update_position(self, transaction_type: str, shares: float, price_per_share: int, transaction_date: date):
        """Update position based on a new transaction."""
        if transaction_type == 'P':  # Purchase
            old_cost_basis = self.cost_basis or 0
            old_shares = float(self.shares or 0)
            
            # Update shares and cost basis
            new_shares = old_shares + shares
            new_cost_basis = old_cost_basis + int(shares * price_per_share)
            
            self.shares = Decimal(str(new_shares))
            self.cost_basis = new_cost_basis
            self.avg_cost_per_share = new_cost_basis // int(new_shares) if new_shares > 0 else 0
            self.total_purchases = (self.total_purchases or 0) + 1
            
            if not self.first_purchase_date:
                self.first_purchase_date = transaction_date
                
        elif transaction_type == 'S':  # Sale
            old_shares = float(self.shares or 0)
            
            if old_shares >= shares:
                # Calculate realized gain/loss for sold shares
                avg_cost = self.avg_cost_per_share or 0
                sale_proceeds = int(shares * price_per_share)
                sale_cost_basis = int(shares * avg_cost)
                realized_gain = sale_proceeds - sale_cost_basis
                
                # Update position
                new_shares = old_shares - shares
                self.shares = Decimal(str(new_shares))
                
                # Reduce cost basis proportionally
                if old_shares > 0:
                    remaining_percent = new_shares / old_shares
                    self.cost_basis = int(self.cost_basis * remaining_percent)
                
                self.realized_gain_loss = (self.realized_gain_loss or 0) + realized_gain
                self.total_sales = (self.total_sales or 0) + 1
        
        self.last_transaction_date = transaction_date
        self.holding_period_days = (transaction_date - self.first_purchase_date).days if self.first_purchase_date else 0


# ============================================================================
# PORTFOLIO PERFORMANCE
# ============================================================================

class MemberPortfolioPerformance(CapitolScopeBaseModel):
    """Member portfolio performance tracking."""
    
    __tablename__ = 'member_portfolio_performance'
    
    # References
    member_id = Column(UUID(as_uuid=True), ForeignKey('congress_members.id'), nullable=False, index=True)
    
    # Performance data
    date = Column(Date, nullable=False, index=True)
    total_value = Column(BigInteger, nullable=False)  # Total portfolio value in cents
    total_gain_loss = Column(BigInteger, default=0)  # Total gain/loss in cents
    total_gain_loss_percent = Column(SQLDecimal(8, 4))  # Total gain/loss percentage
    
    # Performance metrics
    daily_return = Column(SQLDecimal(8, 4))  # Daily return percentage
    weekly_return = Column(SQLDecimal(8, 4))  # Weekly return percentage
    monthly_return = Column(SQLDecimal(8, 4))  # Monthly return percentage
    ytd_return = Column(SQLDecimal(8, 4))  # Year-to-date return percentage
    
    # Risk metrics
    volatility = Column(SQLDecimal(8, 4))  # Portfolio volatility
    beta = Column(SQLDecimal(6, 3))  # Portfolio beta vs market
    sharpe_ratio = Column(SQLDecimal(8, 4))  # Sharpe ratio
    max_drawdown = Column(SQLDecimal(8, 4))  # Maximum drawdown
    
    # Benchmark comparison
    sp500_return = Column(SQLDecimal(8, 4))  # S&P 500 return for comparison
    alpha = Column(SQLDecimal(8, 4))  # Alpha vs S&P 500
    
    # Portfolio composition
    number_of_positions = Column(Integer, default=0)
    largest_position_percent = Column(SQLDecimal(5, 2))
    sector_concentration = Column(SQLDecimal(5, 2))
    
    # Relationships
    member = relationship("CongressMember", back_populates="member_portfolio_performance")
    
    # Indexes and constraints
    __table_args__ = (
        Index('idx_member_portfolio_performance_member_date', 'member_id', 'date'),
        Index('idx_member_portfolio_performance_date', 'date'),
        UniqueConstraint('member_id', 'date', name='unique_member_performance_date'),
    )
    
    def __repr__(self):
        return f"<MemberPortfolioPerformance(member_id={self.member_id}, date={self.date}, value={self.total_value})>"
    
    def get_formatted_total_value(self) -> str:
        """Return formatted total value."""
        if self.total_value:
            return f"${self.total_value / 100:,.2f}"
        return "N/A"
    
    def get_formatted_gain_loss(self) -> str:
        """Return formatted gain/loss."""
        if self.total_gain_loss:
            sign = "+" if self.total_gain_loss > 0 else ""
            return f"{sign}${self.total_gain_loss / 100:,.2f}"
        return "N/A"


# ============================================================================
# TRADE DISCUSSIONS (Community Feature)
# ============================================================================

class TradeDiscussion(CapitolScopeBaseModel):
    """Links trades to community discussions."""
    
    __tablename__ = 'trade_discussions'
    
    trade_id = Column(UUID(as_uuid=True), ForeignKey('congressional_trades.id'), nullable=False, index=True)
    topic_id = Column(Integer, nullable=False, index=True)  # Will link to discussion_topics when implemented
    
    # Discussion metadata
    post_count = Column(Integer, default=0)
    last_post_at = Column(DateTime(timezone=True))
    
    # Relationships
    trade = relationship("CongressionalTrade")
    
    __table_args__ = (
        UniqueConstraint('trade_id', name='unique_trade_discussion'),
        Index('idx_trade_discussion_topic', 'topic_id'),
    )
    
    def __repr__(self):
        return f"<TradeDiscussion(trade_id={self.trade_id}, topic_id={self.topic_id})>"


# Log model creation
logger.info("Congressional domain models initialized")

# Export all models
__all__ = [
    "CongressMember",
    "CongressionalTrade", 
    "MemberPortfolio",
    "MemberPortfolioPerformance",
    "TradeDiscussion"
] 