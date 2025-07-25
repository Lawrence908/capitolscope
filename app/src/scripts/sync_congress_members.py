#!/usr/bin/env python3
"""
Script to sync congressional members from Congress.gov API.

This script fetches member data from the Congress.gov API and updates the database
with the latest information. It can be run manually or scheduled as a cron job.

Usage:
    python src/scripts/sync_congress_members.py --action sync-all
    python src/scripts/sync_congress_members.py --action sync-member --bioguide-id <bioguide_id>
    python src/scripts/sync_congress_members.py --action sync-state --state <state_code>
    python src/scripts/sync_congress_members.py --action test-api
    python src/scripts/sync_congress_members.py --action enrich-existing
    
    docker exec -it capitolscope-dev python /app/src/scripts/sync_congress_members.py --action sync-all
    docker exec -it capitolscope-dev python /app/src/scripts/sync_congress_members.py --action enrich-existing
"""

import asyncio
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any

from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import DatabaseManager
import logging
logger = logging.getLogger(__name__)
from domains.congressional.services import CongressAPIService
from domains.congressional.crud import (
    CongressMemberRepository, 
    CongressionalTradeRepository,
    MemberPortfolioRepository,
    MemberPortfolioPerformanceRepository
)
from domains.congressional.client import CongressAPIClient

load_dotenv()


async def sync_all_members() -> Dict[str, Any]:
    """
    Sync all members from Congress.gov API.
    
    Returns:
        Dict with sync results.
    """
    logger.info("Starting full member sync from Congress.gov API")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        if not db_manager.session_factory:
            raise RuntimeError("Database session factory not initialized")
        async with db_manager.session_factory() as session:
            # Initialize repositories
            member_repo = CongressMemberRepository(session)
            trade_repo = CongressionalTradeRepository(session)
            portfolio_repo = MemberPortfolioRepository(session)
            performance_repo = MemberPortfolioPerformanceRepository(session)
            
            # Initialize service with all required repositories
            api_service = CongressAPIService(
                member_repo=member_repo,
                trade_repo=trade_repo,
                portfolio_repo=portfolio_repo,
                performance_repo=performance_repo
            )
            
            # Perform sync
            results = await api_service.sync_all_members()
            
            # Commit changes
            await session.commit()
            
            return results
            
    except Exception as e:
        logger.error(f"Error during member sync: {e}")
        raise
    finally:
        await db_manager.close()


async def sync_member_by_bioguide_id(bioguide_id: str) -> Dict[str, Any]:
    """
    Sync a specific member by bioguide ID.
    
    Args:
        bioguide_id: Bioguide ID of the member.
        
    Returns:
        Dict with sync results.
    """
    logger.info(f"Syncing member by bioguide ID: {bioguide_id}")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        async with db_manager.session_factory() as session:
            # Initialize repositories
            member_repo = CongressMemberRepository(session)
            trade_repo = CongressionalTradeRepository(session)
            portfolio_repo = MemberPortfolioRepository(session)
            performance_repo = MemberPortfolioPerformanceRepository(session)
            
            # Initialize service with all required repositories
            api_service = CongressAPIService(
                member_repo=member_repo,
                trade_repo=trade_repo,
                portfolio_repo=portfolio_repo,
                performance_repo=performance_repo
            )
            
            # Perform sync
            result = await api_service.sync_member_by_bioguide_id(bioguide_id)
            
            # Commit changes
            await session.commit()
            
            return {"action": result, "bioguide_id": bioguide_id}
            
    except Exception as e:
        logger.error(f"Error syncing member {bioguide_id}: {e}")
        raise
    finally:
        await db_manager.close()


async def sync_members_by_state(state_code: str) -> Dict[str, Any]:
    """
    Sync members from a specific state.
    
    Args:
        state_code: Two-letter state code.
        
    Returns:
        Dict with sync results.
    """
    logger.info(f"Syncing members for state: {state_code}")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        async with db_manager.session_factory() as session:
            # Initialize repositories
            member_repo = CongressMemberRepository(session)
            trade_repo = CongressionalTradeRepository(session)
            portfolio_repo = MemberPortfolioRepository(session)
            performance_repo = MemberPortfolioPerformanceRepository(session)
            
            # Initialize service with all required repositories
            api_service = CongressAPIService(
                member_repo=member_repo,
                trade_repo=trade_repo,
                portfolio_repo=portfolio_repo,
                performance_repo=performance_repo
            )
            
            # Perform sync
            results = await api_service.sync_members_by_state(state_code)
            
            # Commit changes
            await session.commit()
            
            return results
            
    except Exception as e:
        logger.error(f"Error syncing members for state {state_code}: {e}")
        raise
    finally:
        await db_manager.close()


