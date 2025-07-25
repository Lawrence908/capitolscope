"""
Securities domain services.

This module implements business logic for securities, asset types, exchanges,
and price data. Supports CAP-24 (Stock Database) and CAP-25 (Price Data Ingestion).
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from domains.base.services import ServiceBase
from domains.securities.crud import (
    AssetTypeCRUD, SectorCRUD, ExchangeCRUD, SecurityCRUD, 
    DailyPriceCRUD, CorporateActionCRUD, SecurityWatchlistCRUD
)
from domains.securities.models import (
    AssetType, Sector, Exchange, Security, DailyPrice, CorporateAction, SecurityWatchlist
)
from domains.securities.schemas import (
    AssetTypeCreate, AssetTypeUpdate, AssetTypeResponse,
    SectorCreate, SectorUpdate, SectorResponse,
    ExchangeCreate, ExchangeUpdate, ExchangeResponse,
    SecurityCreate, SecurityUpdate, SecurityResponse, SecuritySummary,
    DailyPriceCreate, DailyPriceUpdate, DailyPriceResponse, PriceHistory,
    CorporateActionCreate, CorporateActionUpdate, CorporateActionResponse,
    SecurityWatchlistCreate, SecurityWatchlistUpdate, SecurityWatchlistResponse,
    SecuritySearchParams, PriceSearchParams, BulkPriceCreate, BulkOperationResponse
)
from domains.base.interfaces import DataIngestionInterface
import logging
logger = logging.getLogger(__name__)


# ============================================================================
# ASSET TYPE SERVICE
# ============================================================================

class AssetTypeService(ServiceBase[AssetType, AssetTypeCreate, AssetTypeUpdate, AssetTypeResponse]):
    """Service for asset type operations."""
    
    def __init__(self, db: Session):
        self.crud = AssetTypeCRUD(db)
        super().__init__(self.crud, AssetTypeResponse)
    
    def get_by_code(self, code: str) -> Optional[AssetTypeResponse]:
        """Get asset type by code."""
        try:
            asset_type = self.crud.get_by_code(code)
            if asset_type:
                return AssetTypeResponse.model_validate(asset_type)
            return None
        except Exception as e:
            logger.error(f"Error getting asset type by code {code}: {e}")
            raise
    
    def get_active_types(self) -> List[AssetTypeResponse]:
        """Get all active asset types."""
        try:
            asset_types = self.crud.get_active_types()
            return [AssetTypeResponse.model_validate(at) for at in asset_types]
        except Exception as e:
            logger.error(f"Error getting active asset types: {e}")
            raise
    
    def get_by_category(self, category: str) -> List[AssetTypeResponse]:
        """Get asset types by category."""
        try:
            asset_types = self.crud.get_by_category(category)
            return [AssetTypeResponse.model_validate(at) for at in asset_types]
        except Exception as e:
            logger.error(f"Error getting asset types by category {category}: {e}")
            raise


# ============================================================================
# SECTOR SERVICE
# ============================================================================

class SectorService(ServiceBase[Sector, SectorCreate, SectorUpdate, SectorResponse]):
    """Service for sector operations."""
    
    def __init__(self, db: Session):
        self.crud = SectorCRUD(db)
        super().__init__(self.crud, SectorResponse)
    
    def get_by_name(self, name: str) -> Optional[SectorResponse]:
        """Get sector by name."""
        try:
            sector = self.crud.get_by_name(name)
            if sector:
                return SectorResponse.model_validate(sector)
            return None
        except Exception as e:
            logger.error(f"Error getting sector by name {name}: {e}")
            raise
    
    def get_by_gics_code(self, gics_code: str) -> Optional[SectorResponse]:
        """Get sector by GICS code."""
        try:
            sector = self.crud.get_by_gics_code(gics_code)
            if sector:
                return SectorResponse.model_validate(sector)
            return None
        except Exception as e:
            logger.error(f"Error getting sector by GICS code {gics_code}: {e}")
            raise
    
    def get_top_level_sectors(self) -> List[SectorResponse]:
        """Get top-level sectors."""
        try:
            sectors = self.crud.get_top_level_sectors()
            return [SectorResponse.model_validate(s) for s in sectors]
        except Exception as e:
            logger.error(f"Error getting top-level sectors: {e}")
            raise


# ============================================================================
# EXCHANGE SERVICE
# ============================================================================

class ExchangeService(ServiceBase[Exchange, ExchangeCreate, ExchangeUpdate, ExchangeResponse]):
    """Service for exchange operations."""
    
    def __init__(self, db: Session):
        self.crud = ExchangeCRUD(db)
        super().__init__(self.crud, ExchangeResponse)
    
    def get_by_code(self, code: str) -> Optional[ExchangeResponse]:
        """Get exchange by code."""
        try:
            exchange = self.crud.get_by_code(code)
            if exchange:
                return ExchangeResponse.model_validate(exchange)
            return None
        except Exception as e:
            logger.error(f"Error getting exchange by code {code}: {e}")
            raise
    
    def get_by_country(self, country: str) -> List[ExchangeResponse]:
        """Get exchanges by country."""
        try:
            exchanges = self.crud.get_by_country(country)
            return [ExchangeResponse.model_validate(e) for e in exchanges]
        except Exception as e:
            logger.error(f"Error getting exchanges by country {country}: {e}")
            raise
    
    def get_major_exchanges(self) -> List[ExchangeResponse]:
        """Get major exchanges."""
        try:
            exchanges = self.crud.get_major_exchanges()
            return [ExchangeResponse.model_validate(e) for e in exchanges]
        except Exception as e:
            logger.error(f"Error getting major exchanges: {e}")
            raise


# ============================================================================
# SECURITY SERVICE
# ============================================================================

class SecurityService(ServiceBase[Security, SecurityCreate, SecurityUpdate, SecurityResponse]):
    """Service for security operations."""
    
    def __init__(self, db: Session):
        self.crud = SecurityCRUD(db)
        self.price_crud = DailyPriceCRUD(db)
        super().__init__(self.crud, SecurityResponse)
    
    def get_by_ticker(self, ticker: str, exchange_id: Optional[int] = None) -> Optional[SecurityResponse]:
        """Get security by ticker symbol."""
        try:
            security = self.crud.get_by_ticker(ticker, exchange_id)
            if security:
                response = SecurityResponse.model_validate(security)
                
                # Enrich with current price data
                latest_price = self.price_crud.get_latest_price(security.id)
                if latest_price:
                    response.current_price = latest_price.close_price
                    response.price_change_24h = latest_price.price_change_percent
                
                return response
            return None
        except Exception as e:
            logger.error(f"Error getting security by ticker {ticker}: {e}")
            raise
    
    def search_securities(self, search_params: SecuritySearchParams) -> List[SecuritySummary]:
        """Search securities with filters."""
        try:
            securities = self.crud.search_securities(
                query=search_params.query,
                asset_type_ids=search_params.asset_type_ids,
                sector_ids=search_params.sector_ids,
                exchange_ids=search_params.exchange_ids,
                limit=50
            )
            
            # Convert to summary format with current prices
            summaries = []
            for security in securities:
                summary = SecuritySummary(
                    id=security.id,
                    ticker=security.ticker,
                    name=security.name,
                    market_cap=security.market_cap,
                    asset_type_name=security.asset_type.name if security.asset_type else None,
                    sector_name=security.sector.name if security.sector else None
                )
                
                # Add current price
                latest_price = self.price_crud.get_latest_price(security.id)
                if latest_price:
                    summary.current_price = latest_price.close_price
                    summary.price_change_24h = latest_price.price_change_percent
                
                summaries.append(summary)
            
            return summaries
        except Exception as e:
            logger.error(f"Error searching securities: {e}")
            raise
    
    def get_trending_securities(self, limit: int = 20) -> List[SecuritySummary]:
        """Get trending securities."""
        try:
            securities = self.crud.get_trending_securities(limit)
            return [SecuritySummary.model_validate(s) for s in securities]
        except Exception as e:
            logger.error(f"Error getting trending securities: {e}")
            raise
    
    def get_securities_by_market_cap(
        self, 
        min_market_cap: Optional[int] = None,
        max_market_cap: Optional[int] = None,
        limit: int = 100
    ) -> List[SecuritySummary]:
        """Get securities by market cap range."""
        try:
            securities = self.crud.get_securities_by_market_cap(
                min_market_cap, max_market_cap, limit
            )
            return [SecuritySummary.model_validate(s) for s in securities]
        except Exception as e:
            logger.error(f"Error getting securities by market cap: {e}")
            raise
    
    def _post_create(self, db_obj: Security, **kwargs) -> None:
        """Post-processing after creating a security."""
        logger.info(f"Created security: {db_obj.ticker} - {db_obj.name}")
        
        # Send notification for new security
        self._send_notification("security_created", {
            "security_id": db_obj.id,
            "ticker": db_obj.ticker,
            "name": db_obj.name
        })
    
    def _post_update(self, db_obj: Security, **kwargs) -> None:
        """Post-processing after updating a security."""
        logger.info(f"Updated security: {db_obj.ticker} - {db_obj.name}")
        
        # Track metrics
        self._track_metrics("security_updated", 1, {
            "security_id": str(db_obj.id),
            "ticker": db_obj.ticker
        })


# ============================================================================
# PRICE DATA SERVICE
# ============================================================================

class PriceDataService(ServiceBase[DailyPrice, DailyPriceCreate, DailyPriceUpdate, DailyPriceResponse]):
    """Service for price data operations."""
    
    def __init__(self, db: Session):
        self.crud = DailyPriceCRUD(db)
        super().__init__(self.crud, DailyPriceResponse)
    
    def get_latest_price(self, security_id: int) -> Optional[DailyPriceResponse]:
        """Get latest price for a security."""
        try:
            price = self.crud.get_latest_price(security_id)
            if price:
                return DailyPriceResponse.model_validate(price)
            return None
        except Exception as e:
            logger.error(f"Error getting latest price for security {security_id}: {e}")
            raise
    
    def get_price_history(self, search_params: PriceSearchParams) -> List[PriceHistory]:
        """Get price history for securities."""
        try:
            histories = []
            
            if not search_params.security_ids:
                return histories
            
            for security_id in search_params.security_ids:
                prices = self.crud.get_price_history(
                    security_id=security_id,
                    start_date=search_params.start_date,
                    end_date=search_params.end_date,
                    limit=365
                )
                
                if prices:
                    price_responses = [DailyPriceResponse.model_validate(p) for p in prices]
                    
                    # Calculate summary statistics
                    close_prices = [p.close_price for p in prices]
                    volumes = [p.volume for p in prices]
                    
                    history = PriceHistory(
                        security_id=security_id,
                        prices=price_responses,
                        period=self._determine_period(search_params.start_date, search_params.end_date),
                        min_price=min(close_prices) if close_prices else None,
                        max_price=max(close_prices) if close_prices else None,
                        avg_volume=sum(volumes) // len(volumes) if volumes else None,
                        total_return=self._calculate_total_return(prices),
                        volatility=self._calculate_volatility(prices)
                    )
                    
                    histories.append(history)
            
            return histories
        except Exception as e:
            logger.error(f"Error getting price history: {e}")
            raise
    
    def bulk_ingest_prices(self, bulk_prices: BulkPriceCreate) -> BulkOperationResponse:
        """Bulk ingest price data."""
        try:
            start_time = datetime.now()
            
            # Validate and process prices
            valid_prices = []
            errors = []
            
            for price in bulk_prices.prices:
                try:
                    # Basic validation
                    if price.high_price < price.low_price:
                        errors.append(f"High price < low price for {price.security_id} on {price.date}")
                        continue
                    
                    valid_prices.append(price)
                except Exception as e:
                    errors.append(f"Invalid price data: {e}")
            
            # Bulk upsert
            rows_affected = self.crud.bulk_upsert_prices(valid_prices)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            response = BulkOperationResponse(
                total_requested=len(bulk_prices.prices),
                total_created=len(valid_prices),
                total_updated=0,  # Upsert doesn't distinguish
                total_failed=len(errors),
                errors=errors if errors else None,
                processing_time_ms=processing_time
            )
            
            logger.info(f"Bulk ingested {len(valid_prices)} prices in {processing_time:.2f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Error bulk ingesting prices: {e}")
            raise
    
    def calculate_price_changes(self, security_id: int) -> Dict[str, float]:
        """Calculate price changes for a security."""
        try:
            return self.crud.calculate_price_changes(security_id)
        except Exception as e:
            logger.error(f"Error calculating price changes for security {security_id}: {e}")
            raise
    
    def _determine_period(self, start_date: Optional[date], end_date: Optional[date]) -> str:
        """Determine period string based on date range."""
        if not start_date or not end_date:
            return "custom"
        
        delta = end_date - start_date
        if delta.days <= 7:
            return "1w"
        elif delta.days <= 30:
            return "1m"
        elif delta.days <= 90:
            return "3m"
        elif delta.days <= 180:
            return "6m"
        elif delta.days <= 365:
            return "1y"
        else:
            return "5y"
    
    def _calculate_total_return(self, prices: List[DailyPrice]) -> Optional[float]:
        """Calculate total return for a price series."""
        if len(prices) < 2:
            return None
        
        # Sort by date (oldest first)
        sorted_prices = sorted(prices, key=lambda p: p.date)
        start_price = sorted_prices[0].close_price
        end_price = sorted_prices[-1].close_price
        
        if start_price > 0:
            return ((end_price - start_price) / start_price) * 100
        
        return None
    
    def _calculate_volatility(self, prices: List[DailyPrice]) -> Optional[float]:
        """Calculate price volatility."""
        if len(prices) < 2:
            return None
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1].close_price > 0:
                daily_return = (prices[i].close_price - prices[i-1].close_price) / prices[i-1].close_price
                returns.append(daily_return)
        
        if not returns:
            return None
        
        # Calculate standard deviation
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = variance ** 0.5
        
        # Annualize volatility (assuming 252 trading days)
        return volatility * (252 ** 0.5) * 100


# ============================================================================
# CORPORATE ACTION SERVICE
# ============================================================================

class CorporateActionService(ServiceBase[CorporateAction, CorporateActionCreate, CorporateActionUpdate, CorporateActionResponse]):
    """Service for corporate action operations."""
    
    def __init__(self, db: Session):
        self.crud = CorporateActionCRUD(db)
        super().__init__(self.crud, CorporateActionResponse)
    
    def get_by_security(self, security_id: int) -> List[CorporateActionResponse]:
        """Get corporate actions for a security."""
        try:
            actions = self.crud.get_by_security(security_id)
            return [CorporateActionResponse.model_validate(a) for a in actions]
        except Exception as e:
            logger.error(f"Error getting corporate actions for security {security_id}: {e}")
            raise
    
    def get_upcoming_actions(self, days_ahead: int = 30) -> List[CorporateActionResponse]:
        """Get upcoming corporate actions."""
        try:
            actions = self.crud.get_upcoming_actions(days_ahead)
            return [CorporateActionResponse.model_validate(a) for a in actions]
        except Exception as e:
            logger.error(f"Error getting upcoming corporate actions: {e}")
            raise


# ============================================================================
# WATCHLIST SERVICE
# ============================================================================

class SecurityWatchlistService(ServiceBase[SecurityWatchlist, SecurityWatchlistCreate, SecurityWatchlistUpdate, SecurityWatchlistResponse]):
    """Service for security watchlist operations."""
    
    def __init__(self, db: Session):
        self.crud = SecurityWatchlistCRUD(db)
        super().__init__(self.crud, SecurityWatchlistResponse)
    
    def get_user_watchlist(self, user_id: str) -> List[SecurityWatchlistResponse]:
        """Get user's watchlist."""
        try:
            watchlist = self.crud.get_user_watchlist(user_id)
            return [SecurityWatchlistResponse.model_validate(w) for w in watchlist]
        except Exception as e:
            logger.error(f"Error getting watchlist for user {user_id}: {e}")
            raise
    
    def add_to_watchlist(self, user_id: str, security_id: int) -> SecurityWatchlistResponse:
        """Add security to user's watchlist."""
        try:
            watchlist_item = self.crud.add_to_watchlist(user_id, security_id)
            return SecurityWatchlistResponse.model_validate(watchlist_item)
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
            raise
    
    def remove_from_watchlist(self, user_id: str, security_id: int) -> bool:
        """Remove security from user's watchlist."""
        try:
            return self.crud.remove_from_watchlist(user_id, security_id)
        except Exception as e:
            logger.error(f"Error removing from watchlist: {e}")
            raise


