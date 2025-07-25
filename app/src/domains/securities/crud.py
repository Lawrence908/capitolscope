"""
Securities domain CRUD operations.

This module implements database operations for securities, asset types, exchanges,
and price data. Extends the base CRUD functionality with domain-specific operations.
"""

from typing import Any, Dict, List, Optional, Type
from datetime import date, datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func, text

from domains.base.crud import CRUDBase
from domains.securities.models import (
    AssetType, Sector, Exchange, Security, DailyPrice, CorporateAction,
    PriceHistoryAggregate, SecurityWatchlist
)
from domains.securities.schemas import (
    AssetTypeCreate, AssetTypeUpdate,
    SectorCreate, SectorUpdate,
    ExchangeCreate, ExchangeUpdate,
    SecurityCreate, SecurityUpdate,
    DailyPriceCreate, DailyPriceUpdate,
    CorporateActionCreate, CorporateActionUpdate,
    SecurityWatchlistCreate, SecurityWatchlistUpdate
)
import logging
logger = logging.getLogger(__name__)


# ============================================================================
# ASSET TYPE CRUD
# ============================================================================

class AssetTypeCRUD(CRUDBase[AssetType, AssetTypeCreate, AssetTypeUpdate]):
    """CRUD operations for asset types."""
    
    def __init__(self, db: Session):
        super().__init__(AssetType, db)
    
    def get_by_code(self, code: str) -> Optional[AssetType]:
        """Get asset type by code."""
        try:
            return self.db.query(AssetType).filter(AssetType.code == code).first()
        except Exception as e:
            logger.error(f"Error getting asset type by code {code}: {e}")
            raise
    
    def get_active_types(self) -> List[AssetType]:
        """Get all active asset types."""
        try:
            return self.db.query(AssetType).filter(AssetType.is_active == True).all()
        except Exception as e:
            logger.error(f"Error getting active asset types: {e}")
            raise
    
    def get_by_category(self, category: str) -> List[AssetType]:
        """Get asset types by category."""
        try:
            return self.db.query(AssetType).filter(AssetType.category == category).all()
        except Exception as e:
            logger.error(f"Error getting asset types by category {category}: {e}")
            raise


# ============================================================================
# SECTOR CRUD
# ============================================================================

class SectorCRUD(CRUDBase[Sector, SectorCreate, SectorUpdate]):
    """CRUD operations for sectors."""
    
    def __init__(self, db: Session):
        super().__init__(Sector, db)
    
    def get_by_name(self, name: str) -> Optional[Sector]:
        """Get sector by name."""
        try:
            return self.db.query(Sector).filter(Sector.name == name).first()
        except Exception as e:
            logger.error(f"Error getting sector by name {name}: {e}")
            raise
    
    def get_by_gics_code(self, gics_code: str) -> Optional[Sector]:
        """Get sector by GICS code."""
        try:
            return self.db.query(Sector).filter(Sector.gics_code == gics_code).first()
        except Exception as e:
            logger.error(f"Error getting sector by GICS code {gics_code}: {e}")
            raise
    
    def get_top_level_sectors(self) -> List[Sector]:
        """Get top-level sectors (no parent)."""
        try:
            return self.db.query(Sector).filter(Sector.parent_sector_id.is_(None)).all()
        except Exception as e:
            logger.error(f"Error getting top-level sectors: {e}")
            raise
    
    def get_sub_sectors(self, parent_id: int) -> List[Sector]:
        """Get sub-sectors for a parent sector."""
        try:
            return self.db.query(Sector).filter(Sector.parent_sector_id == parent_id).all()
        except Exception as e:
            logger.error(f"Error getting sub-sectors for parent {parent_id}: {e}")
            raise


# ============================================================================
# EXCHANGE CRUD
# ============================================================================

class ExchangeCRUD(CRUDBase[Exchange, ExchangeCreate, ExchangeUpdate]):
    """CRUD operations for exchanges."""
    
    def __init__(self, db: Session):
        super().__init__(Exchange, db)
    
    def get_by_code(self, code: str) -> Optional[Exchange]:
        """Get exchange by code."""
        try:
            return self.db.query(Exchange).filter(Exchange.code == code).first()
        except Exception as e:
            logger.error(f"Error getting exchange by code {code}: {e}")
            raise
    
    def get_by_country(self, country: str) -> List[Exchange]:
        """Get exchanges by country."""
        try:
            return self.db.query(Exchange).filter(Exchange.country == country).all()
        except Exception as e:
            logger.error(f"Error getting exchanges by country {country}: {e}")
            raise
    
    def get_major_exchanges(self) -> List[Exchange]:
        """Get major exchanges (top 10 by market cap rank)."""
        try:
            return self.db.query(Exchange).filter(
                Exchange.market_cap_rank.isnot(None)
            ).order_by(Exchange.market_cap_rank).limit(10).all()
        except Exception as e:
            logger.error(f"Error getting major exchanges: {e}")
            raise