async def test_api_connection() -> bool:
    """
    Test the connection to Congress.gov API.
    
    Returns:
        True if connection is successful.
    """
    logger.info("Testing Congress.gov API connection")
    
    try:
        async with CongressAPIClient() as client:
            # Try to fetch a small number of members
            response = await client.get_member_list(limit=1)
            
            if response.members:
                logger.info("API connection successful")
                return True
            else:
                logger.warning("API connection successful but no members returned")
                return False
                
    except Exception as e:
        logger.error(f"API connection failed: {e}")
        return False


async def enrich_existing_members() -> Dict[str, Any]:
    """
    Enrich existing members with data from Congress.gov API.
    
    Returns:
        Dict with enrichment results.
    """
    logger.info("Enriching existing members with Congress.gov API data")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        async with db_manager.session_factory() as session:
            # Initialize repositories
            member_repo = CongressMemberRepository(session)
            trade_repo = CongressionalTradeRepository(session)
            portfolio_repo = MemberPortfolioRepository(session)
            performance_repo = MemberPortfolioPerformanceRepository(session)
            
            # Initialize service with all required repositories
            api_service = CongressAPIService(
                member_repo=member_repo,
                trade_repo=trade_repo,
                portfolio_repo=portfolio_repo,
                performance_repo=performance_repo
            )
            
            # Get all members with bioguide IDs
            from domains.congressional.schemas import MemberQuery
            query = MemberQuery(limit=1000)
            members, _ = member_repo.list_members(query)
            
            enriched_count = 0
            failed_count = 0
            
            for member in members:
                if member.bioguide_id:
                    try:
                        result = await api_service.sync_member_by_bioguide_id(member.bioguide_id)
                        if result in ["updated", "created"]:
                            enriched_count += 1
                            logger.info(f"Enriched member: {member.full_name}")
                    except Exception as e:
                        logger.error(f"Failed to enrich member {member.full_name}: {e}")
                        failed_count += 1
                        continue
            
            # Commit changes
            await session.commit()
            
            return {
                "enriched": enriched_count,
                "failed": failed_count,
                "total_processed": enriched_count + failed_count
            }
            
    except Exception as e:
        logger.error(f"Error during member enrichment: {e}")
        raise
    finally:
        await db_manager.close()


def main():
    """Main function to run the sync script."""
    parser = argparse.ArgumentParser(description="Sync congressional members from Congress.gov API")
    parser.add_argument(
        "--action",
        choices=["sync-all", "sync-member", "sync-state", "test-api", "enrich-existing"],
        required=True,
        help="Action to perform"
    )
    parser.add_argument(
        "--bioguide-id",
        help="Bioguide ID for sync-member action"
    )
    parser.add_argument(
        "--state",
        help="State code for sync-state action"
    )
    
    args = parser.parse_args()
    
    # Check if API key is configured
    if not settings.CONGRESS_GOV_API_KEY:
        logger.error("CONGRESS_GOV_API_KEY environment variable is not set")
        return 1
    
    # Run the appropriate action
    if args.action == "sync-all":
        results = asyncio.run(sync_all_members())
        logger.info(f"Sync completed: {results}")
        
    elif args.action == "sync-member":
        if not args.bioguide_id:
            logger.error("--bioguide-id is required for sync-member action")
            return 1
        results = asyncio.run(sync_member_by_bioguide_id(args.bioguide_id))
        logger.info(f"Member sync completed: {results}")
        
    elif args.action == "sync-state":
        if not args.state:
            logger.error("--state is required for sync-state action")
            return 1
        results = asyncio.run(sync_members_by_state(args.state))
        logger.info(f"State sync completed: {results}")
        
    elif args.action == "test-api":
        success = asyncio.run(test_api_connection())
        if success:
            logger.info("API connection test passed")
            return 0
        else:
            logger.error("API connection test failed")
            return 1
            
    elif args.action == "enrich-existing":
        results = asyncio.run(enrich_existing_members())
        logger.info(f"Member enrichment completed: {results}")
    
    return 0


if __name__ == "__main__":
    exit(main())