#!/usr/bin/env python3
"""
Database setup script for CapitolScope.

This script tests the database connection, creates initial migrations,
and sets up the database for our domain-driven architecture.
"""

import asyncio
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

# Add src directory to path
src_path = Path(__file__).parent.parent / "app" / "src"
sys.path.insert(0, str(src_path))

from core.config import settings
from core.database import DatabaseManager
from core.logging import get_logger

logger = get_logger(__name__)


class DatabaseSetup:
    """Database setup and migration manager."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.project_root = Path(__file__).parent.parent
    
    async def test_connection(self) -> bool:
        """Test database connection."""
        logger.info("🔗 Testing database connection...")
        
        try:
            await self.db_manager.initialize()
            await self.db_manager.test_connection()
            logger.info("✅ Database connection successful!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
        finally:
            await self.db_manager.close()
    
    def check_environment(self) -> Dict[str, Any]:
        """Check environment configuration."""
        logger.info("🔍 Checking environment configuration...")
        
        config_status = {
            "database_url": bool(settings.database_url),
            "supabase_url": bool(settings.SUPABASE_URL),
            "supabase_key": bool(settings.SUPABASE_KEY),
            "supabase_service_role_key": bool(settings.SUPABASE_SERVICE_ROLE_KEY),
            "jwt_secret": bool(settings.SUPABASE_JWT_SECRET),
            "environment": settings.ENVIRONMENT,
        }
        
        # Print configuration status
        for key, value in config_status.items():
            status = "✅" if value else "❌"
            logger.info(f"  {status} {key}: {'OK' if value else 'MISSING'}")
        
        return config_status
    
    def create_initial_migration(self) -> bool:
        """Create initial Alembic migration."""
        logger.info("📝 Creating initial database migration...")
        
        try:
            # Change to project root directory
            original_cwd = Path.cwd()
            
            try:
                import os
                os.chdir(self.project_root)
                
                # Create initial migration
                result = subprocess.run([
                    "alembic", "revision", "--autogenerate", 
                    "-m", "Initial migration: base, securities, congressional, users domains"
                ], capture_output=True, text=True, check=True)
                
                logger.info("✅ Initial migration created successfully!")
                logger.info(f"Migration output: {result.stdout}")
                return True
                
            finally:
                os.chdir(original_cwd)
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to create migration: {e}")
            logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error creating migration: {e}")
            return False
    
    def run_migrations(self) -> bool:
        """Run database migrations."""
        logger.info("🚀 Running database migrations...")
        
        try:
            # Change to project root directory
            original_cwd = Path.cwd()
            
            try:
                import os
                os.chdir(self.project_root)
                
                # Run migrations
                result = subprocess.run([
                    "alembic", "upgrade", "head"
                ], capture_output=True, text=True, check=True)
                
                logger.info("✅ Migrations completed successfully!")
                logger.info(f"Migration output: {result.stdout}")
                return True
                
            finally:
                os.chdir(original_cwd)
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to run migrations: {e}")
            logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error running migrations: {e}")
            return False
    
    def check_migration_status(self) -> bool:
        """Check current migration status."""
        logger.info("📊 Checking migration status...")
        
        try:
            # Change to project root directory
            original_cwd = Path.cwd()
            
            try:
                import os
                os.chdir(self.project_root)
                
                # Check current migration status
                result = subprocess.run([
                    "alembic", "current"
                ], capture_output=True, text=True, check=True)
                
                logger.info("✅ Migration status:")
                logger.info(f"Current revision: {result.stdout.strip() or 'No migrations applied'}")
                
                # Show migration history
                history_result = subprocess.run([
                    "alembic", "history", "--verbose"
                ], capture_output=True, text=True, check=True)
                
                logger.info("Migration history:")
                logger.info(history_result.stdout)
                return True
                
            finally:
                os.chdir(original_cwd)
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to check migration status: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error checking migration status: {e}")
            return False
    
    async def setup_database(self) -> bool:
        """Complete database setup process."""
        logger.info("🏗️ Starting database setup for CapitolScope...")
        
        # Step 1: Check environment
        config_status = self.check_environment()
        if not all(config_status[key] for key in ["database_url", "supabase_url", "supabase_key", "supabase_service_role_key", "jwt_secret"]):
            logger.error("❌ Missing required environment variables. Please check your .env file.")
            return False
        
        # Step 2: Test connection
        if not await self.test_connection():
            return False
        
        # Step 3: Check if migrations exist
        migrations_dir = self.project_root / "alembic" / "versions"
        migrations_dir.mkdir(parents=True, exist_ok=True)
        
        migration_files = list(migrations_dir.glob("*.py"))
        
        if not migration_files:
            logger.info("📝 No migrations found. Creating initial migration...")
            if not self.create_initial_migration():
                return False
        else:
            logger.info(f"📁 Found {len(migration_files)} existing migration(s)")
        
        # Step 4: Run migrations
        if not self.run_migrations():
            return False
        
        # Step 5: Check final status
        if not self.check_migration_status():
            return False
        
        logger.info("🎉 Database setup completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. 🚀 Start the FastAPI application: cd app && python -m uvicorn main:app --reload")
        logger.info("2. 📖 Access API documentation: http://localhost:8000/docs")
        logger.info("3. 🧪 Test the endpoints with some data")
        
        return True
    
    def print_domain_summary(self):
        """Print summary of implemented domains."""
        logger.info("\n📊 Domain Architecture Summary:")
        logger.info("=" * 50)
        
        domains = [
            ("🏗️ Base Domain", "Core utilities, logging, common schemas"),
            ("📈 Securities Domain", "Stocks, prices, exchanges (CAP-24, CAP-25)"),
            ("🏛️ Congressional Domain", "Members, trades, portfolios (CAP-10, CAP-11)"),
            ("👤 Users Domain", "Authentication, subscriptions, preferences"),
        ]
        
        for domain_name, description in domains:
            logger.info(f"  {domain_name}: {description}")
        
        logger.info("\n🔗 Key Relationships:")
        logger.info("  • CongressionalTrade → Security (foreign key)")
        logger.info("  • CongressionalTrade → CongressMember (foreign key)")
        logger.info("  • MemberPortfolio → Security + CongressMember")
        logger.info("  • User → UserPreferences, UserWatchlist, UserAlert")


async def main():
    """Main setup function."""
    setup = DatabaseSetup()
    
    # Print domain summary
    setup.print_domain_summary()
    
    # Run database setup
    success = await setup.setup_database()
    
    if success:
        logger.info("✅ Database setup completed successfully!")
        return 0
    else:
        logger.error("❌ Database setup failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main()) 