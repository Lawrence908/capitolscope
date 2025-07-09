"""
Async database connection and session management for CapitolScope.

This module provides async database connectivity using SQLAlchemy with Supabase PostgreSQL,
including connection pooling, session management, and health checks.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from core.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages async database connections and sessions."""

    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_maker: Optional[async_sessionmaker] = None
        self._is_connected = False

    async def initialize(self) -> None:
        """Initialize database connection and session factory."""
        try:
            # Build connection string
            connection_string = self._build_connection_string()
            
            # Create async engine with connection pooling
            self.engine = create_async_engine(
                connection_string,
                # Connection pool settings
                poolclass=QueuePool,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,
                pool_recycle=3600,  # Recycle connections after 1 hour
                
                # Async settings
                echo=settings.DATABASE_ECHO,
                future=True,
                
                # Connection arguments
                connect_args={
                    "server_settings": {
                        "application_name": "capitolscope",
                        "jit": "off",  # Disable JIT for better connection stability
                    }
                }
            )
            
            # Create session factory
            self.session_maker = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
            
            # Test connection
            await self._test_connection()
            self._is_connected = True
            
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise

    def _build_connection_string(self) -> str:
        """Build async PostgreSQL connection string."""
        # Use asyncpg driver for async PostgreSQL
        return (
            f"postgresql+asyncpg://"
            f"{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}@"
            f"{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/"
            f"{settings.DATABASE_NAME}"
        )

    async def _test_connection(self) -> None:
        """Test database connection."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
                logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise

    async def close(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            self._is_connected = False
            logger.info("Database connections closed")

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._is_connected

    async def get_session(self) -> AsyncSession:
        """Get async database session."""
        if not self.session_maker:
            raise RuntimeError("Database not initialized")
        return self.session_maker()

    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional scope around database operations."""
        if not self.session_maker:
            raise RuntimeError("Database not initialized")
        
        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> dict:
        """Perform database health check."""
        health_info = {
            "connected": self._is_connected,
            "engine": self.engine is not None,
            "session_maker": self.session_maker is not None,
        }
        
        if not self._is_connected:
            return {**health_info, "status": "disconnected"}
        
        try:
            async with self.session_scope() as session:
                # Test query
                result = await session.execute(text("SELECT version()"))
                version = result.scalar()
                
                # Pool statistics
                pool_info = {}
                if self.engine and hasattr(self.engine.pool, 'size'):
                    pool_info = {
                        "pool_size": self.engine.pool.size(),
                        "checked_in": self.engine.pool.checkedin(),
                        "checked_out": self.engine.pool.checkedout(),
                        "invalidated": self.engine.pool.invalidated(),
                    }
                
                return {
                    **health_info,
                    "status": "healthy",
                    "version": version,
                    "pool": pool_info,
                }
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                **health_info,
                "status": "unhealthy",
                "error": str(e),
            }

    async def execute_raw_query(self, query: str, params: Optional[dict] = None) -> dict:
        """Execute raw SQL query (for admin/debugging purposes)."""
        if not self.engine:
            raise RuntimeError("Database not initialized")
        
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text(query), params or {})
                
                # Handle different result types
                if result.returns_rows:
                    rows = result.fetchall()
                    return {
                        "success": True,
                        "rows": [dict(row._mapping) for row in rows],
                        "row_count": len(rows),
                    }
                else:
                    return {
                        "success": True,
                        "rows_affected": result.rowcount,
                    }
                    
        except Exception as e:
            logger.error(f"Raw query execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session."""
    async with db_manager.session_scope() as session:
        yield session


# Alternative dependency that returns session directly
async def get_db_session() -> AsyncSession:
    """Get database session directly."""
    return await db_manager.get_session()


# Startup and shutdown event handlers
async def startup_database():
    """Initialize database connection on startup."""
    await db_manager.initialize()


async def shutdown_database():
    """Close database connections on shutdown."""
    await db_manager.close()


# Utility functions
async def check_database_connection() -> bool:
    """Check if database connection is healthy."""
    try:
        health = await db_manager.health_check()
        return health["status"] == "healthy"
    except Exception:
        return False


async def get_database_info() -> dict:
    """Get database connection information."""
    if not db_manager.is_connected:
        return {"status": "disconnected"}
    
    try:
        async with db_manager.session_scope() as session:
            # Get database version
            version_result = await session.execute(text("SELECT version()"))
            version = version_result.scalar()
            
            # Get current database name
            db_result = await session.execute(text("SELECT current_database()"))
            current_db = db_result.scalar()
            
            # Get connection count
            connections_result = await session.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
            )
            connection_count = connections_result.scalar()
            
            return {
                "status": "connected",
                "version": version,
                "database": current_db,
                "connections": connection_count,
                "host": settings.DATABASE_HOST,
                "port": settings.DATABASE_PORT,
                "user": settings.DATABASE_USER,
                "pool_size": settings.DATABASE_POOL_SIZE,
            }
            
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {"status": "error", "error": str(e)}


# Context manager for database transactions
@asynccontextmanager
async def database_transaction():
    """Context manager for explicit database transactions."""
    async with db_manager.session_scope() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# Supabase integration utilities
class SupabaseIntegration:
    """Utilities for Supabase-specific features."""
    
    @staticmethod
    async def get_supabase_auth_user(jwt_token: str) -> Optional[dict]:
        """Get user info from Supabase auth JWT token."""
        try:
            # This would typically use the Supabase client
            # For now, we'll just return None and implement later
            return None
        except Exception as e:
            logger.error(f"Failed to get Supabase auth user: {e}")
            return None
    
    @staticmethod
    async def create_rls_policy(table_name: str, policy_name: str, policy_definition: str) -> bool:
        """Create Row Level Security policy (admin function)."""
        try:
            query = f"""
            CREATE POLICY {policy_name} ON {table_name}
            {policy_definition}
            """
            result = await db_manager.execute_raw_query(query)
            return result["success"]
        except Exception as e:
            logger.error(f"Failed to create RLS policy: {e}")
            return False


# Export public interface
__all__ = [
    "db_manager",
    "get_db",
    "get_db_session",
    "startup_database",
    "shutdown_database",
    "check_database_connection",
    "get_database_info",
    "database_transaction",
    "SupabaseIntegration",
    "DatabaseManager",
] 