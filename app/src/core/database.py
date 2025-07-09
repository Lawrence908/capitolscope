"""
Async database connection and session management for Supabase PostgreSQL.

This module provides database connection management using SQLAlchemy 2.0
with async support and proper connection pooling for Supabase.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

from core.config import settings

logger = structlog.get_logger(__name__)

class DatabaseManager:
    """Async database manager for Supabase PostgreSQL."""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self._initialized:
            logger.warning("Database already initialized")
            return
        
        try:
            # Create async engine with connection pooling
            self.engine = create_async_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=settings.DB_POOL_RECYCLE,
                echo=settings.DB_ECHO,
                # Connection arguments for better PostgreSQL performance
                connect_args={
                    "server_settings": {
                        "application_name": "capitolscope",
                        "timezone": "UTC",
                    },
                    "ssl": "require" if not settings.is_development else "prefer",
                }
            )
            
            # Create async session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False,
            )
            
            # Test connection
            await self.test_connection()
            
            self._initialized = True
            logger.info(
                "Database connection initialized successfully",
                database_url=settings.database_url.split("@")[1] if "@" in settings.database_url else "***",
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
            )
            
        except Exception as e:
            logger.error("Failed to initialize database connection", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close database engine and all connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database engine disposed")
        
        self._initialized = False
    
    async def test_connection(self) -> bool:
        """Test database connectivity."""
        if not self.engine:
            raise RuntimeError("Database not initialized")
        
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.scalar()
            
            logger.info("Database connection test successful")
            return True
            
        except Exception as e:
            logger.error("Database connection test failed", error=str(e))
            raise
    
    def get_session(self) -> AsyncSession:
        """Get a new async database session."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.session_factory()
    
    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provide a transactional scope around a series of operations.
        
        Usage:
            async with db_manager.session_scope() as session:
                await session.execute(...)
                # Auto-commit on success, auto-rollback on exception
        """
        async with self.get_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI dependency injection.
    
    Usage in FastAPI:
        @app.get("/trades")
        async def get_trades(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(...)
            return result.scalars().all()
    """
    async with db_manager.session_scope() as session:
        yield session


async def init_database() -> None:
    """Initialize the database connection."""
    await db_manager.initialize()


async def close_database() -> None:
    """Close the database connection."""
    await db_manager.close()


async def execute_sql(sql: str, params: dict = None) -> None:
    """Execute a SQL statement directly."""
    try:
        async with db_manager.session_scope() as session:
            result = await session.execute(text(sql), params or {})
            return result
    except Exception as e:
        logger.error("Failed to execute SQL", sql=sql, error=str(e))
        raise


# Health check function for the database
async def check_database_health() -> dict:
    """Check database health for monitoring."""
    try:
        if not db_manager._initialized:
            return {
                "status": "unhealthy",
                "error": "Database not initialized"
            }
        
        # Test basic connectivity
        start_time = time.time()
        await db_manager.test_connection()
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Get connection pool status
        pool = db_manager.engine.pool
        pool_status = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
        }
        
        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "pool": pool_status,
        }
        
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }


import time  # Import needed for health check function 