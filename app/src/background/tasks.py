"""
Background tasks for CapitolScope data processing and maintenance.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession

from background.celery_app import celery_app
from core.config import get_settings
from core.database import DatabaseManager, db_manager, get_sync_db_session
from domains.congressional.services import CongressAPIService
from domains.congressional.crud import (
    CongressMemberRepository, CongressionalTradeRepository,
    MemberPortfolioRepository, MemberPortfolioPerformanceRepository
)
from domains.congressional.ingestion import CongressionalDataIngestion
from domains.securities.ingestion import (
    populate_securities_from_major_indices,
    ingest_price_data_for_all_securities
)
from domains.securities.data_fetcher import EnhancedStockDataService, StockDataRequest

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseTask(Task):
    """Base task class that provides database session management."""
    
    def __call__(self, *args, **kwargs):
        try:
            logger.debug(f"Starting task {self.name} with args: {args}, kwargs: {kwargs}")
            result = super().__call__(*args, **kwargs)
            logger.debug(f"Task {self.name} completed successfully")
            return result
        except Exception as exc:
            logger.error(f"Task {self.name} failed: {exc}", exc_info=True)
            raise


def run_async_task(coro):
    """
    Helper function to run async functions in sync Celery tasks.
    
    This handles different execution contexts:
    - Celery workers (separate processes)
    - FastAPI background tasks (uvloop context)
    - Direct script execution
    """
    try:
        logger.debug("Attempting to run async task")
        
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        
        # Check if loop is already running
        if loop.is_running():
            # We're in an environment with a running loop (like FastAPI/uvloop)
            # Check if it's uvloop (which doesn't support nest_asyncio)
            loop_type = type(loop).__name__
            
            logger.debug(f"Running loop detected: {loop_type}")
            
            if 'uvloop' in loop_type.lower():
                # In uvloop context (FastAPI), we can't use nest_asyncio
                # This should not happen in Celery workers, but if it does,
                # we need to run in a separate thread
                import concurrent.futures
                import threading
                
                logger.warning(f"Running async task in uvloop context ({loop_type}), using thread pool")
                
                def run_in_thread():
                    # Create a new event loop in this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(coro)
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result()
            else:
                # Non-uvloop event loop, try nest_asyncio
                try:
                    import nest_asyncio
                    # Check if already patched to avoid double-patching
                    if not hasattr(loop, '_nest_asyncio_patched'):
                        nest_asyncio.apply(loop)
                        loop._nest_asyncio_patched = True
                    
                    logger.debug(f"Using nest_asyncio for loop type: {loop_type}")
                    return loop.run_until_complete(coro)
                    
                except ImportError:
                    logger.error("nest_asyncio not available and running loop detected")
                    raise RuntimeError(
                        "Cannot run async task: nest_asyncio not available and event loop is running"
                    )
                except Exception as e:
                    logger.error(f"nest_asyncio failed: {e}")
                    raise RuntimeError(f"Failed to patch event loop with nest_asyncio: {e}")
        else:
            # No running loop, we can create our own
            logger.debug("No running event loop, creating new one")
            return loop.run_until_complete(coro)
            
    except RuntimeError as e:
        if "no running event loop" in str(e).lower() or "no current event loop" in str(e).lower():
            # No event loop exists, create a new one
            logger.debug("Creating new event loop for async task")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                # Clean up the loop
                asyncio.set_event_loop(None)
                loop.close()
        else:
            logger.error(f"Event loop error: {e}")
            raise


async def get_db_session_async():
    """Get async database session for background tasks."""
    logger.debug("Initializing database session for background task")
    
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    if not db_manager.session_factory:
        raise RuntimeError("Database session factory not initialized")
        
    logger.debug("Database session factory initialized successfully")
    
    async with db_manager.session_factory() as session:
        try:
            logger.debug("Database session created, yielding to task")
            yield session
            await session.commit()
            logger.debug("Database session committed successfully")
        except Exception:
            await session.rollback()
            logger.error("Database session rolled back due to error")
            raise
        finally:
            await db_manager.close()
            logger.debug("Database manager closed")


# ============================================================================
# CONGRESSIONAL DATA INGESTION TASKS
# ============================================================================

@celery_app.task(base=DatabaseTask, bind=True)
def sync_congressional_members(self, action: str = "sync-all", **kwargs):
    """
    Sync congressional members from Congress.gov API.
    
    Args:
        action: Action to perform ('sync-all', 'sync-state', 'sync-member', 'enrich-existing')
        **kwargs: Additional parameters for specific actions
    """
    logger.info(f"Received congressional members sync task: action={action}, kwargs={kwargs}")
    return run_async_task(_sync_congressional_members_async(action, **kwargs))


async def _sync_congressional_members_async(action: str, **kwargs) -> Dict[str, Any]:
    """Async implementation of congressional members sync."""
    
    try:
        logger.info(f"Starting congressional members sync: action={action}, kwargs={kwargs}")
        
        # Initialize database first
        from core.database import db_manager
        
        # Ensure database is initialized
        if not db_manager._initialized:
            logger.debug("Database manager not initialized, initializing now")
            await db_manager.initialize()
            logger.debug("Database manager initialized successfully")
        
        logger.debug("Creating async database session")
        async with db_manager.session_factory() as session:
            # Initialize services with async session
            logger.debug("Initializing repositories")
            member_repo = CongressMemberRepository(session)
            trade_repo = CongressionalTradeRepository(session)
            portfolio_repo = MemberPortfolioRepository(session)
            performance_repo = MemberPortfolioPerformanceRepository(session)
            
            logger.debug("Initializing CongressAPIService")
            api_service = CongressAPIService(
                member_repo=member_repo,
                trade_repo=trade_repo,
                portfolio_repo=portfolio_repo,
                performance_repo=performance_repo
            )
            
            # Execute the appropriate sync action
            logger.info(f"Executing sync action: action={action}")
            
            if action == "sync-all":
                logger.debug("Starting sync-all action")
                results = await api_service.sync_all_members()
                logger.info(f"sync-all action completed: results={results}")
            elif action == "sync-state" and "state" in kwargs:
                logger.debug(f"Starting sync-state action: state={kwargs['state']}")
                results = await api_service.sync_members_by_state(kwargs["state"])
                logger.info(f"sync-state action completed: results={results}")
            elif action == "sync-member" and "bioguide_id" in kwargs:
                logger.debug(f"Starting sync-member action: bioguide_id={kwargs['bioguide_id']}")
                result = await api_service.sync_member_by_bioguide_id(kwargs["bioguide_id"])
                results = {"action": result, "bioguide_id": kwargs["bioguide_id"]}
                logger.info(f"sync-member action completed: results={results}")
            elif action == "enrich-existing":
                logger.debug("Starting enrich-existing action")
                results = await _enrich_existing_members(member_repo, api_service)
                logger.info(f"enrich-existing action completed: results={results}")
            else:
                logger.error(f"Invalid action specified: action={action}")
                raise ValueError(f"Invalid action: {action}")
            
            # Commit changes (handled by context manager)
            await session.commit()
            logger.info(f"Congressional members sync completed: action={action}, results={results}")
            return {
                "status": "success",
                "action": action,
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as exc:
        logger.error(f"Congressional members sync failed: action={action}, error={str(exc)}", exc_info=True)
        raise


async def _enrich_existing_members(member_repo: CongressMemberRepository, api_service: CongressAPIService) -> Dict[str, Any]:
    """Enrich existing members with additional Congress.gov data."""
    from domains.congressional.schemas import MemberQuery
    
    logger.debug("Starting enrichment of existing members")
    
    # Get all members with bioguide IDs using async repository
    query = MemberQuery(limit=1000)
    logger.debug(f"Fetching existing members for enrichment: limit={query.limit}")
    
    members, total_count = await member_repo.list_members(query)
    logger.info(f"Found {len(members)} members to enrich: total_count={total_count}")
    
    enriched_count = 0
    failed_count = 0
    
    for i, member in enumerate(members):
        if member.bioguide_id:
            logger.debug(f"Enriching member {i+1}/{len(members)}: member_id={member.id}, bioguide_id={member.bioguide_id}, name={member.full_name}")
            
            try:
                result = await api_service.sync_member_by_bioguide_id(member.bioguide_id)
                if result in ["updated", "created"]:
                    enriched_count += 1
                    logger.info(f"Enriched member: member_id={member.id}, name={member.full_name}, result={result}")
                else:
                    logger.debug(f"No changes needed for member: member_id={member.id}, name={member.full_name}, result={result}")
            except Exception as e:
                logger.error(f"Failed to enrich member: member_id={member.id}, name={member.full_name}, error={str(e)}")
                failed_count += 1
                continue
    
    results = {
        "enriched": enriched_count,
        "failed": failed_count,
        "total_processed": enriched_count + failed_count,
        "total_members": len(members)
    }
    
    logger.info(f"Member enrichment completed: results={results}")
    return results


@celery_app.task(base=DatabaseTask, bind=True)
def comprehensive_data_ingestion(self):
    """
    Comprehensive data ingestion workflow that syncs all congressional data.
    
    This is the main orchestration task that runs:
    1. Member data sync from Congress.gov
    2. Legislative data enrichment
    3. Trading data updates
    4. Portfolio recalculations
    """
    logger.info("Received comprehensive data ingestion task")
    return run_async_task(_comprehensive_data_ingestion_async())


async def _comprehensive_data_ingestion_async() -> Dict[str, Any]:
    """Async implementation of comprehensive data ingestion."""
    try:
        logger.info("Starting comprehensive data ingestion workflow")
        start_time = datetime.utcnow()
        results = {}
        
        # Step 1: Sync congressional members
        logger.info("Step 1: Syncing congressional members")
        member_sync_results = await _sync_congressional_members_async("sync-all")
        results["member_sync"] = member_sync_results
        logger.info(f"Step 1 completed: results={member_sync_results}")
        
        # Step 2: Enrich member data with legislation
        logger.info("Step 2: Enriching member data")
        enrich_results = await _sync_congressional_members_async("enrich-existing")
        results["enrichment"] = enrich_results
        logger.info(f"Step 2 completed: results={enrich_results}")
        
        # TODO: Implement stock price update logic
        # NOTE: Do I implement this here or in the ingestion task?
        # # Step 3: Update stock prices (if we have trades)
        # logger.info("Step 3: Updating stock prices")
        # price_update_results = await _update_stock_prices_async()
        # results["price_updates"] = price_update_results
        # logger.info("Step 3 completed", results=price_update_results)
        
        # TODO: Implement portfolio recalculation logic
        # NOTE: Do I implement this here or in the ingestion task?
        # Step 4: Recalculate portfolios and performance
        logger.info("Step 4: Recalculating portfolios")
        portfolio_results = await _recalculate_portfolios_async()
        results["portfolio_calculations"] = portfolio_results
        logger.info(f"Step 4 completed: results={portfolio_results}")
        
        end_time = datetime.utcnow()
        duration = end_time - start_time
        
        logger.info(f"Comprehensive data ingestion completed: duration_seconds={duration.total_seconds()}, start_time={start_time.isoformat()}, end_time={end_time.isoformat()}")
        
        return {
            "status": "success",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "results": results
        }
        
    except Exception as exc:
        logger.error(f"Comprehensive data ingestion failed: error={str(exc)}", exc_info=True)
        raise


# ============================================================================
# TRADING DATA TASKS
# ============================================================================

@celery_app.task(base=DatabaseTask, bind=True)
def sync_congressional_trades(self, date_from: Optional[str] = None):
    """
    Sync congressional trading data from external sources.
    
    Args:
        date_from: ISO date string to sync from (defaults to yesterday)
    """
    try:
        logger.info(f"Starting congressional trades synchronization: date_from={date_from}")
        
        if not date_from:
            date_from = (datetime.utcnow() - timedelta(days=1)).isoformat()
            logger.debug(f"No date_from specified, using yesterday: date_from={date_from}")
        
        # TODO: Implement actual data synchronization logic
        # This would typically involve:
        # 1. Fetching data from external APIs (House/Senate disclosure sites)
        # 2. Parsing PDF files or structured data
        # 3. Normalizing and validating the data
        # 4. Storing in database with proper conflict resolution
        
        logger.info(f"Congressional trades sync completed: date_from={date_from}, records_processed=0")
        return {"status": "success", "date_from": date_from, "records_processed": 0}
        
    except Exception as exc:
        logger.error(f"Congressional trades sync failed: date_from={date_from}, error={str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=300, max_retries=3)


@celery_app.task(base=DatabaseTask, bind=True)
def update_stock_prices(self, symbols: Optional[List[str]] = None):
    """
    Update stock prices for tracked securities.
    
    Args:
        symbols: List of stock symbols to update (defaults to all tracked)
    """
    logger.info(f"Received stock price update task: symbols_count={len(symbols) if symbols else None}")
    return run_async_task(_update_stock_prices_async(symbols))


async def _update_stock_prices_async(symbols: Optional[List[str]] = None) -> Dict[str, Any]:
    """Async implementation of stock price updates."""
    try:
        logger.info(f"Starting stock price updates: symbols_count={len(symbols) if symbols else None}")
        
        # NOTE: This is a placeholder for the actual stock price update logic.
        # Do I implement this here or in the ingestion task?
        # TODO: Implement stock price update logic
        # This would typically involve:
        # 1. Querying all unique symbols from congressional trades
        # 2. Fetching current/latest prices from financial APIs
        # 3. Updating price history and current values
        # 4. Calculating portfolio performance metrics
        
        processed_count = 0
        if symbols:
            processed_count = len(symbols)
            logger.info(f"Updated prices for {processed_count} symbols: symbols={symbols}")
        else:
            logger.info("Updated prices for all tracked securities")
        
        return {"status": "success", "symbols_updated": processed_count}
        
    except Exception as exc:
        logger.error(f"Stock price update failed: symbols={symbols}, error={str(exc)}", exc_info=True)
        raise


async def _recalculate_portfolios_async() -> Dict[str, Any]:
    """Recalculate portfolio values and performance metrics."""
    try:
        logger.info("Starting portfolio recalculations")
        
        # TODO: Implement portfolio recalculation logic
        # This would typically involve:
        # 1. Getting all congressional members with trades
        # 2. Recalculating current portfolio values
        # 3. Updating performance metrics
        # 4. Generating analytics summaries
        
        portfolios_updated = 0
        logger.info(f"Recalculated {portfolios_updated} member portfolios")
        
        return {"status": "success", "portfolios_updated": portfolios_updated}
        
    except Exception as exc:
        logger.error(f"Portfolio recalculation failed: error={str(exc)}", exc_info=True)
        raise


# ============================================================================
# MAINTENANCE AND CLEANUP TASKS
# ============================================================================

@celery_app.task(base=DatabaseTask, bind=True)
def cleanup_old_data(self, days_to_keep: int = 90):
    """
    Clean up old temporary data and logs.
    
    Args:
        days_to_keep: Number of days of data to retain
    """
    try:
        logger.info(f"Starting cleanup of data older than {days_to_keep} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        logger.debug(f"Calculated cutoff date: cutoff_date={cutoff_date.isoformat()}")
        
        # TODO: Implement cleanup logic
        # This would typically involve:
        # 1. Cleaning up old session data
        # 2. Removing temporary files
        # 3. Archiving old log entries
        # 4. Cleaning up expired user notifications
        
        cleaned_items = 0
        logger.info(f"Cleanup completed: items_cleaned={cleaned_items}, cutoff_date={cutoff_date.isoformat()}")
        
        return {"status": "success", "items_cleaned": cleaned_items, "cutoff_date": cutoff_date.isoformat()}
        
    except Exception as exc:
        logger.error(f"Data cleanup failed: days_to_keep={days_to_keep}, error={str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=600, max_retries=2)


@celery_app.task(base=DatabaseTask, bind=True)
def send_trade_alerts(self, user_id: Optional[int] = None):
    """
    Send trading alerts to users based on their watchlists and preferences.
    
    Args:
        user_id: Specific user to send alerts to (defaults to all eligible users)
    """
    try:
        logger.info(f"Starting trade alert processing: user_id={user_id}")
        
        # TODO: Implement alert logic
        # This would typically involve:
        # 1. Finding users with active watchlists
        # 2. Checking for new trades matching their criteria
        # 3. Sending email/in-app notifications
        # 4. Updating notification history
        
        alerts_sent = 0
        logger.info(f"Trade alerts completed: alerts_sent={alerts_sent}, user_id={user_id}")
        
        return {"status": "success", "alerts_sent": alerts_sent}
        
    except Exception as exc:
        logger.error(f"Trade alerts failed: user_id={user_id}, error={str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=300, max_retries=3)


@celery_app.task(base=DatabaseTask, bind=True)
def process_new_trade_notifications(self, doc_id: str, member_id: str, transaction_date: str):
    """
    Process notifications for a newly inserted trade.
    
    Args:
        doc_id: Trade document ID
        member_id: Congress member ID (UUID string)
        transaction_date: Trade transaction date (ISO format)
    """
    try:
        logger.info(f"Processing notifications for trade: doc_id={doc_id}, member_id={member_id}")
        
        # Use sync session for Celery tasks
        with get_sync_db_session() as session:
            from sqlalchemy import and_
            from datetime import datetime
            from domains.congressional.models import CongressionalTrade
            from domains.congressional.schemas import CongressionalTradeDetail
            
            # Find the trade by doc_id, member_id, and transaction_date
            from uuid import UUID
            trade_date = datetime.fromisoformat(transaction_date).date()
            member_uuid = UUID(member_id) if isinstance(member_id, str) else member_id
            trade = session.query(CongressionalTrade).filter(
                and_(
                    CongressionalTrade.doc_id == doc_id,
                    CongressionalTrade.member_id == member_uuid,
                    CongressionalTrade.transaction_date == trade_date
                )
            ).first()
            
            if not trade:
                logger.warning(f"Trade not found: doc_id={doc_id}, member_id={member_id}")
                return {"status": "error", "message": "Trade not found"}
            
            # Convert to schema object for processing
            trade_detail = CongressionalTradeDetail.from_orm(trade)
            
            # Run async notification processing in sync context
            import asyncio
            from sqlalchemy.ext.asyncio import AsyncSession
            from core.database import db_manager
            from domains.notifications.trade_detection import TradeDetectionService
            
            async def process_notifications():
                """Process notifications asynchronously."""
                db_manager_instance = DatabaseManager()
                await db_manager_instance.initialize()
                
                try:
                    async with db_manager_instance.session_factory() as async_session:
                        detection_service = TradeDetectionService(async_session)
                        result = await detection_service.process_new_trade(trade_detail)
                        return result
                finally:
                    await db_manager_instance.close()
            
            # Run the async function
            result = run_async_task(process_notifications())
            
            logger.info(f"Trade {doc_id} notifications processed: {result}")
            return {"status": "success", "result": result}
            
    except Exception as exc:
        logger.error(f"Error processing notifications for trade {doc_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300, max_retries=3)


@celery_app.task(base=DatabaseTask, bind=True)
def generate_analytics_report(self, report_type: str = "daily"):
    """
    Generate analytics reports for portfolio performance and trading patterns.
    
    Args:
        report_type: Type of report to generate (daily, weekly, monthly)
    """
    try:
        logger.info(f"Starting {report_type} analytics report generation")
        
        # TODO: Implement analytics generation
        # This would typically involve:
        # 1. Aggregating trading data by various dimensions
        # 2. Calculating performance metrics
        # 3. Generating trend analyses
        # 4. Storing report data for quick access
        
        logger.info(f"{report_type} analytics report completed")
        
        return {"status": "success", "report_type": report_type}
        
    except Exception as exc:
        logger.error(f"Analytics report generation failed: report_type={report_type}, error={str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=600, max_retries=2)


# ============================================================================
# HEALTH CHECK AND MONITORING TASKS
# ============================================================================

@celery_app.task(base=DatabaseTask, bind=True)
def health_check_congress_api(self):
    """
    Health check for Congress.gov API connectivity.
    """
    logger.info("Received Congress API health check task")
    return run_async_task(_health_check_congress_api_async())


async def _health_check_congress_api_async() -> Dict[str, Any]:
    """Async implementation of Congress API health check."""
    
    try:
        from domains.congressional.client import CongressAPIClient
        
        logger.info("Running Congress.gov API health check")
        
        async with CongressAPIClient() as client:
            # Try to fetch a small number of members
            logger.debug("Fetching test member list from Congress.gov API")
            response = await client.get_member_list(limit=1)
            
            if response.members:
                logger.info(f"Congress.gov API health check passed: member_count={len(response.members)}")
                return {
                    "status": "healthy",
                    "api_name": "Congress.gov",
                    "timestamp": datetime.utcnow().isoformat(),
                    "response_time_ms": None  # Could measure this
                }
            else:
                logger.warning("Congress.gov API health check failed - no data returned")
                return {
                    "status": "unhealthy",
                    "api_name": "Congress.gov",
                    "error": "No data returned",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
    except Exception as exc:
        logger.error(f"Congress.gov API health check failed: error={str(exc)}", exc_info=True)
        return {
            "status": "unhealthy",
            "api_name": "Congress.gov",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }


# ============================================================================
# TASK SCHEDULING AND ORCHESTRATION
# ============================================================================

@celery_app.task(bind=True)
def schedule_daily_ingestion(self):
    """
    Schedule the daily comprehensive data ingestion workflow.
    This task is typically run by a cron job or periodic scheduler.
    """
    try:
        logger.info("Scheduling daily data ingestion workflow")
        
        # Queue the comprehensive ingestion task
        result = comprehensive_data_ingestion.delay()
        
        logger.info(f"Daily ingestion task scheduled: task_id={result.id}")
        
        return {
            "status": "scheduled",
            "task_id": result.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to schedule daily ingestion: error={str(exc)}", exc_info=True)
        raise


@celery_app.task(bind=True) 
def schedule_weekly_maintenance(self):
    """
    Schedule weekly maintenance tasks.
    """
    try:
        logger.info("Scheduling weekly maintenance tasks")
        
        # Queue maintenance tasks
        cleanup_task = cleanup_old_data.delay(days_to_keep=90)
        analytics_task = generate_analytics_report.delay(report_type="weekly")
        
        logger.info(f"Weekly maintenance tasks scheduled: cleanup_task_id={cleanup_task.id}, analytics_task_id={analytics_task.id}")
        
        return {
            "status": "scheduled",
            "cleanup_task_id": cleanup_task.id,
            "analytics_task_id": analytics_task.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to schedule weekly maintenance: error={str(exc)}", exc_info=True)
        raise


# ============================================================================
# ENHANCED DATA TASKS
# ============================================================================

@celery_app.task(base=DatabaseTask, bind=True)
def seed_securities_database(self, include_prices: bool = False, batch_size: int = 50):
    """
    Seed the securities database with major market indices.
    
    Args:
        include_prices: Whether to also fetch historical price data
        batch_size: Batch size for price data processing
    """
    logger.info(f"Received securities database seeding task: include_prices={include_prices}, batch_size={batch_size}")
    return run_async_task(_seed_securities_database_async(include_prices, batch_size))


async def _seed_securities_database_async(include_prices: bool, batch_size: int) -> Dict[str, Any]:
    """Async implementation of securities database seeding."""
    try:
        logger.info(f"Starting securities database seeding: include_prices={include_prices}, batch_size={batch_size}")
        
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        results = {}
        
        async with db_manager.session_factory() as session:
            # Step 1: Populate securities from major indices
            logger.info("Populating securities from major market indices")
            securities_result = await populate_securities_from_major_indices(session)
            results["securities"] = securities_result
            logger.info(f"Securities population completed: results={securities_result}")
            
            # Step 2: Fetch price data (optional)
            if include_prices:
                logger.info(f"Fetching historical price data for all securities: batch_size={batch_size}")
                prices_result = await ingest_price_data_for_all_securities(
                    session, batch_size=batch_size
                )
                results["prices"] = prices_result
                logger.info(f"Price data ingestion completed: results={prices_result}")
            
            await session.commit()
            logger.debug("Database session committed")
        
        logger.info(f"Securities database seeding completed: results={results}")
        return {
            "status": "success",
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Securities database seeding failed: include_prices={include_prices}, batch_size={batch_size}, error={str(exc)}", exc_info=True)
        raise
    finally:
        await db_manager.close()
        logger.debug("Database manager closed")


@celery_app.task(base=DatabaseTask, bind=True)
def fetch_stock_data_enhanced(self, tickers: Optional[List[str]] = None, 
                            interval: str = "1d", 
                            start_date: str = "2014-01-01",
                            end_date: Optional[str] = None,
                            source: str = "yfinance",
                            use_async: bool = True,
                            batch_size: int = 10):
    """
    Fetch stock data using the enhanced stock data service.
    
    Args:
        tickers: List of ticker symbols (None for all major indices)
        interval: Data interval (1d, 1wk, 1mo)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (None for today)
        source: Data source (yfinance, alpha_vantage)
        use_async: Whether to use async fetching
        batch_size: Batch size for async operations
    """
    logger.info(f"Received enhanced stock data fetching task: tickers_count={len(tickers) if tickers else None}, interval={interval}, start_date={start_date}, end_date={end_date}, source={source}, use_async={use_async}, batch_size={batch_size}")
    
    return run_async_task(_fetch_stock_data_enhanced_async(
        tickers, interval, start_date, end_date, source, use_async, batch_size
    ))


async def _fetch_stock_data_enhanced_async(tickers: Optional[List[str]], 
                                         interval: str,
                                         start_date: str, 
                                         end_date: Optional[str],
                                         source: str,
                                         use_async: bool,
                                         batch_size: int) -> Dict[str, Any]:
    """Async implementation of enhanced stock data fetching."""
    try:
        logger.info(f"Starting enhanced stock data fetching: tickers_count={len(tickers) if tickers else None}, interval={interval}, start_date={start_date}, end_date={end_date}, source={source}, use_async={use_async}, batch_size={batch_size}")
        
        # Initialize service
        logger.debug("Initializing EnhancedStockDataService")
        service = EnhancedStockDataService()
        
        # Create request template
        request_template = StockDataRequest(
            symbol="",  # Will be replaced
            interval=interval,
            start_date=start_date,
            end_date=end_date or str(datetime.now().date()),
            source=source
        )
        
        if tickers:
            # Fetch specific tickers
            logger.debug(f"Fetching specific tickers: tickers={tickers}")
            requests = []
            for ticker in tickers:
                request = StockDataRequest(
                    symbol=ticker,
                    interval=interval,
                    start_date=start_date,
                    end_date=end_date or str(datetime.now().date()),
                    source=source
                )
                requests.append(request)
            
            if use_async:
                logger.debug("Using async fetching for specific tickers")
                responses = await service.fetch_multiple_stocks_async(requests, batch_size)
            else:
                logger.debug("Using sync fetching for specific tickers")
                responses = service.fetch_multiple_stocks(requests)
        else:
            # Fetch all major indices
            logger.debug("Fetching all major indices")
            if use_async:
                logger.debug("Using async fetching for major indices")
                responses = await service.fetch_all_major_stocks_async(request_template, batch_size)
            else:
                logger.debug("Using sync fetching for major indices")
                responses = service.fetch_all_major_stocks(request_template)
        
        # Analyze results
        successful = [r for r in responses if r.success]
        failed = [r for r in responses if not r.success]
        total_records = sum(len(r.data) for r in successful)
        
        results = {
            "total_tickers": len(responses),
            "successful_tickers": len(successful),
            "failed_tickers": len(failed),
            "total_records": total_records,
            "success_rate": len(successful) / len(responses) * 100 if responses else 0,
            "failed_symbols": [(r.symbol, r.error) for r in failed]
        }
        
        logger.info(f"Enhanced stock data fetching completed: results={results}")
        return {
            "status": "success",
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Enhanced stock data fetching failed: tickers={tickers}, interval={interval}, source={source}, error={str(exc)}", exc_info=True)
        raise


@celery_app.task(base=DatabaseTask, bind=True)
def import_congressional_data_csvs(self, csv_directory: str):
    """
    Import congressional trading data from CSV files.
    
    Args:
        csv_directory: Path to directory containing CSV files
    """
    try:
        logger.info(f"Starting congressional data import from CSVs: csv_directory={csv_directory}")
        
        with get_sync_db_session() as session:
            logger.debug("Creating CongressionalDataIngestion")
            ingester = CongressionalDataIngestion(session)
            logger.debug("Starting CSV import")
            result = ingester.import_congressional_data_from_csvs_sync(csv_directory)
        
        logger.info(f"Congressional CSV import completed: results={result}")
        return {
            "status": "success",
            "results": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Congressional CSV import failed: csv_directory={csv_directory}, error={str(exc)}", exc_info=True)
        raise


@celery_app.task(base=DatabaseTask, bind=True)
def enrich_congressional_member_data(self):
    """
    Enrich congressional member profiles with additional data.
    """
    try:
        logger.info("Starting congressional member data enrichment")
        
        with get_sync_db_session() as session:
            logger.debug("Creating CongressionalDataIngestion for enrichment")
            ingester = CongressionalDataIngestion(session)
            logger.debug("Starting member data enrichment")
            result = ingester.enrich_member_data_sync()
        
        logger.info(f"Congressional member enrichment completed: results={result}")
        return {
            "status": "success",
            "results": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Congressional member enrichment failed: error={str(exc)}", exc_info=True)
        raise


# ============================================================================
# NOTIFICATION AND ALERT TASKS
# ============================================================================

@celery_app.task(base=DatabaseTask, bind=True)
def process_pending_notifications(self):
    """Process pending notifications and send alerts."""
    logger.info("Received pending notifications processing task")
    return run_async_task(_process_pending_notifications_async())


async def _process_pending_notifications_async() -> Dict[str, Any]:
    """Async implementation of pending notifications processing."""
    try:
        logger.info("Starting pending notifications processing")
        
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        notifications_processed = 0
        errors = []
        
        async with db_manager.session_factory() as session:
            from domains.notifications.trade_detection import TradeDetectionService
            from datetime import datetime, timedelta
            
            # Initialize trade detection service
            detection_service = TradeDetectionService(session)
            
            # Find new trades in the last hour that might need notification processing
            since_date = datetime.utcnow() - timedelta(hours=1)
            new_trades = await detection_service.detect_new_trades(since_date)
            
            if new_trades:
                logger.info(f"Found {len(new_trades)} new trades to process for notifications")
                
                # Process notifications for new trades
                result = await detection_service.batch_process_trades(new_trades)
                notifications_processed = result.get("total_notifications", 0)
                errors = result.get("errors", [])
                
                logger.info(f"Processed {len(new_trades)} trades, sent {notifications_processed} notifications")
            else:
                logger.info("No new trades found for notification processing")
            
            await session.commit()
        
        await db_manager.close()
        
        return {
            "status": "success",
            "trades_processed": len(new_trades) if new_trades else 0,
            "notifications_processed": notifications_processed,
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Pending notifications processing failed: error={str(exc)}", exc_info=True)
        raise


@celery_app.task(base=DatabaseTask, bind=True)
def daily_maintenance(self):
    """Run daily maintenance tasks."""
    try:
        logger.info("Starting daily maintenance tasks")
        
        # TODO: Implement daily maintenance logic
        # This would typically involve:
        # 1. Database optimization and cleanup
        # 2. Log rotation and cleanup
        # 3. Cache cleanup
        # 4. Data validation checks
        # 5. Performance metrics collection
        
        tasks_completed = 0
        logger.info(f"Daily maintenance completed: tasks_completed={tasks_completed}")
        
        return {"status": "success", "tasks_completed": tasks_completed}
        
    except Exception as exc:
        logger.error(f"Daily maintenance failed: error={str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=600, max_retries=2)


@celery_app.task(base=DatabaseTask, bind=True)
def system_health_check(self):
    """Comprehensive system health check."""
    try:
        logger.info("Starting system health check")
        
        health_status = {
            "database": "unknown",
            "redis": "unknown",
            "external_apis": "unknown",
            "disk_space": "unknown",
            "memory_usage": "unknown",
            "celery_workers": "unknown"
        }
        
        # Check database connectivity
        try:
            with get_sync_db_session() as session:
                session.execute("SELECT 1")
                health_status["database"] = "healthy"
                logger.debug("Database health check passed")
        except Exception as e:
            health_status["database"] = f"unhealthy: {str(e)}"
            logger.error(f"Database health check failed: {e}")
        
        # Check Redis connectivity
        try:
            import redis
            redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            redis_client.ping()
            health_status["redis"] = "healthy"
            logger.debug("Redis health check passed")
        except Exception as e:
            health_status["redis"] = f"unhealthy: {str(e)}"
            logger.error(f"Redis health check failed: {e}")
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_percentage = (free / total) * 100
            if free_percentage > 20:
                health_status["disk_space"] = f"healthy ({free_percentage:.1f}% free)"
            elif free_percentage > 10:
                health_status["disk_space"] = f"warning ({free_percentage:.1f}% free)"
            else:
                health_status["disk_space"] = f"critical ({free_percentage:.1f}% free)"
            logger.debug(f"Disk space check: {free_percentage:.1f}% free")
        except Exception as e:
            health_status["disk_space"] = f"error: {str(e)}"
            logger.error(f"Disk space check failed: {e}")
        
        # Check memory usage
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent < 80:
                health_status["memory_usage"] = f"healthy ({memory.percent:.1f}% used)"
            elif memory.percent < 90:
                health_status["memory_usage"] = f"warning ({memory.percent:.1f}% used)"
            else:
                health_status["memory_usage"] = f"critical ({memory.percent:.1f}% used)"
            logger.debug(f"Memory usage check: {memory.percent:.1f}% used")
        except Exception as e:
            health_status["memory_usage"] = f"error: {str(e)}"
            logger.error(f"Memory usage check failed: {e}")
        
        # Overall health determination
        unhealthy_components = [k for k, v in health_status.items() if "unhealthy" in v or "critical" in v]
        overall_status = "unhealthy" if unhealthy_components else "healthy"
        
        logger.info(f"System health check completed: overall_status={overall_status}, health_status={health_status}")
        
        return {
            "status": "success",
            "overall_health": overall_status,
            "components": health_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"System health check failed: error={str(exc)}", exc_info=True)
        raise