# ============================================================================
# DATA INGESTION SERVICE
# ============================================================================

class PriceDataIngestionService(DataIngestionInterface):
    """Service for ingesting price data from external sources."""
    
    def __init__(self, db: Session):
        self.db = db
        self.price_service = PriceDataService(db)
        self.security_crud = SecurityCRUD(db)
        
    def ingest_data(self, source: str, data: Any) -> Dict[str, Any]:
        """Ingest price data from external source."""
        try:
            logger.info(f"Starting price data ingestion from {source}")
            
            # Validate data format
            if not self.validate_data(data):
                raise ValueError("Invalid data format")
            
            # Transform data
            transformed_data = self.transform_data(data)
            
            # Bulk ingest
            bulk_create = BulkPriceCreate(prices=transformed_data)
            result = self.price_service.bulk_ingest_prices(bulk_create)
            
            logger.info(f"Completed price data ingestion from {source}: {result.total_created} created, {result.total_failed} failed")
            
            return {
                "source": source,
                "total_processed": result.total_created,
                "total_failed": result.total_failed,
                "processing_time_ms": result.processing_time_ms
            }
            
        except Exception as e:
            logger.error(f"Error ingesting price data from {source}: {e}")
            raise
    
    def validate_data(self, data: Any) -> bool:
        """Validate price data format."""
        # Implementation depends on data source format
        return True
    
    def transform_data(self, data: Any) -> List[DailyPriceCreate]:
        """Transform raw data to DailyPriceCreate objects."""
        # Implementation depends on data source format
        return []


