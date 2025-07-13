"""
Async database connection and session management for Supabase PostgreSQL.

This module provides database connection management using SQLAlchemy 2.0
with async support and Supabase's session pooler for optimal performance.

Connection Details:
- Uses Supabase Session Pooler (aws-0-ca-central-1.pooler.supabase.com:5432)
- NullPool for async engine compatibility
- Proper SSL configuration for production
- Health check monitoring included
"""

import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional

import structlog
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import SQLAlchemyError

from core.config import settings

logger = structlog.get_logger(__name__)

class DatabaseManager:
    """Async database manager for Supabase PostgreSQL."""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self.sync_engine: Optional[object] = None
        self.sync_session_factory: Optional[sessionmaker[Session]] = None
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
                poolclass=NullPool,  # NullPool is recommended for async engines
                echo=settings.DATABASE_ECHO,
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
            
            # Create synchronous engine and session factory for import scripts
            sync_url = settings.database_url.replace("+asyncpg://", "://")
            self.sync_engine = create_engine(
                sync_url,
                echo=settings.DATABASE_ECHO,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            self.sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                class_=Session,
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
                pool_type="NullPool",
                echo=settings.DATABASE_ECHO,
            )
            
        except Exception as e:
            logger.error("Failed to initialize database connection", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close database engine and all connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database engine disposed")
        
        if self.sync_engine:
            self.sync_engine.dispose()
            logger.info("Synchronous database engine disposed")
        
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
    
    def get_sync_session(self) -> Session:
        """Get a new synchronous database session for import scripts."""
        if not self.sync_session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.sync_session_factory()
    
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
    
    @contextmanager
    def sync_session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a synchronous transactional scope around a series of operations.
        
        Usage:
            with db_manager.sync_session_scope() as session:
                session.execute(...)
                # Auto-commit on success, auto-rollback on exception
        """
        session = self.get_sync_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


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


def get_sync_db_session():
    """
    Synchronous dependency function for import scripts.
    
    Usage in import scripts:
        with get_sync_db_session() as session:
            crud = CongressMemberCRUD(session)
            crud.create(...)
    """
    return db_manager.sync_session_scope()


async def execute_sql(sql: str, params: dict = None) -> None:
    """Execute a SQL statement directly."""
    try:
        async with db_manager.session_scope() as session:
            result = await session.execute(text(sql), params or {})
            return result
    except Exception as e:
        logger.error("Failed to execute SQL", sql=sql, error=str(e))
        raise


async def init_database() -> None:
    """Initialize the database connection."""
    await db_manager.initialize()


async def close_database() -> None:
    """Close the database connection."""
    await db_manager.close()


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
        
        # Get connection pool status (NullPool doesn't have these methods)
        pool_status = {
            "type": "NullPool",
            "note": "NullPool creates new connections for each request"
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