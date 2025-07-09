#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to PostgreSQL.

This script migrates existing congressional trading data from the SQLite
database to the new PostgreSQL database structure.
"""

import os
import sys
import sqlite3
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.connection import init_database, db_manager
from database.models import (
    CongressMember, CongressionalTrade, Security, AssetType, 
    Exchange, Sector, IngestionLog
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SQLiteToPostgresMigrator:
    """Migrates data from SQLite to PostgreSQL."""
    
    def __init__(self, sqlite_path: str):
        self.sqlite_path = sqlite_path
        self.sqlite_conn = None
        self.stats = {
            'members_migrated': 0,
            'trades_migrated': 0,
            'securities_migrated': 0,
            'errors': 0
        }
    
    def connect_sqlite(self):
        """Connect to SQLite database."""
        try:
            self.sqlite_conn = sqlite3.connect(self.sqlite_path)
            logger.info(f"Connected to SQLite database: {self.sqlite_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            return False
    
    def get_sqlite_tables(self) -> List[str]:
        """Get list of tables in SQLite database."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Found SQLite tables: {tables}")
        return tables
    
    def migrate_congress_members(self):
        """Migrate congress members from existing trade data."""
        logger.info("Migrating congress members...")
        
        try:
            # Get unique members from SQLite data
            query = """
            SELECT DISTINCT Member as full_name
            FROM (
                SELECT Member FROM '2024FD' WHERE Member IS NOT NULL
                UNION
                SELECT Member FROM '2023FD' WHERE Member IS NOT NULL
                UNION
                SELECT Member FROM '2022FD' WHERE Member IS NOT NULL
                UNION
                SELECT Member FROM '2021FD' WHERE Member IS NOT NULL
                UNION
                SELECT Member FROM '2020FD' WHERE Member IS NOT NULL
            )
            """
            
            df = pd.read_sql(query, self.sqlite_conn)
            
            with db_manager.session_scope() as session:
                for _, row in df.iterrows():
                    full_name = row['full_name'].strip()
                    
                    # Skip empty or invalid names
                    if not full_name or len(full_name) < 2:
                        continue
                    
                    # Check if member already exists
                    existing = session.query(CongressMember).filter_by(full_name=full_name).first()
                    if existing:
                        continue
                    
                    # Parse name (basic parsing - can be improved)
                    name_parts = full_name.split(' ')
                    if len(name_parts) >= 2:
                        first_name = name_parts[0]
                        last_name = ' '.join(name_parts[1:])
                    else:
                        first_name = full_name
                        last_name = ''
                    
                    # Create member record
                    member = CongressMember(
                        first_name=first_name,
                        last_name=last_name,
                        full_name=full_name,
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    
                    session.add(member)
                    self.stats['members_migrated'] += 1
            
            logger.info(f"Migrated {self.stats['members_migrated']} congress members")
            
        except Exception as e:
            logger.error(f"Failed to migrate congress members: {e}")
            self.stats['errors'] += 1
    
    def migrate_securities(self):
        """Migrate securities from existing trade data."""
        logger.info("Migrating securities...")
        
        try:
            # Get unique tickers from SQLite data
            query = """
            SELECT DISTINCT Ticker as ticker, Asset as asset_description
            FROM (
                SELECT Ticker, Asset FROM '2024FD' WHERE Ticker IS NOT NULL AND Ticker != ''
                UNION
                SELECT Ticker, Asset FROM '2023FD' WHERE Ticker IS NOT NULL AND Ticker != ''
                UNION
                SELECT Ticker, Asset FROM '2022FD' WHERE Ticker IS NOT NULL AND Ticker != ''
                UNION
                SELECT Ticker, Asset FROM '2021FD' WHERE Ticker IS NOT NULL AND Ticker != ''
                UNION
                SELECT Ticker, Asset FROM '2020FD' WHERE Ticker IS NOT NULL AND Ticker != ''
            )
            """
            
            df = pd.read_sql(query, self.sqlite_conn)
            
            with db_manager.session_scope() as session:
                # Get default asset type and exchange
                default_asset_type = session.query(AssetType).filter_by(code='ST').first()
                default_exchange = session.query(Exchange).filter_by(code='NYSE').first()
                
                for _, row in df.iterrows():
                    ticker = row['ticker'].strip().upper()
                    
                    # Skip invalid tickers
                    if not ticker or len(ticker) > 20:
                        continue
                    
                    # Check if security already exists
                    existing = session.query(Security).filter_by(ticker=ticker).first()
                    if existing:
                        continue
                    
                    # Create security record
                    security = Security(
                        ticker=ticker,
                        name=f"{ticker} Corp",  # Placeholder name
                        asset_type_id=default_asset_type.id if default_asset_type else None,
                        exchange_id=default_exchange.id if default_exchange else None,
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    
                    session.add(security)
                    self.stats['securities_migrated'] += 1
            
            logger.info(f"Migrated {self.stats['securities_migrated']} securities")
            
        except Exception as e:
            logger.error(f"Failed to migrate securities: {e}")
            self.stats['errors'] += 1
    
    def migrate_congressional_trades(self, table_name: str):
        """Migrate congressional trades from a specific table."""
        logger.info(f"Migrating trades from table: {table_name}")
        
        try:
            # Read trades from SQLite
            df = pd.read_sql(f"SELECT * FROM '{table_name}'", self.sqlite_conn)
            
            trades_count = 0
            with db_manager.session_scope() as session:
                # Get member and security lookups
                members = {m.full_name: m.id for m in session.query(CongressMember).all()}
                securities = {s.ticker: s.id for s in session.query(Security).all()}
                
                for _, row in df.iterrows():
                    try:
                        # Get member ID
                        member_name = str(row.get('Member', '')).strip()
                        member_id = members.get(member_name)
                        if not member_id:
                            continue
                        
                        # Get security ID (optional)
                        ticker = str(row.get('Ticker', '')).strip().upper()
                        security_id = securities.get(ticker) if ticker else None
                        
                        # Parse dates
                        transaction_date = pd.to_datetime(row.get('Transaction Date'), errors='coerce')
                        notification_date = pd.to_datetime(row.get('Notification Date'), errors='coerce')
                        
                        if pd.isna(transaction_date) or pd.isna(notification_date):
                            continue
                        
                        # Parse amounts (convert range to min/max)
                        amount_str = str(row.get('Amount', ''))
                        amount_min, amount_max = self.parse_amount_range(amount_str)
                        
                        # Create trade record
                        trade = CongressionalTrade(
                            member_id=member_id,
                            security_id=security_id,
                            doc_id=str(row.get('DocID', '')),
                            owner=str(row.get('Owner', ''))[:10] if row.get('Owner') else None,
                            raw_asset_description=str(row.get('Asset', '')) if row.get('Asset') else None,
                            ticker=ticker if ticker else None,
                            transaction_type=str(row.get('Transaction Type', ''))[:2] if row.get('Transaction Type') else None,
                            transaction_date=transaction_date.date(),
                            notification_date=notification_date.date(),
                            amount_min=amount_min,
                            amount_max=amount_max,
                            filing_status=str(row.get('Filing Status', ''))[:1] if row.get('Filing Status') else None,
                            comment=str(row.get('Description', '')) if row.get('Description') else None,
                            created_at=datetime.utcnow()
                        )
                        
                        session.add(trade)
                        trades_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to migrate trade row: {e}")
                        self.stats['errors'] += 1
                        continue
            
            self.stats['trades_migrated'] += trades_count
            logger.info(f"Migrated {trades_count} trades from {table_name}")
            
        except Exception as e:
            logger.error(f"Failed to migrate trades from {table_name}: {e}")
            self.stats['errors'] += 1
    
    def parse_amount_range(self, amount_str: str) -> tuple:
        """Parse amount range string to min/max values in cents."""
        if not amount_str or amount_str == 'nan':
            return None, None
        
        # Common amount ranges in congressional filings
        amount_ranges = {
            '$1,001 - $15,000': (100100, 1500000),
            '$15,001 - $50,000': (1500100, 5000000),
            '$50,001 - $100,000': (5000100, 10000000),
            '$100,001 - $250,000': (10000100, 25000000),
            '$250,001 - $500,000': (25000100, 50000000),
            '$500,001 - $1,000,000': (50000100, 100000000),
            '$1,000,001 - $5,000,000': (100000100, 500000000),
            '$5,000,001 - $25,000,000': (500000100, 2500000000),
            '$25,000,001 - $50,000,000': (2500000100, 5000000000),
            '$50,000,000+': (5000000000, None)
        }
        
        # Try to match known ranges
        for range_str, (min_val, max_val) in amount_ranges.items():
            if range_str in amount_str:
                return min_val, max_val
        
        # Try to extract dollar amounts
        import re
        amounts = re.findall(r'\$[\d,]+', amount_str)
        if amounts:
            try:
                # Convert first amount to cents
                amount = int(amounts[0].replace('$', '').replace(',', '')) * 100
                return amount, amount
            except:
                pass
        
        return None, None
    
    def create_migration_log(self):
        """Create a log entry for this migration."""
        try:
            with db_manager.session_scope() as session:
                log_entry = IngestionLog(
                    source='sqlite_migration',
                    records_processed=self.stats['trades_migrated'] + self.stats['members_migrated'] + self.stats['securities_migrated'],
                    records_inserted=self.stats['trades_migrated'] + self.stats['members_migrated'] + self.stats['securities_migrated'],
                    records_failed=self.stats['errors'],
                    status='completed',
                    metadata={
                        'migration_stats': self.stats,
                        'sqlite_path': self.sqlite_path
                    },
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
                session.add(log_entry)
            
            logger.info("Migration log created")
            
        except Exception as e:
            logger.error(f"Failed to create migration log: {e}")
    
    def migrate_all(self):
        """Run complete migration process."""
        logger.info("Starting complete migration from SQLite to PostgreSQL...")
        
        if not self.connect_sqlite():
            return False
        
        try:
            # Get available tables
            tables = self.get_sqlite_tables()
            
            # Migrate reference data first
            self.migrate_congress_members()
            self.migrate_securities()
            
            # Migrate trade data from each year table
            trade_tables = [t for t in tables if t.endswith('FD')]
            for table in trade_tables:
                self.migrate_congressional_trades(table)
            
            # Create migration log
            self.create_migration_log()
            
            # Print summary
            logger.info("Migration completed!")
            logger.info(f"Summary: {self.stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
        
        finally:
            if self.sqlite_conn:
                self.sqlite_conn.close()

def main():
    """Main migration function."""
    # Initialize PostgreSQL connection
    init_database()
    
    # Find SQLite database
    sqlite_path = Path(__file__).parent.parent / 'data' / 'congress' / 'congress_trades.db'
    
    if not sqlite_path.exists():
        logger.error(f"SQLite database not found: {sqlite_path}")
        return False
    
    # Run migration
    migrator = SQLiteToPostgresMigrator(str(sqlite_path))
    return migrator.migrate_all()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 