# Factory functions for services
def get_asset_type_service(db: Session) -> AssetTypeService:
    return AssetTypeService(db)

def get_sector_service(db: Session) -> SectorService:
    return SectorService(db)

def get_exchange_service(db: Session) -> ExchangeService:
    return ExchangeService(db)

def get_security_service(db: Session) -> SecurityService:
    return SecurityService(db)

def get_price_data_service(db: Session) -> PriceDataService:
    return PriceDataService(db)

def get_corporate_action_service(db: Session) -> CorporateActionService:
    return CorporateActionService(db)

def get_security_watchlist_service(db: Session) -> SecurityWatchlistService:
    return SecurityWatchlistService(db)

def get_price_data_ingestion_service(db: Session) -> PriceDataIngestionService:
    return PriceDataIngestionService(db)


# Export all services
__all__ = [
    "AssetTypeService",
    "SectorService",
    "ExchangeService", 
    "SecurityService",
    "PriceDataService",
    "CorporateActionService",
    "SecurityWatchlistService",
    "PriceDataIngestionService",
    "get_asset_type_service",
    "get_sector_service",
    "get_exchange_service",
    "get_security_service",
    "get_price_data_service",
    "get_corporate_action_service",
    "get_security_watchlist_service",
    "get_price_data_ingestion_service"
] 