# ============================================================================
# SECURITY CRUD
# ============================================================================

class SecurityCRUD(CRUDBase[Security, SecurityCreate, SecurityUpdate]):
    """CRUD operations for securities."""
    
    def __init__(self, db: Session):
        super().__init__(Security, db)
    
    def get_by_ticker(self, ticker: str, exchange_id: Optional[int] = None) -> Optional[Security]:
        """Get security by ticker symbol."""
        try:
            query = self.db.query(Security).filter(Security.ticker == ticker.upper())
            
            if exchange_id:
                query = query.filter(Security.exchange_id == exchange_id)
            
            return query.first()
        except Exception as e:
            logger.error(f"Error getting security by ticker {ticker}: {e}")
            raise
    
    def get_by_identifiers(self, isin: str = None, cusip: str = None, figi: str = None) -> Optional[Security]:
        """Get security by various identifiers."""
        try:
            query = self.db.query(Security)
            
            if isin:
                query = query.filter(Security.isin == isin)
            elif cusip:
                query = query.filter(Security.cusip == cusip)
            elif figi:
                query = query.filter(Security.figi == figi)
            else:
                return None
            
            return query.first()
        except Exception as e:
            logger.error(f"Error getting security by identifiers: {e}")
            raise
    
    def search_securities(
        self, 
        query: str, 
        asset_type_ids: Optional[List[int]] = None,
        sector_ids: Optional[List[int]] = None,
        exchange_ids: Optional[List[int]] = None,
        limit: int = 50
    ) -> List[Security]:
        """Search securities by ticker or name."""
        try:
            search_query = self.db.query(Security).options(
                joinedload(Security.asset_type),
                joinedload(Security.sector),
                joinedload(Security.exchange)
            )
            
            # Text search
            if query:
                search_query = search_query.filter(
                    or_(
                        Security.ticker.ilike(f"%{query}%"),
                        Security.name.ilike(f"%{query}%")
                    )
                )
            
            # Filter by asset types
            if asset_type_ids:
                search_query = search_query.filter(Security.asset_type_id.in_(asset_type_ids))
            
            # Filter by sectors
            if sector_ids:
                search_query = search_query.filter(Security.sector_id.in_(sector_ids))
            
            # Filter by exchanges
            if exchange_ids:
                search_query = search_query.filter(Security.exchange_id.in_(exchange_ids))
            
            # Only active securities
            search_query = search_query.filter(Security.is_active == True)
            
            # Order by relevance (exact ticker match first, then name)
            search_query = search_query.order_by(
                Security.ticker.ilike(f"{query}%").desc(),
                Security.name.ilike(f"{query}%").desc(),
                Security.ticker
            )
            
            results = search_query.limit(limit).all()
            logger.debug(f"Found {len(results)} securities for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching securities: {e}")
            raise
    
    def get_securities_by_market_cap(
        self, 
        min_market_cap: Optional[int] = None,
        max_market_cap: Optional[int] = None,
        limit: int = 100
    ) -> List[Security]:
        """Get securities by market cap range."""
        try:
            query = self.db.query(Security).filter(
                Security.market_cap.isnot(None),
                Security.is_active == True
            )
            
            if min_market_cap:
                query = query.filter(Security.market_cap >= min_market_cap)
            
            if max_market_cap:
                query = query.filter(Security.market_cap <= max_market_cap)
            
            return query.order_by(desc(Security.market_cap)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting securities by market cap: {e}")
            raise
    
    def get_trending_securities(self, limit: int = 20) -> List[Security]:
        """Get trending securities based on recent activity."""
        try:
            # This is a simplified version - in production, you'd want to factor in
            # trading volume, price changes, news mentions, etc.
            query = self.db.query(Security).filter(
                Security.is_active == True,
                Security.volume_avg_30d.isnot(None)
            ).order_by(desc(Security.volume_avg_30d)).limit(limit)
            
            return query.all()
        except Exception as e:
            logger.error(f"Error getting trending securities: {e}")
            raise


# ============================================================================
# DAILY PRICE CRUD
# ============================================================================

class DailyPriceCRUD(CRUDBase[DailyPrice, DailyPriceCreate, DailyPriceUpdate]):
    """CRUD operations for daily prices."""
    
    def __init__(self, db: Session):
        super().__init__(DailyPrice, db)
    
    def get_latest_price(self, security_id: int) -> Optional[DailyPrice]:
        """Get the latest price for a security."""
        try:
            return self.db.query(DailyPrice).filter(
                DailyPrice.security_id == security_id
            ).order_by(desc(DailyPrice.date)).first()
        except Exception as e:
            logger.error(f"Error getting latest price for security {security_id}: {e}")
            raise
    
    def get_price_history(
        self, 
        security_id: int, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365
    ) -> List[DailyPrice]:
        """Get price history for a security."""
        try:
            query = self.db.query(DailyPrice).filter(
                DailyPrice.security_id == security_id
            )
            
            if start_date:
                query = query.filter(DailyPrice.date >= start_date)
            
            if end_date:
                query = query.filter(DailyPrice.date <= end_date)
            
            return query.order_by(desc(DailyPrice.date)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting price history for security {security_id}: {e}")
            raise
    
    def get_price_on_date(self, security_id: int, target_date: date) -> Optional[DailyPrice]:
        """Get price for a security on a specific date."""
        try:
            return self.db.query(DailyPrice).filter(
                DailyPrice.security_id == security_id,
                DailyPrice.date == target_date
            ).first()
        except Exception as e:
            logger.error(f"Error getting price for security {security_id} on {target_date}: {e}")
            raise
    
    def bulk_upsert_prices(self, prices: List[DailyPriceCreate]) -> int:
        """Bulk upsert daily prices (insert or update on conflict)."""
        try:
            if not prices:
                return 0
            
            # Convert to dictionaries for bulk operations
            price_dicts = [price.dict() for price in prices]
            
            # Use PostgreSQL's ON CONFLICT DO UPDATE
            stmt = text("""
                INSERT INTO daily_prices (security_id, date, open_price, high_price, low_price, close_price, volume)
                VALUES (:security_id, :date, :open_price, :high_price, :low_price, :close_price, :volume)
                ON CONFLICT (security_id, date) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
                    updated_at = NOW()
            """)
            
            result = self.db.execute(stmt, price_dicts)
            self.db.commit()
            
            logger.info(f"Bulk upserted {len(prices)} daily prices")
            return result.rowcount
            
        except Exception as e:
            logger.error(f"Error bulk upserting prices: {e}")
            self.db.rollback()
            raise
    
    def calculate_price_changes(self, security_id: int, days: int = 30) -> Dict[str, float]:
        """Calculate price changes for a security over different periods."""
        try:
            prices = self.get_price_history(security_id, limit=days + 1)
            
            if len(prices) < 2:
                return {}
            
            latest_price = prices[0].close_price
            changes = {}
            
            # Calculate changes for different periods
            periods = [1, 7, 30]
            for period in periods:
                if len(prices) > period:
                    old_price = prices[period].close_price
                    if old_price > 0:
                        change_percent = ((latest_price - old_price) / old_price) * 100
                        changes[f"{period}d"] = change_percent
            
            return changes
            
        except Exception as e:
            logger.error(f"Error calculating price changes for security {security_id}: {e}")
            raise


# ============================================================================
# CORPORATE ACTION CRUD
# ============================================================================

class CorporateActionCRUD(CRUDBase[CorporateAction, CorporateActionCreate, CorporateActionUpdate]):
    """CRUD operations for corporate actions."""
    
    def __init__(self, db: Session):
        super().__init__(CorporateAction, db)
    
    def get_by_security(self, security_id: int, limit: int = 100) -> List[CorporateAction]:
        """Get corporate actions for a security."""
        try:
            return self.db.query(CorporateAction).filter(
                CorporateAction.security_id == security_id
            ).order_by(desc(CorporateAction.ex_date)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting corporate actions for security {security_id}: {e}")
            raise
    
    def get_by_date_range(
        self, 
        start_date: date, 
        end_date: date,
        action_type: Optional[str] = None
    ) -> List[CorporateAction]:
        """Get corporate actions within a date range."""
        try:
            query = self.db.query(CorporateAction).filter(
                CorporateAction.ex_date >= start_date,
                CorporateAction.ex_date <= end_date
            )
            
            if action_type:
                query = query.filter(CorporateAction.action_type == action_type)
            
            return query.order_by(desc(CorporateAction.ex_date)).all()
        except Exception as e:
            logger.error(f"Error getting corporate actions by date range: {e}")
            raise
    
    def get_upcoming_actions(self, days_ahead: int = 30) -> List[CorporateAction]:
        """Get upcoming corporate actions."""
        try:
            future_date = datetime.now().date()
            end_date = future_date + datetime.timedelta(days=days_ahead)
            
            return self.db.query(CorporateAction).filter(
                CorporateAction.ex_date > future_date,
                CorporateAction.ex_date <= end_date
            ).order_by(CorporateAction.ex_date).all()
        except Exception as e:
            logger.error(f"Error getting upcoming corporate actions: {e}")
            raise


# ============================================================================
# SECURITY WATCHLIST CRUD
# ============================================================================

class SecurityWatchlistCRUD(CRUDBase[SecurityWatchlist, SecurityWatchlistCreate, SecurityWatchlistUpdate]):
    """CRUD operations for security watchlists."""
    
    def __init__(self, db: Session):
        super().__init__(SecurityWatchlist, db)
    
    def get_user_watchlist(self, user_id: str) -> List[SecurityWatchlist]:
        """Get watchlist for a user."""
        try:
            return self.db.query(SecurityWatchlist).options(
                joinedload(SecurityWatchlist.security)
            ).filter(SecurityWatchlist.user_id == user_id).all()
        except Exception as e:
            logger.error(f"Error getting watchlist for user {user_id}: {e}")
            raise
    
    def add_to_watchlist(self, user_id: str, security_id: int) -> SecurityWatchlist:
        """Add security to user's watchlist."""
        try:
            # Check if already exists
            existing = self.db.query(SecurityWatchlist).filter(
                SecurityWatchlist.user_id == user_id,
                SecurityWatchlist.security_id == security_id
            ).first()
            
            if existing:
                return existing
            
            # Create new watchlist entry
            watchlist_item = SecurityWatchlist(
                user_id=user_id,
                security_id=security_id
            )
            
            self.db.add(watchlist_item)
            self.db.commit()
            self.db.refresh(watchlist_item)
            
            logger.info(f"Added security {security_id} to user {user_id} watchlist")
            return watchlist_item
            
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
            self.db.rollback()
            raise
    
    def remove_from_watchlist(self, user_id: str, security_id: int) -> bool:
        """Remove security from user's watchlist."""
        try:
            watchlist_item = self.db.query(SecurityWatchlist).filter(
                SecurityWatchlist.user_id == user_id,
                SecurityWatchlist.security_id == security_id
            ).first()
            
            if watchlist_item:
                self.db.delete(watchlist_item)
                self.db.commit()
                logger.info(f"Removed security {security_id} from user {user_id} watchlist")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error removing from watchlist: {e}")
            self.db.rollback()
            raise


# Create CRUD instances
def get_asset_type_crud(db: Session) -> AssetTypeCRUD:
    return AssetTypeCRUD(db)

def get_sector_crud(db: Session) -> SectorCRUD:
    return SectorCRUD(db)

def get_exchange_crud(db: Session) -> ExchangeCRUD:
    return ExchangeCRUD(db)

def get_security_crud(db: Session) -> SecurityCRUD:
    return SecurityCRUD(db)

def get_daily_price_crud(db: Session) -> DailyPriceCRUD:
    return DailyPriceCRUD(db)

def get_corporate_action_crud(db: Session) -> CorporateActionCRUD:
    return CorporateActionCRUD(db)

def get_security_watchlist_crud(db: Session) -> SecurityWatchlistCRUD:
    return SecurityWatchlistCRUD(db)


# Export all CRUD classes
__all__ = [
    "AssetTypeCRUD",
    "SectorCRUD", 
    "ExchangeCRUD",
    "SecurityCRUD",
    "DailyPriceCRUD",
    "CorporateActionCRUD",
    "SecurityWatchlistCRUD",
    "get_asset_type_crud",
    "get_sector_crud",
    "get_exchange_crud",
    "get_security_crud",
    "get_daily_price_crud",
    "get_corporate_action_crud",
    "get_security_watchlist_crud"
] 