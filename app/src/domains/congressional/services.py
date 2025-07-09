"""
Congressional domain services.

This module contains business logic services for congressional domain operations.
Supports CAP-10 (Transaction List) and CAP-11 (Member Profiles).
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from domains.base.services import BaseService
from domains.congressional.interfaces import (
    CongressMemberServiceInterface, CongressionalTradeServiceInterface,
    PortfolioServiceInterface, CongressionalAnalyticsInterface,
    TradeDataProcessorInterface, TradeEnrichmentInterface
)
from domains.congressional.crud import (
    CongressMemberRepository, CongressionalTradeRepository,
    MemberPortfolioRepository, PortfolioPerformanceRepository
)
from domains.congressional.schemas import (
    CongressMemberCreate, CongressMemberUpdate, CongressMemberDetail, CongressMemberSummary,
    CongressionalTradeCreate, CongressionalTradeUpdate, CongressionalTradeDetail,
    CongressionalTradeFilter, MemberPortfolioSummary, PortfolioPerformanceSummary,
    TradingStatistics, MemberAnalytics, MarketPerformanceComparison
)
from core.exceptions import NotFoundError, ValidationError, BusinessLogicError
from core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# CONGRESS MEMBER SERVICE
# ============================================================================

class CongressMemberService(BaseService, CongressMemberServiceInterface):
    """Service for congress member business logic."""
    
    def __init__(
        self,
        member_repo: CongressMemberRepository,
        trade_repo: CongressionalTradeRepository,
        portfolio_repo: MemberPortfolioRepository,
        performance_repo: PortfolioPerformanceRepository
    ):
        self.member_repo = member_repo
        self.trade_repo = trade_repo
        self.portfolio_repo = portfolio_repo
        self.performance_repo = performance_repo
    
    async def create_member(self, member_data: CongressMemberCreate) -> CongressMemberDetail:
        """Create a new congress member with validation."""
        # Validate bioguide_id uniqueness
        if member_data.bioguide_id:
            existing = await self.member_repo.get_by_bioguide_id(member_data.bioguide_id)
            if existing:
                raise ValidationError(f"Member with bioguide_id {member_data.bioguide_id} already exists")
        
        # Generate full name if not provided
        if not member_data.full_name:
            member_data.full_name = f"{member_data.first_name} {member_data.last_name}"
        
        logger.info(f"Creating congress member: {member_data.full_name}")
        return await self.member_repo.create(member_data)
    
    async def update_member(self, member_id: int, update_data: CongressMemberUpdate) -> CongressMemberDetail:
        """Update congress member with business rules."""
        existing = await self.member_repo.get_by_id(member_id)
        if not existing:
            raise NotFoundError(f"Congress member {member_id} not found")
        
        # Update full name if first/last name changed
        if update_data.first_name or update_data.last_name:
            first_name = update_data.first_name or existing.first_name
            last_name = update_data.last_name or existing.last_name
            update_data.full_name = f"{first_name} {last_name}"
        
        logger.info(f"Updating congress member: {member_id}")
        return await self.member_repo.update(member_id, update_data)
    
    async def get_member_profile(self, member_id: int) -> CongressMemberDetail:
        """Get complete member profile with analytics."""
        member = await self.member_repo.get_by_id(member_id)
        if not member:
            raise NotFoundError(f"Congress member {member_id} not found")
        
        # Enhance with computed fields
        member_dict = member.dict()
        
        # Add trade statistics
        stats = await self.member_repo.get_trading_statistics(member_id)
        member_dict['trade_count'] = stats.total_trades
        member_dict['total_trade_value'] = stats.total_value
        
        # Add portfolio value
        portfolio_value = await self.portfolio_repo.calculate_portfolio_value(member_id)
        member_dict['portfolio_value'] = portfolio_value
        
        return CongressMemberDetail(**member_dict)
    
    async def get_member_analytics(self, member_id: int) -> MemberAnalytics:
        """Get comprehensive analytics for a member."""
        member = await self.member_repo.get_by_id(member_id)
        if not member:
            raise NotFoundError(f"Congress member {member_id} not found")
        
        # Get trading statistics
        trading_stats = await self.member_repo.get_trading_statistics(member_id)
        
        # Get portfolio summary
        portfolio_value = await self.portfolio_repo.calculate_portfolio_value(member_id)
        latest_performance = await self.performance_repo.get_latest_performance(member_id)
        
        portfolio_summary = None
        if latest_performance:
            portfolio_summary = CongressMemberPortfolioSummary(
                member_id=member_id,
                total_value=latest_performance.total_value,
                total_cost_basis=latest_performance.total_cost_basis,
                unrealized_gain_loss=latest_performance.unrealized_gain_loss,
                realized_gain_loss=latest_performance.realized_gain_loss,
                position_count=latest_performance.position_count
            )
        
        # Get top positions
        top_positions = await self.portfolio_repo.get_top_positions(member_id, limit=5)
        
        # Get recent trades
        recent_trades = await self.trade_repo.get_member_trades(member_id, limit=10)
        
        return MemberAnalytics(
            member_id=member_id,
            trading_stats=trading_stats,
            portfolio_summary=portfolio_summary,
            top_positions=top_positions,
            recent_trades=recent_trades
        )
    
    async def sync_member_data(self, bioguide_id: str) -> CongressMemberDetail:
        """Sync member data from external sources."""
        # This would integrate with external APIs like Congress.gov
        # For now, just return existing member
        member = await self.member_repo.get_by_bioguide_id(bioguide_id)
        if not member:
            raise NotFoundError(f"Member with bioguide_id {bioguide_id} not found")
        
        logger.info(f"Syncing member data for bioguide_id: {bioguide_id}")
        return member
    
    async def calculate_influence_score(self, member_id: int) -> Decimal:
        """Calculate influence score based on various factors."""
        # Implementation would consider:
        # - Committee positions
        # - Leadership roles
        # - Trading activity impact
        # - Fundraising totals
        # - Voting record
        
        member = await self.member_repo.get_by_id(member_id)
        if not member:
            raise NotFoundError(f"Congress member {member_id} not found")
        
        # Basic score calculation
        score = Decimal('50.0')  # Base score
        
        # Adjust for leadership roles
        if member.leadership_roles:
            score += Decimal('20.0')
        
        # Adjust for committee count
        if member.committees:
            score += min(Decimal('10.0'), len(member.committees) * Decimal('2.0'))
        
        # Adjust for seniority
        if member.seniority_rank and member.seniority_rank <= 10:
            score += Decimal('15.0')
        elif member.seniority_rank and member.seniority_rank <= 50:
            score += Decimal('10.0')
        
        return min(score, Decimal('100.0'))
    
    async def get_similar_members(self, member_id: int, limit: int = 5) -> List[CongressMemberSummary]:
        """Find members with similar trading patterns."""
        # This would implement similarity algorithms based on:
        # - Trading frequency
        # - Asset preferences
        # - Performance patterns
        # - Sector allocations
        
        # For now, return members from same party/chamber
        member = await self.member_repo.get_by_id(member_id)
        if not member:
            raise NotFoundError(f"Congress member {member_id} not found")
        
        # Simple similarity: same party and chamber
        from domains.congressional.schemas import MemberQuery
        query = MemberQuery(
            parties=[member.party] if member.party else None,
            chambers=[member.chamber],
            limit=limit + 1  # +1 to exclude self
        )
        
        similar_members, _ = await self.member_repo.list_members(query)
        
        # Remove the member themselves
        return [m for m in similar_members if m.id != member_id][:limit]


# ============================================================================
# CONGRESSIONAL TRADE SERVICE
# ============================================================================

class CongressionalTradeService(BaseService, CongressionalTradeServiceInterface):
    """Service for congressional trade business logic."""
    
    def __init__(
        self,
        trade_repo: CongressionalTradeRepository,
        member_repo: CongressMemberRepository,
        portfolio_service: Optional['PortfolioService'] = None
    ):
        self.trade_repo = trade_repo
        self.member_repo = member_repo
        self.portfolio_service = portfolio_service
    
    async def process_trade_filing(self, filing_data: Dict[str, Any]) -> List[CongressionalTradeDetail]:
        """Process raw trade filing data into structured trades."""
        # This would parse trade disclosure documents
        # For now, create a single trade from the data
        
        if 'trades' not in filing_data:
            raise ValidationError("Filing data must contain 'trades' list")
        
        created_trades = []
        for trade_data in filing_data['trades']:
            try:
                trade_create = CongressionalTradeCreate(**trade_data)
                
                # Validate trade data
                if await self.validate_trade_data(trade_create):
                    trade = await self.trade_repo.create(trade_create)
                    created_trades.append(trade)
                    
                    # Update portfolio if service available
                    if self.portfolio_service:
                        await self.portfolio_service.update_member_portfolio(trade)
                
            except ValidationError as e:
                logger.warning(f"Skipping invalid trade: {e}")
                continue
        
        logger.info(f"Processed filing: created {len(created_trades)} trades")
        return created_trades
    
    async def validate_trade_data(self, trade_data: CongressionalTradeCreate) -> bool:
        """Validate trade data for consistency and completeness."""
        # Check if member exists
        member = await self.member_repo.get_by_id(trade_data.member_id)
        if not member:
            raise ValidationError(f"Member {trade_data.member_id} not found")
        
        # Check disclosure timing (45 days max)
        days_to_disclosure = (trade_data.notification_date - trade_data.transaction_date).days
        if days_to_disclosure > 45:
            logger.warning(f"Late disclosure: {days_to_disclosure} days")
        
        # Validate amount consistency
        if trade_data.amount_exact and trade_data.amount_min and trade_data.amount_max:
            if not (trade_data.amount_min <= trade_data.amount_exact <= trade_data.amount_max):
                raise ValidationError("Exact amount must be within min/max range")
        
        return True
    
    async def enrich_trade_data(self, trade_id: int) -> CongressionalTradeDetail:
        """Enrich trade with security information and market data."""
        trade = await self.trade_repo.get_by_id(trade_id)
        if not trade:
            raise NotFoundError(f"Trade {trade_id} not found")
        
        # This would:
        # 1. Match asset description to securities database
        # 2. Add market data at trade date
        # 3. Calculate performance metrics
        # 4. Update confidence scores
        
        logger.info(f"Enriching trade data for trade: {trade_id}")
        return trade
    
    async def detect_duplicate_trades(self, trade_data: CongressionalTradeCreate) -> List[CongressionalTradeDetail]:
        """Detect potential duplicate trades."""
        # Look for trades with same member, ticker, date, and amount
        filters = CongressionalTradeFilter(
            member_ids=[trade_data.member_id],
            transaction_date_from=trade_data.transaction_date,
            transaction_date_to=trade_data.transaction_date
        )
        
        if trade_data.ticker:
            filters.tickers = [trade_data.ticker]
        
        from domains.congressional.schemas import CongressionalTradeQuery
        query = CongressionalTradeQuery(**filters.dict())
        
        similar_trades, _ = await self.trade_repo.list_trades(query)
        
        # Check for duplicates based on amount similarity
        duplicates = []
        trade_amount = trade_data.amount_exact or ((trade_data.amount_min + trade_data.amount_max) / 2 if trade_data.amount_min and trade_data.amount_max else 0)
        
        for existing_trade in similar_trades:
            existing_amount = existing_trade.estimated_value or 0
            if abs(trade_amount - existing_amount) < (trade_amount * 0.1):  # 10% threshold
                trade_detail = await self.trade_repo.get_by_id(existing_trade.id)
                if trade_detail:
                    duplicates.append(trade_detail)
        
        return duplicates
    
    async def calculate_trade_performance(self, trade_id: int) -> Dict[str, Decimal]:
        """Calculate performance metrics for a trade."""
        trade = await self.trade_repo.get_by_id(trade_id)
        if not trade:
            raise NotFoundError(f"Trade {trade_id} not found")
        
        # This would calculate:
        # - Price changes at various intervals
        # - Relative performance vs market
        # - Risk-adjusted returns
        
        performance = {
            'price_change_1d': trade.price_change_1d or Decimal('0'),
            'price_change_7d': trade.price_change_7d or Decimal('0'),
            'price_change_30d': trade.price_change_30d or Decimal('0')
        }
        
        return performance
    
    async def analyze_trading_patterns(self, member_id: int) -> Dict[str, Any]:
        """Analyze trading patterns for a member."""
        member = await self.member_repo.get_by_id(member_id)
        if not member:
            raise NotFoundError(f"Member {member_id} not found")
        
        # Get all member trades
        trades = await self.trade_repo.get_member_trades(member_id)
        
        # Analyze patterns
        patterns = {
            'total_trades': len(trades),
            'avg_trade_size': 0,
            'most_active_months': {},
            'preferred_transaction_types': {},
            'sector_preferences': {},
            'timing_patterns': {}
        }
        
        if trades:
            # Calculate average trade size
            total_value = sum(trade.estimated_value or 0 for trade in trades)
            patterns['avg_trade_size'] = total_value // len(trades) if trades else 0
            
            # Transaction type preferences
            type_counts = {}
            for trade in trades:
                type_counts[trade.transaction_type] = type_counts.get(trade.transaction_type, 0) + 1
            patterns['preferred_transaction_types'] = type_counts
        
        return patterns
    
    async def get_trade_insights(self, filters: CongressionalTradeFilter) -> Dict[str, Any]:
        """Get insights from filtered trade data."""
        from domains.congressional.schemas import CongressionalTradeQuery
        query = CongressionalTradeQuery(**filters.dict(), limit=10000)  # Large limit for analysis
        
        trades, total_count = await self.trade_repo.list_trades(query)
        
        insights = {
            'total_trades': total_count,
            'total_value': sum(trade.estimated_value or 0 for trade in trades),
            'avg_trade_size': 0,
            'top_tickers': {},
            'party_breakdown': {},
            'chamber_breakdown': {},
            'transaction_type_breakdown': {}
        }
        
        if trades:
            insights['avg_trade_size'] = insights['total_value'] // len(trades)
            
            # Count by various dimensions
            ticker_counts = {}
            party_counts = {}
            chamber_counts = {}
            type_counts = {}
            
            for trade in trades:
                if trade.ticker:
                    ticker_counts[trade.ticker] = ticker_counts.get(trade.ticker, 0) + 1
                if trade.member_party:
                    party_counts[trade.member_party] = party_counts.get(trade.member_party, 0) + 1
                if trade.member_chamber:
                    chamber_counts[trade.member_chamber] = chamber_counts.get(trade.member_chamber, 0) + 1
                type_counts[trade.transaction_type] = type_counts.get(trade.transaction_type, 0) + 1
            
            insights['top_tickers'] = dict(sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            insights['party_breakdown'] = party_counts
            insights['chamber_breakdown'] = chamber_counts
            insights['transaction_type_breakdown'] = type_counts
        
        return insights


# ============================================================================
# PORTFOLIO SERVICE
# ============================================================================

class PortfolioService(BaseService, PortfolioServiceInterface):
    """Service for portfolio management business logic."""
    
    def __init__(
        self,
        portfolio_repo: MemberPortfolioRepository,
        performance_repo: PortfolioPerformanceRepository,
        trade_repo: CongressionalTradeRepository
    ):
        self.portfolio_repo = portfolio_repo
        self.performance_repo = performance_repo
        self.trade_repo = trade_repo
    
    async def update_member_portfolio(self, trade: CongressionalTradeDetail) -> List[MemberPortfolioSummary]:
        """Update member portfolio based on a new trade."""
        if not trade.security_id:
            logger.warning(f"Trade {trade.id} has no security_id, skipping portfolio update")
            return []
        
        # Estimate shares traded (simplified calculation)
        trade_value = trade.estimated_value or 0
        if trade.price_at_trade and trade.price_at_trade > 0:
            shares = Decimal(str(trade_value / trade.price_at_trade))
        else:
            # Use current price or default
            shares = Decimal('100')  # Default estimate
        
        transaction_data = {
            'transaction_type': trade.transaction_type,
            'shares': float(shares),
            'price_per_share': trade.price_at_trade or 10000,  # Default $100.00
            'transaction_date': trade.transaction_date
        }
        
        # Update position
        updated_position = await self.portfolio_repo.update_position(
            trade.member_id,
            trade.security_id,
            transaction_data
        )
        
        logger.info(f"Updated portfolio position for member {trade.member_id}, security {trade.security_id}")
        
        # Return updated portfolio
        return await self.portfolio_repo.get_member_portfolio(trade.member_id)
    
    async def calculate_daily_performance(self, member_id: int, date: date) -> PortfolioPerformanceSummary:
        """Calculate and record daily portfolio performance."""
        # Get current portfolio
        portfolio = await self.portfolio_repo.get_member_portfolio(member_id)
        
        # Calculate portfolio values
        total_value = sum(pos.cost_basis for pos in portfolio)  # Simplified
        total_cost_basis = sum(pos.cost_basis for pos in portfolio)
        unrealized_gain_loss = 0  # Would calculate with current prices
        realized_gain_loss = sum(pos.realized_gain_loss or 0 for pos in portfolio)
        
        performance_data = {
            'total_value': total_value,
            'total_cost_basis': total_cost_basis,
            'unrealized_gain_loss': unrealized_gain_loss,
            'realized_gain_loss': realized_gain_loss,
            'position_count': len(portfolio)
        }
        
        return await self.performance_repo.record_daily_performance(
            member_id, date, performance_data
        )
    
    async def rebalance_portfolio_allocations(self, member_id: int) -> bool:
        """Recalculate portfolio allocations and percentages."""
        portfolio = await self.portfolio_repo.get_member_portfolio(member_id)
        
        if not portfolio:
            return True
        
        # Calculate total portfolio value
        total_value = sum(pos.cost_basis for pos in portfolio)
        
        if total_value == 0:
            return True
        
        # Update position percentages (would need to update in database)
        for position in portfolio:
            percentage = (position.cost_basis / total_value) * 100
            # Would update position.position_size_percent here
        
        logger.info(f"Rebalanced portfolio allocations for member {member_id}")
        return True
    
    async def generate_portfolio_report(self, member_id: int, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """Generate comprehensive portfolio report."""
        if not as_of_date:
            as_of_date = date.today()
        
        # Get portfolio and performance data
        portfolio = await self.portfolio_repo.get_member_portfolio(member_id)
        latest_performance = await self.performance_repo.get_latest_performance(member_id)
        
        report = {
            'member_id': member_id,
            'as_of_date': as_of_date,
            'portfolio_summary': {
                'position_count': len(portfolio),
                'total_value': sum(pos.cost_basis for pos in portfolio),
                'total_cost_basis': sum(pos.cost_basis for pos in portfolio),
                'unrealized_gain_loss': sum(pos.unrealized_gain_loss or 0 for pos in portfolio),
                'realized_gain_loss': sum(pos.realized_gain_loss or 0 for pos in portfolio)
            },
            'top_positions': portfolio[:10],
            'sector_allocation': await self.portfolio_repo.get_sector_allocation(member_id),
            'performance_metrics': latest_performance.dict() if latest_performance else None
        }
        
        return report
    
    async def compare_portfolio_performance(self, member_id: int, benchmark: str, period_days: int) -> MarketPerformanceComparison:
        """Compare portfolio performance to benchmark."""
        # This would calculate actual performance comparison
        # For now, return a mock comparison
        
        return MarketPerformanceComparison(
            period_days=period_days,
            portfolio_return=Decimal('5.2'),
            benchmark_return=Decimal('4.8'),
            alpha=Decimal('0.4'),
            beta=Decimal('1.1'),
            outperformed=True
        )
    
    async def calculate_risk_metrics(self, member_id: int) -> Dict[str, Decimal]:
        """Calculate portfolio risk metrics."""
        # This would calculate actual risk metrics
        # For now, return mock metrics
        
        return {
            'volatility': Decimal('15.2'),
            'sharpe_ratio': Decimal('1.3'),
            'max_drawdown': Decimal('-8.5'),
            'beta': Decimal('1.1'),
            'var_95': Decimal('-2.1')
        }


# Log service creation
logger.info("Congressional domain services initialized")

# Export all services
__all__ = [
    "CongressMemberService",
    "CongressionalTradeService",
    "PortfolioService"
] 