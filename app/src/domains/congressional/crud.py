"""
Congressional domain CRUD operations.

This module contains repository implementations for congressional domain
data access operations. Supports CAP-10 (Transaction List) and CAP-11 (Member Profiles).
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, or_, desc, asc, func, text, select
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from domains.base.crud import CRUDBase
from domains.congressional.interfaces import (
    CongressMemberRepositoryInterface, CongressionalTradeRepositoryInterface,
    MemberPortfolioRepositoryInterface, PortfolioPerformanceRepositoryInterface
)
from domains.congressional.models import (
    CongressMember, CongressionalTrade, MemberPortfolio, MemberPortfolioPerformance
)
from domains.congressional.schemas import (
    CongressMemberCreate, CongressMemberUpdate, CongressMemberDetail, CongressMemberSummary,
    CongressionalTradeCreate, CongressionalTradeUpdate, CongressionalTradeDetail, CongressionalTradeSummary,
    CongressionalTradeQuery, MemberQuery, CongressionalTradeFilter,
    MemberPortfolioSummary, PortfolioPerformanceSummary,
    TradingStatistics, SortOrder, MarketPerformanceComparison
)
from core.exceptions import NotFoundError, ValidationError
from core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# CONGRESS MEMBER REPOSITORY
# ============================================================================

class CongressMemberRepository(CRUDBase[CongressMember, CongressMemberCreate, CongressMemberUpdate], CongressMemberRepositoryInterface):
    """Repository for congress member operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(CongressMember, db)
        self.db = db
    
    async def create(self, member_data: CongressMemberCreate) -> CongressMemberDetail:
        """Create a new congress member."""
        try:
            db_member = CongressMember(**member_data.dict())
            self.db.add(db_member)
            await self.db.commit()
            await self.db.refresh(db_member)
            
            logger.info(f"Created congress member: {db_member.full_name} ({db_member.id})")
            return CongressMemberDetail.from_orm(db_member)
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create congress member: {e}")
            raise ValidationError(f"Member with this bioguide_id already exists")
    
    async def get_by_id(self, member_id: UUID) -> Optional[CongressMemberDetail]:
        """Get congress member by ID."""
        stmt = select(CongressMember).where(CongressMember.id == member_id)
        result = await self.db.execute(stmt)
        db_member = result.scalar_one_or_none()
        if db_member:
            return CongressMemberDetail.from_orm(db_member)
        return None
    
    async def get_by_bioguide_id(self, bioguide_id: str) -> Optional[CongressMemberDetail]:
        """Get congress member by bioguide ID."""
        stmt = select(CongressMember).where(CongressMember.bioguide_id == bioguide_id)
        result = await self.db.execute(stmt)
        db_member = result.scalar_one_or_none()
        if db_member:
            return CongressMemberDetail.from_orm(db_member)
        return None
    
    async def get_by_congress_gov_id(self, congress_gov_id: str) -> Optional[CongressMemberDetail]:
        """Get congress member by congress.gov ID."""
        stmt = select(CongressMember).where(CongressMember.congress_gov_id == congress_gov_id)
        result = await self.db.execute(stmt)
        db_member = result.scalar_one_or_none()
        if db_member:
            return CongressMemberDetail.from_orm(db_member)
        return None
    
    async def get_by_name(self, last_name: str, first_name: str = "") -> Optional[CongressMemberDetail]:
        """Get congress member by last name and first name."""
        # Try to find by last name and first name combination
        if first_name:
            stmt = select(CongressMember).where(
                and_(
                    CongressMember.last_name == last_name,
                    CongressMember.first_name == first_name
                )
            )
        else:
            # If no first name, try to find by last name only
            stmt = select(CongressMember).where(CongressMember.last_name == last_name)
        
        result = await self.db.execute(stmt)
        db_member = result.scalar_one_or_none()
        
        if db_member:
            return CongressMemberDetail.from_orm(db_member)
        return None
    
    async def update(self, member_id: UUID, update_data: CongressMemberUpdate) -> Optional[CongressMemberDetail]:
        """Update congress member."""
        stmt = select(CongressMember).where(CongressMember.id == member_id)
        result = await self.db.execute(stmt)
        db_member = result.scalar_one_or_none()
        if not db_member:
            raise NotFoundError(f"Congress member {member_id} not found")
        
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_member, key, value)
        
        await self.db.commit()
        await self.db.refresh(db_member)
        
        logger.info(f"Updated congress member: {db_member.full_name} ({db_member.id})")
        return CongressMemberDetail.from_orm(db_member)
    
    async def list_members(self, query: MemberQuery) -> Tuple[List[CongressMemberSummary], int]:
        """List congress members with pagination and filtering."""
        # Build base query
        stmt = select(CongressMember)
        
        # Apply filters
        if query.parties:
            stmt = stmt.where(CongressMember.party.in_([p.value for p in query.parties]))
        
        if query.chambers:
            stmt = stmt.where(CongressMember.chamber.in_([c.value for c in query.chambers]))
        
        if query.states:
            stmt = stmt.where(CongressMember.state.in_(query.states))
        
        if query.congress_numbers:
            stmt = stmt.where(CongressMember.congress_number.in_(query.congress_numbers))
        
        if query.search:
            search_term = f"%{query.search}%"
            stmt = stmt.where(
                or_(
                    CongressMember.full_name.ilike(search_term),
                    CongressMember.first_name.ilike(search_term),
                    CongressMember.last_name.ilike(search_term)
                )
            )
        
        # Count total results
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Apply sorting
        sort_column = getattr(CongressMember, query.sort_by, CongressMember.last_name)
        if query.sort_order == SortOrder.DESC:
            stmt = stmt.order_by(desc(sort_column))
        else:
            stmt = stmt.order_by(asc(sort_column))
        
        # Apply pagination
        offset = (query.page - 1) * query.limit
        stmt = stmt.offset(offset).limit(query.limit)
        
        # Execute query
        result = await self.db.execute(stmt)
        db_members = result.scalars().all()
        
        # Convert to schemas
        members = []
        for db_member in db_members:
            member_dict = CongressMemberSummary.from_orm(db_member).dict()
            
            # Add computed fields if requested
            if query.include_trade_stats:
                # Note: These would need to be implemented as async methods
                # For now, skip to prevent errors
                member_dict['trade_count'] = 0  # db_member.get_trade_count()
                member_dict['total_trade_value'] = 0  # db_member.get_total_trade_value()
            
            members.append(CongressMemberSummary(**member_dict))
        
        return members, total_count
    
    async def search_members(self, search_term: str, limit: int = 10) -> List[CongressMemberSummary]:
        """Search congress members by name."""
        search_pattern = f"%{search_term}%"
        stmt = (
            select(CongressMember)
            .where(
                or_(
                    CongressMember.full_name.ilike(search_pattern),
                    CongressMember.first_name.ilike(search_pattern),
                    CongressMember.last_name.ilike(search_pattern)
                )
            )
            .order_by(CongressMember.last_name)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        db_members = result.scalars().all()
        
        return [CongressMemberSummary.from_orm(member) for member in db_members]
    
    def get_members_by_state(self, state: str) -> List[CongressMemberSummary]:
        """Get all members from a specific state."""
        db_members = (
            self.db.query(CongressMember)
            .filter(CongressMember.state == state.upper())
            .order_by(CongressMember.chamber, CongressMember.district, CongressMember.last_name)
            .all()
        )
        
        return [CongressMemberSummary.from_orm(member) for member in db_members]
    
    def get_active_members(self) -> List[CongressMemberSummary]:
        """Get all currently active members."""
        current_date = date.today()
        db_members = (
            self.db.query(CongressMember)
            .filter(
                and_(
                    CongressMember.term_start <= current_date,
                    CongressMember.term_end >= current_date
                )
            )
            .order_by(CongressMember.chamber, CongressMember.state, CongressMember.last_name)
            .all()
        )
        
        return [CongressMemberSummary.from_orm(member) for member in db_members]
    
    def get_trading_statistics(self, member_id: int) -> TradingStatistics:
        """Get trading statistics for a member."""
        # Query trade statistics
        trade_stats = (
            self.db.query(
                func.count(CongressionalTrade.id).label('total_trades'),
                func.sum(
                    func.coalesce(
                        CongressionalTrade.amount_exact,
                        (CongressionalTrade.amount_min + CongressionalTrade.amount_max) / 2
                    )
                ).label('total_value'),
                func.count(func.nullif(CongressionalTrade.transaction_type != 'P', True)).label('purchase_count'),
                func.count(func.nullif(CongressionalTrade.transaction_type != 'S', True)).label('sale_count'),
                func.avg(
                    CongressionalTrade.notification_date - CongressionalTrade.transaction_date
                ).label('avg_days_to_disclosure')
            )
            .filter(CongressionalTrade.member_id == member_id)
            .first()
        )
        
        # Get most traded assets
        most_traded = (
            self.db.query(
                CongressionalTrade.ticker,
                CongressionalTrade.asset_name,
                func.count(CongressionalTrade.id).label('trade_count'),
                func.sum(
                    func.coalesce(
                        CongressionalTrade.amount_exact,
                        (CongressionalTrade.amount_min + CongressionalTrade.amount_max) / 2
                    )
                ).label('total_value')
            )
            .filter(
                and_(
                    CongressionalTrade.member_id == member_id,
                    CongressionalTrade.ticker.isnot(None)
                )
            )
            .group_by(CongressionalTrade.ticker, CongressionalTrade.asset_name)
            .order_by(desc('trade_count'))
            .limit(10)
            .all()
        )
        
        most_traded_assets = [
            {
                'ticker': row.ticker,
                'asset_name': row.asset_name,
                'trade_count': row.trade_count,
                'total_value': int(row.total_value or 0)
            }
            for row in most_traded
        ]
        
        return TradingStatistics(
            total_trades=trade_stats.total_trades or 0,
            total_value=int(trade_stats.total_value or 0),
            purchase_count=trade_stats.purchase_count or 0,
            sale_count=trade_stats.sale_count or 0,
            avg_trade_size=int(trade_stats.total_value / trade_stats.total_trades) if trade_stats.total_trades else None,
            avg_days_to_disclosure=float(trade_stats.avg_days_to_disclosure.days) if trade_stats.avg_days_to_disclosure else None,
            most_traded_assets=most_traded_assets
        )


# ============================================================================
# CONGRESSIONAL TRADE REPOSITORY
# ============================================================================

class CongressionalTradeRepository(CRUDBase[CongressionalTrade, CongressionalTradeCreate, CongressionalTradeUpdate], CongressionalTradeRepositoryInterface):
    """Repository for congressional trade operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(CongressionalTrade, db)
        self.db = db
    
    def create(self, trade_data: CongressionalTradeCreate) -> CongressionalTradeDetail:
        """Create a new congressional trade."""
        try:
            db_trade = CongressionalTrade(**trade_data.dict())
            self.db.add(db_trade)
            self.db.commit()
            self.db.refresh(db_trade)
            
            logger.info(f"Created congressional trade: {db_trade.id} for member {db_trade.member_id}")
            return CongressionalTradeDetail.from_orm(db_trade)
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create congressional trade: {e}")
            raise ValidationError(f"Trade creation failed: {e}")
    
    def get_by_id(self, trade_id: int) -> Optional[CongressionalTradeDetail]:
        """Get congressional trade by ID."""
        db_trade = (
            self.db.query(CongressionalTrade)
            .options(joinedload(CongressionalTrade.member))
            .filter(CongressionalTrade.id == trade_id)
            .first()
        )
        
        if db_trade:
            return CongressionalTradeDetail.from_orm(db_trade)
        return None
    
    def update(self, trade_id: int, update_data: CongressionalTradeUpdate) -> Optional[CongressionalTradeDetail]:
        """Update congressional trade."""
        db_trade = self.db.query(CongressionalTrade).filter(CongressionalTrade.id == trade_id).first()
        if not db_trade:
            raise NotFoundError(f"Congressional trade {trade_id} not found")
        
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_trade, key, value)
        
        self.db.commit()
        self.db.refresh(db_trade)
        
        logger.info(f"Updated congressional trade: {trade_id}")
        return CongressionalTradeDetail.from_orm(db_trade)
    
    def list_trades(self, query: CongressionalTradeQuery) -> Tuple[List[CongressionalTradeSummary], int]:
        """List congressional trades with pagination and filtering."""
        db_query = (
            self.db.query(CongressionalTrade)
            .join(CongressMember, CongressionalTrade.member_id == CongressMember.id)
        )
        
        # Apply filters
        if query.member_ids:
            db_query = db_query.filter(CongressionalTrade.member_id.in_(query.member_ids))
        
        if query.member_names:
            name_filters = [CongressMember.full_name.ilike(f"%{name}%") for name in query.member_names]
            db_query = db_query.filter(or_(*name_filters))
        
        if query.parties:
            db_query = db_query.filter(CongressMember.party.in_([p.value for p in query.parties]))
        
        if query.chambers:
            db_query = db_query.filter(CongressMember.chamber.in_([c.value for c in query.chambers]))
        
        if query.states:
            db_query = db_query.filter(CongressMember.state.in_(query.states))
        
        if query.tickers:
            db_query = db_query.filter(CongressionalTrade.ticker.in_(query.tickers))
        
        if query.asset_types:
            db_query = db_query.filter(CongressionalTrade.asset_type.in_(query.asset_types))
        
        if query.transaction_types:
            db_query = db_query.filter(CongressionalTrade.transaction_type.in_([t.value for t in query.transaction_types]))
        
        if query.owners:
            db_query = db_query.filter(CongressionalTrade.owner.in_([o.value for o in query.owners]))
        
        # Date filters
        if query.transaction_date_from:
            db_query = db_query.filter(CongressionalTrade.transaction_date >= query.transaction_date_from)
        
        if query.transaction_date_to:
            db_query = db_query.filter(CongressionalTrade.transaction_date <= query.transaction_date_to)
        
        if query.notification_date_from:
            db_query = db_query.filter(CongressionalTrade.notification_date >= query.notification_date_from)
        
        if query.notification_date_to:
            db_query = db_query.filter(CongressionalTrade.notification_date <= query.notification_date_to)
        
        # Amount filters
        if query.amount_min or query.amount_max:
            estimated_value = func.coalesce(
                CongressionalTrade.amount_exact,
                (CongressionalTrade.amount_min + CongressionalTrade.amount_max) / 2
            )
            if query.amount_min:
                db_query = db_query.filter(estimated_value >= query.amount_min)
            if query.amount_max:
                db_query = db_query.filter(estimated_value <= query.amount_max)
        
        # Search filter
        if query.search:
            search_term = f"%{query.search}%"
            db_query = db_query.filter(
                or_(
                    CongressionalTrade.raw_asset_description.ilike(search_term),
                    CongressionalTrade.asset_name.ilike(search_term),
                    CongressionalTrade.ticker.ilike(search_term),
                    CongressMember.full_name.ilike(search_term)
                )
            )
        
        # Count total results
        total_count = db_query.count()
        
        # Apply sorting
        sort_map = {
            'transaction_date': CongressionalTrade.transaction_date,
            'notification_date': CongressionalTrade.notification_date,
            'member_name': CongressMember.full_name,
            'ticker': CongressionalTrade.ticker,
            'transaction_type': CongressionalTrade.transaction_type,
            'amount': func.coalesce(
                CongressionalTrade.amount_exact,
                (CongressionalTrade.amount_min + CongressionalTrade.amount_max) / 2
            )
        }
        
        sort_column = sort_map.get(query.sort_by.value, CongressionalTrade.transaction_date)
        if query.sort_order == SortOrder.DESC:
            db_query = db_query.order_by(desc(sort_column))
        else:
            db_query = db_query.order_by(asc(sort_column))
        
        # Apply pagination
        offset = (query.page - 1) * query.limit
        db_trades = db_query.offset(offset).limit(query.limit).all()
        
        # Convert to schemas
        trades = []
        for db_trade in db_trades:
            trade_dict = CongressionalTradeSummary.from_orm(db_trade).dict()

            # Defensive: handle missing member
            member = db_trade.member
            trade_dict['member_name'] = member.full_name if member else 'Unknown'
            trade_dict['member_party'] = member.party if member else None
            trade_dict['member_chamber'] = member.chamber if member else None
            trade_dict['member_state'] = member.state if member else None

            # Add estimated value
            trade_dict['estimated_value'] = db_trade.estimated_value

            trades.append(CongressionalTradeSummary(**trade_dict))

        return trades, total_count
    
    def get_member_trades(self, member_id: int, limit: Optional[int] = None) -> List[CongressionalTradeSummary]:
        """Get all trades for a specific member."""
        db_query = (
            self.db.query(CongressionalTrade)
            .filter(CongressionalTrade.member_id == member_id)
            .order_by(desc(CongressionalTrade.transaction_date))
        )
        
        if limit:
            db_query = db_query.limit(limit)
        
        db_trades = db_query.all()
        return [CongressionalTradeSummary.from_orm(trade) for trade in db_trades]
    
    def get_trades_by_ticker(self, ticker: str, limit: Optional[int] = None) -> List[CongressionalTradeSummary]:
        """Get all trades for a specific ticker."""
        db_query = (
            self.db.query(CongressionalTrade)
            .filter(CongressionalTrade.ticker == ticker.upper())
            .order_by(desc(CongressionalTrade.transaction_date))
        )
        
        if limit:
            db_query = db_query.limit(limit)
        
        db_trades = db_query.all()
        return [CongressionalTradeSummary.from_orm(trade) for trade in db_trades]
    
    def get_trades_by_date_range(self, start_date: date, end_date: date) -> List[CongressionalTradeSummary]:
        """Get trades within a date range."""
        db_trades = (
            self.db.query(CongressionalTrade)
            .filter(
                and_(
                    CongressionalTrade.transaction_date >= start_date,
                    CongressionalTrade.transaction_date <= end_date
                )
            )
            .order_by(desc(CongressionalTrade.transaction_date))
            .all()
        )
        
        return [CongressionalTradeSummary.from_orm(trade) for trade in db_trades]
    
    def get_recent_trades(self, days: int = 30, limit: int = 100) -> List[CongressionalTradeSummary]:
        """Get recent trades within specified days."""
        cutoff_date = date.today() - timedelta(days=days)
        
        db_trades = (
            self.db.query(CongressionalTrade)
            .filter(CongressionalTrade.transaction_date >= cutoff_date)
            .order_by(desc(CongressionalTrade.transaction_date))
            .limit(limit)
            .all()
        )
        
        return [CongressionalTradeSummary.from_orm(trade) for trade in db_trades]
    
    def get_large_trades(self, min_amount: int, limit: int = 100) -> List[CongressionalTradeSummary]:
        """Get trades above a minimum amount threshold."""
        estimated_value = func.coalesce(
            CongressionalTrade.amount_exact,
            (CongressionalTrade.amount_min + CongressionalTrade.amount_max) / 2
        )
        
        db_trades = (
            self.db.query(CongressionalTrade)
            .filter(estimated_value >= min_amount)
            .order_by(desc(estimated_value))
            .limit(limit)
            .all()
        )
        
        return [CongressionalTradeSummary.from_orm(trade) for trade in db_trades]
    
    def bulk_create(self, trades_data: List[CongressionalTradeCreate]) -> List[CongressionalTradeDetail]:
        """Bulk create congressional trades."""
        try:
            db_trades = [CongressionalTrade(**trade_data.dict()) for trade_data in trades_data]
            self.db.add_all(db_trades)
            self.db.commit()
            
            for db_trade in db_trades:
                self.db.refresh(db_trade)
            
            logger.info(f"Bulk created {len(db_trades)} congressional trades")
            return [CongressionalTradeDetail.from_orm(trade) for trade in db_trades]
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to bulk create congressional trades: {e}")
            raise ValidationError(f"Bulk trade creation failed: {e}")
    
    def update_price_performance(self, trade_id: int, price_changes: Dict[str, Decimal]) -> bool:
        """Update price performance data for a trade."""
        db_trade = self.db.query(CongressionalTrade).filter(CongressionalTrade.id == trade_id).first()
        if not db_trade:
            return False
        
        if '1d' in price_changes:
            db_trade.price_change_1d = price_changes['1d']
        if '7d' in price_changes:
            db_trade.price_change_7d = price_changes['7d']
        if '30d' in price_changes:
            db_trade.price_change_30d = price_changes['30d']
        
        self.db.commit()
        return True


# ============================================================================
# PORTFOLIO REPOSITORIES
# ============================================================================

class MemberPortfolioRepository(CRUDBase[MemberPortfolio, dict, dict], MemberPortfolioRepositoryInterface):
    """Repository for member portfolio operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(MemberPortfolio, db)
        self.db = db
    
    def get_member_portfolio(self, member_id: int) -> List[MemberPortfolioSummary]:
        """Get current portfolio for a member."""
        db_positions = (
            self.db.query(MemberPortfolio)
            .filter(
                and_(
                    MemberPortfolio.member_id == member_id,
                    MemberPortfolio.shares > 0
                )
            )
            .order_by(desc(MemberPortfolio.cost_basis))
            .all()
        )
        
        return [MemberPortfolioSummary.from_orm(position) for position in db_positions]
    
    def get_member_position(self, member_id: int, security_id: int) -> Optional[MemberPortfolioSummary]:
        """Get specific position for a member."""
        db_position = (
            self.db.query(MemberPortfolio)
            .filter(
                and_(
                    MemberPortfolio.member_id == member_id,
                    MemberPortfolio.security_id == security_id
                )
            )
            .first()
        )
        
        if db_position:
            return MemberPortfolioSummary.from_orm(db_position)
        return None
    
    def update_position(self, member_id: int, security_id: int, transaction_data: Dict[str, Any]) -> MemberPortfolioSummary:
        """Update portfolio position based on a trade."""
        # Get or create position
        db_position = (
            self.db.query(MemberPortfolio)
            .filter(
                and_(
                    MemberPortfolio.member_id == member_id,
                    MemberPortfolio.security_id == security_id
                )
            )
            .first()
        )
        
        if not db_position:
            db_position = MemberPortfolio(
                member_id=member_id,
                security_id=security_id,
                shares=Decimal('0'),
                cost_basis=0
            )
            self.db.add(db_position)
        
        # Update position based on transaction
        db_position.update_position(
            transaction_type=transaction_data['transaction_type'],
            shares=transaction_data['shares'],
            price_per_share=transaction_data['price_per_share'],
            transaction_date=transaction_data['transaction_date']
        )
        
        self.db.commit()
        self.db.refresh(db_position)
        
        return MemberPortfolioSummary.from_orm(db_position)
    
    def calculate_portfolio_value(self, member_id: int) -> int:
        """Calculate total portfolio value for a member."""
        # This would require current prices from securities domain
        # For now, return sum of cost basis
        result = (
            self.db.query(func.sum(MemberPortfolio.cost_basis))
            .filter(
                and_(
                    MemberPortfolio.member_id == member_id,
                    MemberPortfolio.shares > 0
                )
            )
            .scalar()
        )
        
        return int(result or 0)
    
    def get_top_positions(self, member_id: int, limit: int = 10) -> List[MemberPortfolioSummary]:
        """Get top positions by value for a member."""
        db_positions = (
            self.db.query(MemberPortfolio)
            .filter(
                and_(
                    MemberPortfolio.member_id == member_id,
                    MemberPortfolio.shares > 0
                )
            )
            .order_by(desc(MemberPortfolio.cost_basis))
            .limit(limit)
            .all()
        )
        
        return [MemberPortfolioSummary.from_orm(position) for position in db_positions]
    
    def get_sector_allocation(self, member_id: int) -> Dict[str, Decimal]:
        """Get sector allocation for a member's portfolio."""
        # This would require sector information from securities domain
        # Return empty dict for now
        return {}


class MemberPortfolioPerformanceRepository(CRUDBase[MemberPortfolioPerformance, dict, dict], PortfolioPerformanceRepositoryInterface):
    """Repository for member portfolio performance data."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(MemberPortfolioPerformance, db)
    
    def record_daily_performance(self, member_id: int, date: date, performance_data: Dict[str, Any]) -> PortfolioPerformanceSummary:
        """Record daily performance for a member."""
        # Check if performance already exists for this date
        existing = (
            self.db.query(MemberPortfolioPerformance)
            .filter(
                MemberPortfolioPerformance.member_id == member_id,
                MemberPortfolioPerformance.date == date
            )
            .first()
        )
        
        if existing:
            # Update existing record
            for key, value in performance_data.items():
                setattr(existing, key, value)
            self.db.commit()
            return PortfolioPerformanceSummary.from_orm(existing)
        
        # Create new performance record
        db_performance = MemberPortfolioPerformance(
            member_id=member_id,
            date=date,
            **performance_data
        )
        
        self.db.add(db_performance)
        self.db.commit()
        self.db.refresh(db_performance)
        
        return PortfolioPerformanceSummary.from_orm(db_performance)
    
    def get_performance_history(self, member_id: int, start_date: date, end_date: date) -> List[PortfolioPerformanceSummary]:
        """Get performance history for a member."""
        db_performance = (
            self.db.query(MemberPortfolioPerformance)
            .filter(
                MemberPortfolioPerformance.member_id == member_id,
                MemberPortfolioPerformance.date >= start_date,
                MemberPortfolioPerformance.date <= end_date
            )
            .order_by(MemberPortfolioPerformance.date)
            .all()
        )
        
        return [PortfolioPerformanceSummary.from_orm(perf) for perf in db_performance]
    
    def get_latest_performance(self, member_id: int) -> Optional[PortfolioPerformanceSummary]:
        """Get latest performance for a member."""
        db_performance = (
            self.db.query(MemberPortfolioPerformance)
            .filter(MemberPortfolioPerformance.member_id == member_id)
            .order_by(desc(MemberPortfolioPerformance.date))
            .first()
        )
        
        if not db_performance:
            return None
        
        return PortfolioPerformanceSummary.from_orm(db_performance)
    
    def calculate_returns(self, member_id: int, period_days: int) -> Optional[MarketPerformanceComparison]:
        """Calculate returns for a specific period."""
        # Implementation would calculate returns based on historical performance
        # Return None for now
        return None
    
    def get_risk_metrics(self, member_id: int, period_days: int = 252) -> Dict[str, Decimal]:
        """Calculate risk metrics for a member's portfolio."""
        # Implementation would calculate volatility, Sharpe ratio, etc.
        # Return empty dict for now
        return {}


# Log CRUD creation
logger.info("Congressional domain CRUD operations initialized")

# Create aliases for backward compatibility
CongressMemberCRUD = CongressMemberRepository
CongressionalTradeCRUD = CongressionalTradeRepository
MemberPortfolioCRUD = MemberPortfolioRepository
PortfolioPerformanceCRUD = MemberPortfolioPerformanceRepository

# Export all repositories
__all__ = [
    "CongressMemberRepository",
    "CongressionalTradeRepository", 
    "MemberPortfolioRepository",
    "MemberPortfolioPerformanceRepository",
    "CongressMemberCRUD",
    "CongressionalTradeCRUD",
    "MemberPortfolioCRUD", 
    "PortfolioPerformanceCRUD"
] 