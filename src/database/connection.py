"""
Database connection utilities for CapitolScope.

This module provides database connection management, session handling,
and connection pooling for PostgreSQL using SQLAlchemy.
"""

import os
import logging
from typing import Generator, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration settings."""
    
    def __init__(self):
        self.database_url = os.getenv(
            'DATABASE_URL', 
            'postgresql://capitolscope:dev_password_change_me@localhost:5432/capitolscope'
        )
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '10'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '20'))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))
        self.echo = os.getenv('DB_ECHO', 'False').lower() == 'true'

class DatabaseManager:
    """
    Database manager for handling connections and sessions.
    
    This class provides a centralized way to manage database connections,
    session creation, and connection pooling.
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.engine = None
        self.session_factory = None
        
    def initialize(self):
        """Initialize the database engine and session factory."""
        try:
            # Create engine with connection pooling
            self.engine = create_engine(
                self.config.database_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=self.config.echo,
                # Connection arguments for better PostgreSQL performance
                connect_args={
                    "options": "-c timezone=utc",
                    "application_name": "capitolscope"
                }
            )
            
            # Create session factory
            self.session_factory = sessionmaker(bind=self.engine)
            
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.session_factory()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        
        Usage:
            with db_manager.session_scope() as session:
                session.add(some_object)
                # Auto-commit on success, auto-rollback on exception
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            with self.session_scope() as session:
                session.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def close(self):
        """Close the database engine."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database engine disposed")

# Global database manager instance
db_manager = DatabaseManager()

def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI or other frameworks.
    
    Usage in FastAPI:
        @app.get("/trades")
        def get_trades(session: Session = Depends(get_db_session)):
            return session.query(CongressionalTrade).all()
    """
    with db_manager.session_scope() as session:
        yield session

def init_database():
    """Initialize the database connection."""
    db_manager.initialize()

def test_database_connection():
    """Test the database connection."""
    return db_manager.test_connection()

def close_database():
    """Close the database connection."""
    db_manager.close()

# Connection utilities for direct use
def execute_sql_file(file_path: str):
    """Execute SQL commands from a file."""
    try:
        with open(file_path, 'r') as file:
            sql_content = file.read()
        
        with db_manager.session_scope() as session:
            # Split on semicolons and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            for statement in statements:
                session.execute(text(statement))
        
        logger.info(f"Successfully executed SQL file: {file_path}")
        
    except Exception as e:
        logger.error(f"Failed to execute SQL file {file_path}: {e}")
        raise

def execute_sql(sql: str, params: dict = None):
    """Execute a SQL statement."""
    try:
        with db_manager.session_scope() as session:
            result = session.execute(text(sql), params or {})
            return result
    except Exception as e:
        logger.error(f"Failed to execute SQL: {e}")
        raise 