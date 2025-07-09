#!/usr/bin/env python3
"""
Database initialization script for CapitolScope.

This script initializes the PostgreSQL database, creates all tables,
and populates initial reference data.
"""

import os
import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.connection import init_database, test_database_connection, execute_sql_file
from database.models import Base
from database.connection import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_tables():
    """Create all database tables using SQLAlchemy models."""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=db_manager.engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False

def populate_reference_data():
    """Populate reference data (asset types, exchanges, sectors)."""
    try:
        logger.info("Populating reference data...")
        
        # Path to the schema file with initial data
        schema_file = Path(__file__).parent.parent / 'schema' / 'database_schema.sql'
        
        if schema_file.exists():
            # Execute only the INSERT statements from the schema file
            with open(schema_file, 'r') as f:
                content = f.read()
            
            # Extract INSERT statements
            lines = content.split('\n')
            insert_statements = []
            for line in lines:
                line = line.strip()
                if line.startswith('INSERT INTO'):
                    # Find the complete INSERT statement (may span multiple lines)
                    statement = line
                    idx = lines.index(line.strip('\r'))
                    while not statement.rstrip().endswith(';'):
                        idx += 1
                        if idx < len(lines):
                            statement += ' ' + lines[idx].strip()
                        else:
                            break
                    insert_statements.append(statement)
            
            # Execute INSERT statements
            with db_manager.session_scope() as session:
                for statement in insert_statements:
                    if statement.strip():
                        try:
                            session.execute(statement)
                            logger.info(f"Executed: {statement[:50]}...")
                        except Exception as e:
                            logger.warning(f"Insert statement failed (may already exist): {e}")
                            
        logger.info("Reference data populated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to populate reference data: {e}")
        return False

def verify_database():
    """Verify database setup by running some basic queries."""
    try:
        logger.info("Verifying database setup...")
        
        with db_manager.session_scope() as session:
            # Check asset types
            result = session.execute("SELECT COUNT(*) FROM asset_types")
            asset_count = result.scalar()
            logger.info(f"Asset types count: {asset_count}")
            
            # Check exchanges
            result = session.execute("SELECT COUNT(*) FROM exchanges")
            exchange_count = result.scalar()
            logger.info(f"Exchanges count: {exchange_count}")
            
            # Check sectors
            result = session.execute("SELECT COUNT(*) FROM sectors")
            sector_count = result.scalar()
            logger.info(f"Sectors count: {sector_count}")
            
            if asset_count > 0 and exchange_count > 0 and sector_count > 0:
                logger.info("Database verification successful")
                return True
            else:
                logger.warning("Database verification failed - missing reference data")
                return False
                
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False

def main():
    """Main initialization function."""
    logger.info("Starting CapitolScope database initialization...")
    
    try:
        # Initialize database connection
        logger.info("Initializing database connection...")
        init_database()
        
        # Test connection
        if not test_database_connection():
            logger.error("Database connection test failed")
            return False
        
        # Create tables
        if not create_tables():
            logger.error("Table creation failed")
            return False
        
        # Populate reference data
        if not populate_reference_data():
            logger.error("Reference data population failed")
            return False
        
        # Verify setup
        if not verify_database():
            logger.error("Database verification failed")
            return False
        
        logger.info("✅ Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 