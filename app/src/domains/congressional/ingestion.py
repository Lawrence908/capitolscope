"""
Congressional domain data ingestion module.

This module handles importing congressional trading data from CSV files,
extracting member information, and parsing PDF files for new data.
Supports CAP-10 (Transaction List) and CAP-11 (Member Profiles).
"""

import os
import pandas as pd
import sqlite3
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from core.logging import get_logger
from core.config import settings
from domains.congressional.models import CongressMember, CongressionalTrade, MemberPortfolio
from domains.congressional.crud import CongressMemberCRUD, CongressionalTradeCRUD
from domains.congressional.schemas import CongressMemberCreate, CongressionalTradeCreate
from domains.securities.models import Security
from domains.securities.crud import SecurityCRUD

logger = get_logger(__name__)


class CongressionalDataIngester:
    """
    Congressional trading data ingestion service for CapitolScope.
    
    Handles importing data from CSV files, SQLite databases, and extracting
    member information for profile creation.
    """
    
    def __init__(self, session):
        """
        Initialize the ingester with a database session.
        
        Args:
            session: Either AsyncSession (for async operations) or Session (for sync operations)
        """
        self.session = session
        self.member_crud = CongressMemberCRUD(session)
        self.trade_crud = CongressionalTradeCRUD(session)
        self.security_crud = SecurityCRUD(session)
        
        # Validation system (optional)
        self.validator = None
        
        # Asset type mapping from the original script
        self.asset_type_dict = {
            "4K": "401K and Other Non-Federal Retirement Accounts",
            "5C": "529 College Savings Plan",
            "5F": "529 Portfolio",
            "5P": "529 Prepaid Tuition Plan",
            "AB": "Asset-Backed Securities",
            "BA": "Bank Accounts, Money Market Accounts and CDs",
            "BK": "Brokerage Accounts",
            "CO": "Collectibles",
            "CS": "Corporate Securities (Bonds and Notes)",
            "CT": "Cryptocurrency",
            "DB": "Defined Benefit Pension",
            "DO": "Debts Owed to the Filer",
            "DS": "Delaware Statutory Trust",
            "EF": "Exchange Traded Funds (ETF)",
            "EQ": "Excepted/Qualified Blind Trust",
            "ET": "Exchange Traded Notes",
            "FA": "Farms",
            "FE": "Foreign Exchange Position (Currency)",
            "FN": "Fixed Annuity",
            "FU": "Futures",
            "GS": "Government Securities and Agency Debt",
            "HE": "Hedge Funds & Private Equity Funds (EIF)",
            "HN": "Hedge Funds & Private Equity Funds (non-EIF)",
            "IC": "Investment Club",
            "IH": "IRA (Held in Cash)",
            "IP": "Intellectual Property & Royalties",
            "IR": "IRA",
            "MA": "Managed Accounts (e.g., SMA and UMA)",
            "MF": "Mutual Funds",
            "MO": "Mineral/Oil/Solar Energy Rights",
            "OI": "Ownership Interest (Holding Investments)",
            "OL": "Ownership Interest (Engaged in a Trade or Business)",
            "OP": "Options",
            "OT": "Other",
            "PE": "Pensions",
            "PM": "Precious Metals",
            "PS": "Stock (Not Publicly Traded)",
            "RE": "Real Estate Invest. Trust (REIT)",
            "RP": "Real Property",
            "RS": "Restricted Stock Units (RSUs)",
            "SA": "Stock Appreciation Right",
            "ST": "Stocks (including ADRs)",
            "TR": "Trust",
            "VA": "Variable Annuity",
            "VI": "Variable Insurance",
            "WU": "Whole/Universal Insurance"
        }
    
    def set_validator(self, validator):
        """
        Set the validator for data quality validation.
        
        Args:
            validator: CongressionalDataValidator instance
        """
        self.validator = validator
        logger.info("Data validator set for ingestion")
    
    async def import_congressional_data_from_csvs(self, data_directory: str) -> Dict[str, int]:
        """
        Import congressional trading data from CSV files.
        
        Args:
            data_directory: Path to directory containing CSV files (2014FD.csv, 2015FD.csv, etc.)
            
        Returns:
            Dict with import statistics
        """
        data_path = Path(data_directory)
        if not data_path.exists():
            raise ValueError(f"Data directory does not exist: {data_directory}")
        
        logger.info(f"Starting congressional data import from {data_directory}")
        
        # Find all FD CSV files
        csv_files = list(data_path.glob("*FD.csv"))
        csv_files = [f for f in csv_files if not f.name.endswith("_old.csv") and not f.name.endswith("_docIDlist.csv")]
        
        total_members = 0
        total_trades = 0
        failed_trades = 0
        
        for csv_file in sorted(csv_files):
            logger.info(f"Processing {csv_file.name}...")
            
            try:
                # Read CSV file
                df = pd.read_csv(csv_file)
                logger.info(f"Loaded {len(df)} records from {csv_file.name}")
                
                # Extract and create members from this file
                members_created = await self._extract_and_create_members(df)
                total_members += members_created
                
                # Import trades
                trades_created, trades_failed = await self._import_trades_from_dataframe(df, csv_file.stem)
                total_trades += trades_created
                failed_trades += trades_failed
                
                logger.info(f"Completed {csv_file.name}: {members_created} members, {trades_created} trades")
                
            except Exception as e:
                logger.error(f"Failed to process {csv_file.name}: {e}")
                continue
        
        await self.session.commit()
        
        result = {
            "csv_files_processed": len(csv_files),
            "total_members": total_members,
            "total_trades": total_trades,
            "failed_trades": failed_trades
        }
        
        logger.info(f"Congressional data import complete: {result}")
        return result
    
    def import_congressional_data_from_csvs_sync(self, data_directory: str) -> Dict[str, int]:
        """
        Synchronous version of import_congressional_data_from_csvs for use with sync sessions.
        
        Args:
            data_directory: Path to directory containing CSV files (2014FD.csv, 2015FD.csv, etc.)
            
        Returns:
            Dict with import statistics
        """
        data_path = Path(data_directory)
        if not data_path.exists():
            raise ValueError(f"Data directory does not exist: {data_directory}")
        
        logger.info(f"Starting congressional data import from {data_directory}")
        
        # Find all FD CSV files
        csv_files = list(data_path.glob("*FD.csv"))
        csv_files = [f for f in csv_files if not f.name.endswith("_old.csv") and not f.name.endswith("_docIDlist.csv")]
        
        total_members = 0
        total_trades = 0
        failed_trades = 0
        
        for csv_file in sorted(csv_files):
            logger.info(f"Processing {csv_file.name}...")
            
            try:
                # Read CSV file
                df = pd.read_csv(csv_file)
                logger.info(f"Loaded {len(df)} records from {csv_file.name}")
                
                # Extract and create members from this file
                members_created = self._extract_and_create_members_sync(df)
                total_members += members_created
                
                # Import trades
                trades_created, trades_failed = self._import_trades_from_dataframe_sync(df, csv_file.stem)
                total_trades += trades_created
                failed_trades += trades_failed
                
                logger.info(f"Completed {csv_file.name}: {members_created} members, {trades_created} trades")
                
            except Exception as e:
                logger.error(f"Failed to process {csv_file.name}: {e}")
                continue
        
        self.session.commit()
        
        result = {
            "csv_files_processed": len(csv_files),
            "total_members": total_members,
            "total_trades": total_trades,
            "failed_trades": failed_trades
        }
        
        logger.info(f"Congressional data import complete: {result}")
        return result
    
    async def import_from_sqlite_database(self, sqlite_path: str) -> Dict[str, int]:
        """
        Import congressional trading data from existing SQLite database.
        
        Args:
            sqlite_path: Path to the SQLite database file
            
        Returns:
            Dict with import statistics
        """
        sqlite_file = Path(sqlite_path)
        if not sqlite_file.exists():
            raise ValueError(f"SQLite database does not exist: {sqlite_path}")
        
        logger.info(f"Starting import from SQLite database: {sqlite_path}")
        
        # Connect to SQLite database
        conn = sqlite3.connect(sqlite_path)
        
        try:
            # Get list of tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%FD';")
            tables = [row[0] for row in cursor.fetchall()]
            
            logger.info(f"Found {len(tables)} FD tables in SQLite database")
            
            total_members = 0
            total_trades = 0
            failed_trades = 0
            
            for table_name in sorted(tables):
                logger.info(f"Processing table {table_name}...")
                
                try:
                    # Read table into DataFrame
                    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                    logger.info(f"Loaded {len(df)} records from {table_name}")
                    
                    # Extract and create members
                    members_created = await self._extract_and_create_members(df)
                    total_members += members_created
                    
                    # Import trades
                    trades_created, trades_failed = await self._import_trades_from_dataframe(df, table_name)
                    total_trades += trades_created
                    failed_trades += trades_failed
                    
                    logger.info(f"Completed {table_name}: {members_created} members, {trades_created} trades")
                    
                except Exception as e:
                    logger.error(f"Failed to process table {table_name}: {e}")
                    continue
            
            await self.session.commit()
            
            result = {
                "tables_processed": len(tables),
                "total_members": total_members,
                "total_trades": total_trades,
                "failed_trades": failed_trades
            }
            
            logger.info(f"SQLite import complete: {result}")
            return result
            
        finally:
            conn.close()
    
    async def _extract_and_create_members(self, df: pd.DataFrame) -> int:
        """
        Extract unique members from DataFrame and create member records.
        
        Args:
            df: DataFrame containing congressional trade data
            
        Returns:
            Number of new members created
        """
        if 'Member' not in df.columns:
            logger.warning("No 'Member' column found in DataFrame")
            return 0
        
        # Get unique member names
        unique_members = df['Member'].dropna().unique()
        logger.info(f"Found {len(unique_members)} unique members in data")
        
        created_count = 0
        
        for member_name in unique_members:
            if not member_name or pd.isna(member_name):
                continue
                
            try:
                # Parse member name (assume format: "Last, First" or just "Last")
                name_parts = member_name.strip().split(',')
                if len(name_parts) >= 2:
                    last_name = name_parts[0].strip()
                    first_name = name_parts[1].strip()
                else:
                    last_name = member_name.strip()
                    first_name = ""
                
                # Check if member already exists
                existing = await self.member_crud.get_by_name(last_name, first_name)
                if existing:
                    continue
                
                # Create new member record
                member_data = CongressMemberCreate(
                    first_name=first_name or "Unknown",
                    last_name=last_name,
                    full_name=member_name.strip(),
                    # These will be populated later from external APIs
                    chamber="House",  # Default to House, will be updated later
                    party="I",  # Default to Independent, will be updated later
                    state="DC",  # Default to DC, will be updated later
                    district=None,
                    is_active=True
                )
                
                member = await self.member_crud.create(member_data)
                created_count += 1
                
                logger.debug(f"Created member: {member_name}")
                
            except Exception as e:
                logger.error(f"Failed to create member {member_name}: {e}")
                continue
        
        logger.info(f"Created {created_count} new members")
        return created_count
    
    def _extract_and_create_members_sync(self, df: pd.DataFrame) -> int:
        """
        Synchronous version of _extract_and_create_members for use with sync sessions.
        Uses UPSERT pattern to preserve existing member data like party, chamber, state.
        
        Args:
            df: DataFrame containing congressional trade data
            
        Returns:
            Number of new members created
        """
        if 'Member' not in df.columns:
            logger.warning("No 'Member' column found in DataFrame")
            return 0
        
        # Check if we have FirstName and LastName columns (new format)
        has_separate_names = 'FirstName' in df.columns and 'LastName' in df.columns
        has_prefix = 'Prefix' in df.columns
        
        if has_separate_names:
            logger.info("Using FirstName/LastName columns for member extraction")
        else:
            logger.info("Using Member column parsing for member extraction")
        
        # Track member names to ensure consistency
        member_names = {}  # {member_key: (prefix, first_name, last_name, full_name)}
        
        # Get unique member names
        unique_members = df['Member'].dropna().unique()
        logger.info(f"Found {len(unique_members)} unique members in data")
        
        created_count = 0
        
        for member_name in unique_members:
            member_name = str(member_name).strip()
            if not member_name or member_name == 'nan':
                continue
            
            try:
                # Extract name components based on available columns
                if has_separate_names:
                    # Find the best row with complete data for this member
                    member_rows = df[df['Member'] == member_name]
                    
                    best_entry = None
                    for _, row in member_rows.iterrows():
                        if pd.notna(row.get('FirstName')) and pd.notna(row.get('LastName')):
                            best_entry = row
                            break
                    
                    if best_entry is not None:
                        prefix = str(best_entry.get('Prefix', '')).strip() if has_prefix and pd.notna(best_entry.get('Prefix')) else ""
                        first_name = str(best_entry['FirstName']).strip()
                        last_name = str(best_entry['LastName']).strip()
                        if prefix:
                            full_name = f"{prefix} {first_name} {last_name}".strip()
                        else:
                            full_name = f"{first_name} {last_name}".strip()
                        member_names[member_name] = (prefix, first_name, last_name, full_name)
                    else:
                        first_name, last_name = self._parse_name_from_member(member_name)
                        full_name = f"{first_name} {last_name}".strip()
                        member_names[member_name] = ("", first_name, last_name, full_name)
                else:
                    first_name, last_name = self._parse_name_from_member(member_name)
                    full_name = f"{first_name} {last_name}".strip()
                    member_names[member_name] = ("", first_name, last_name, full_name)

                prefix, first_name, last_name, full_name = member_names[member_name]

                # Check if member already exists (by last and first name)
                existing_member = self.member_crud.get_by_name(last_name, first_name)
                if existing_member:
                    # Update member details ONLY if the new data is better/more complete
                    # and preserve existing party, chamber, state data
                    from domains.congressional.schemas import CongressMemberUpdate
                    update_data = CongressMemberUpdate()
                    
                    # Only update fields that are not already set or are improved
                    if prefix and not existing_member.prefix:
                        update_data.prefix = prefix
                    if full_name and len(full_name) > len(existing_member.full_name or ""):
                        update_data.full_name = full_name
                    
                    # Only update if we have actual changes to make
                    update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
                    if update_dict:
                        self.member_crud.update(existing_member.id, update_data)
                        logger.info(f"Updated congress member: {existing_member.full_name} ({existing_member.id})")
                        logger.debug(f"Updated member: {existing_member.full_name}")
                    continue

                # Create new member record with minimal required data
                # Leave party, chamber, state empty for later enrichment via external APIs
                member_data = CongressMemberCreate(
                    first_name=first_name or "Unknown",
                    last_name=last_name,
                    full_name=full_name,
                    prefix=prefix if prefix else None,
                    # These fields are left empty for later enrichment from external APIs
                    chamber=None,  
                    party=None,   
                    state=None,   
                    district=None,
                    is_active=True
                )
                
                member = self.member_crud.create(member_data)
                created_count += 1
                
                logger.info(f"Created congress member: {member.full_name} ({member.id})")
                logger.debug(f"Created member: {member.full_name}")
                
            except Exception as e:
                logger.error(f"Failed to create member {member_name}: {e}")
                continue
        
        logger.info(f"Created {created_count} new members")
        return created_count
    
    def _parse_name_from_member(self, member_name: str) -> Tuple[str, str]:
        """
        Parse first and last name from member name string.
        
        Args:
            member_name: Member name string (e.g., "Barletta", "Brooks", "DelBene")
            
        Returns:
            Tuple of (first_name, last_name)
        """
        if not member_name:
            return "", ""
        
        # Try to extract from description patterns
        # Common patterns: "Mr. Lou Barletta", "Ms. Suzan K. DelBene", "Mr. Mo Brooks"
        name_patterns = [
            r'(Mr\.|Ms\.|Mrs\.|Dr\.|Sen\.|Rep\.)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+([A-Za-z]+)',
            r'(Mr\.|Ms\.|Mrs\.|Dr\.|Sen\.|Rep\.)\s+([A-Za-z]+)\s+([A-Za-z]+)',
        ]
        
        # For now, just use the member name as last name
        # This will be improved when we have better name extraction
        last_name = member_name.strip()
        first_name = ""  # Will be populated later from external APIs
        
        return first_name, last_name
    
    def _get_consistent_member_names(self, df: pd.DataFrame) -> Dict[str, Tuple[str, str, str, str]]:
        """
        Build a mapping of member names to consistent (first_name, last_name, full_name, prefix) tuples.
        
        Args:
            df: DataFrame containing trade data
            
        Returns:
            Dict mapping member_key to (first_name, last_name, full_name, prefix)
        """
        member_names = {}
        has_separate_names = 'FirstName' in df.columns and 'LastName' in df.columns
        has_prefix = 'Prefix' in df.columns
        
        for member_name in df['Member'].dropna().unique():
            if not member_name or member_name.strip() == '':
                continue
            
            member_data = df[df['Member'] == member_name]
            
            # Find the best name entry for this member
            # Priority: JT (joint) entries with names > any entry with names
            best_entry = None
            
            if has_separate_names:
                # First try to find JT entries with names
                jt_entries = member_data[member_data['Owner'] == 'JT']
                jt_with_names = jt_entries[
                    (jt_entries['FirstName'].notna()) & 
                    (jt_entries['FirstName'] != '') & 
                    (jt_entries['LastName'].notna()) & 
                    (jt_entries['LastName'] != '')
                ]
                
                if not jt_with_names.empty:
                    best_entry = jt_with_names.iloc[0]
                else:
                    # Try any entry with names
                    entries_with_names = member_data[
                        (member_data['FirstName'].notna()) & 
                        (member_data['FirstName'] != '') & 
                        (member_data['LastName'].notna()) & 
                        (member_data['LastName'] != '')
                    ]
                    if not entries_with_names.empty:
                        best_entry = entries_with_names.iloc[0]
                
                if best_entry is not None:
                    prefix = str(best_entry.get('Prefix', '')).strip() if has_prefix and pd.notna(best_entry.get('Prefix')) else ""
                    first_name = str(best_entry['FirstName']).strip()
                    last_name = str(best_entry['LastName']).strip()
                    
                    # Create full name with prefix
                    if prefix:
                        full_name = f"{prefix} {first_name} {last_name}".strip()
                    else:
                        full_name = f"{first_name} {last_name}".strip()
                else:
                    # Fall back to parsing from Member column
                    first_name, last_name = self._parse_name_from_member(member_name)
                    full_name = f"{first_name} {last_name}".strip()
                    prefix = ""
            else:
                # Parse from Member column
                first_name, last_name = self._parse_name_from_member(member_name)
                full_name = f"{first_name} {last_name}".strip()
                prefix = ""
            
            member_names[member_name] = (first_name, last_name, full_name, prefix)
        
        return member_names
    
    async def _import_trades_from_dataframe(self, df: pd.DataFrame, source_table: str) -> Tuple[int, int]:
        """
        Import trades from DataFrame into database.
        
        Args:
            df: DataFrame containing trade data
            source_table: Name of source table/file for reference
            
        Returns:
            Tuple of (successful_imports, failed_imports)
        """
        created_count = 0
        failed_count = 0
        
        # Check if we have FirstName and LastName columns (new format)
        has_separate_names = 'FirstName' in df.columns and 'LastName' in df.columns
        
        # Get consistent member names mapping
        member_names = self._get_consistent_member_names(df)
        
        # Expected column mappings
        column_mappings = {
            'member': 'Member',
            'doc_id': 'DocID',
            'owner': 'Owner',
            'asset': 'Asset',
            'ticker': 'Ticker',
            'transaction_type': 'Transaction Type',
            'transaction_date': 'Transaction Date',
            'notification_date': 'Notification Date',
            'amount': 'Amount',
            'filing_status': 'Filing Status',
            'description': 'Description'
        }
        
        # Validate required columns exist
        missing_columns = []
        for expected_col in ['Member', 'DocID', 'Asset', 'Transaction Type', 'Transaction Date', 'Notification Date', 'Amount']:
            if expected_col not in df.columns:
                missing_columns.append(expected_col)
        
        if missing_columns:
            logger.error(f"Missing required columns in {source_table}: {missing_columns}")
            return 0, len(df)
        
        logger.info(f"Processing {len(df)} trades from {source_table}")
        
        for idx, row in df.iterrows():
            try:
                # Extract member information
                member_key = str(row['Member']).strip()
                if not member_key or member_key == 'nan':
                    failed_count += 1
                    continue
                
                # Get consistent member names
                if member_key in member_names:
                    first_name, last_name, full_name, prefix = member_names[member_key]
                else:
                    first_name, last_name = self._parse_name_from_member(member_key)
                    full_name = f"{first_name} {last_name}".strip()
                    prefix = ""
                
                # Get or create member
                member = self.member_crud.get_by_name(member_key)
                if not member:
                    logger.warning(f"Member not found for key: {member_key}")
                    failed_count += 1
                    continue
                
                # Extract trade data with better validation
                doc_id = str(row['DocID']).strip()
                owner = str(row['Owner']).strip() if 'Owner' in df.columns and pd.notna(row['Owner']) else "Unknown"
                asset = str(row['Asset']).strip()
                ticker = str(row['Ticker']).strip() if 'Ticker' in df.columns and pd.notna(row['Ticker']) else ""
                
                # Handle malformed data where columns are shifted
                transaction_type_raw = str(row['Transaction Type']).strip()
                transaction_date_raw = str(row['Transaction Date']).strip()
                notification_date_raw = str(row['Notification Date']).strip()
                amount_raw = str(row['Amount']).strip()
                
                # Try to determine which field is which based on content patterns
                transaction_type = self._extract_transaction_type(transaction_type_raw, transaction_date_raw, notification_date_raw, amount_raw)
                transaction_date = self._extract_transaction_date(transaction_type_raw, transaction_date_raw, notification_date_raw, amount_raw)
                notification_date = self._extract_notification_date(transaction_type_raw, transaction_date_raw, notification_date_raw, amount_raw)
                amount = self._extract_amount(transaction_type_raw, transaction_date_raw, notification_date_raw, amount_raw)
                
                filing_status = str(row['Filing Status']).strip() if 'Filing Status' in df.columns and pd.notna(row['Filing Status']) else "New"
                description = str(row['Description']).strip() if 'Description' in df.columns and pd.notna(row['Description']) else ""
                
                # Extract asset description for raw_asset_description field
                raw_asset_description = self._extract_asset_description(row)
                
                # Clean up amount (remove $ and commas)
                if amount.startswith('$'):
                    amount = amount[1:]
                amount = amount.replace(',', '')
                
                # Create trade record with proper validation
                trade_data = CongressionalTradeCreate(
                    member_id=member.id,
                    doc_id=doc_id,
                    raw_asset_description=raw_asset_description,
                    transaction_type=transaction_type if transaction_type else "P",  # Default to Purchase if empty
                    transaction_date=self._parse_date_string(transaction_date) if transaction_date else None,  # Allow None for missing dates
                    notification_date=self._parse_date_string(notification_date) if notification_date else None,  # Allow None for missing dates
                    amount=amount if amount else None,  # Allow None for missing amounts
                    filing_status="N",  # Use "N" for New instead of "New"
                    description=description,
                    source_table=source_table
                )
                
                await self.trade_crud.create(trade_data)
                created_count += 1
                
                if created_count % 100 == 0:
                    logger.info(f"Processed {created_count} trades from {source_table}")
                    
            except Exception as e:
                logger.warning(f"Failed to import trade at row {idx}: {e}")
                failed_count += 1
        
        logger.info(f"Trade import for {source_table}: {created_count} successful, {failed_count} failed")
        return created_count, failed_count
    
    def _import_trades_from_dataframe_sync(self, df: pd.DataFrame, source_table: str) -> Tuple[int, int]:
        """
        Synchronous version of _import_trades_from_dataframe for use with sync sessions.
        
        Args:
            df: DataFrame containing trade data
            source_table: Name of source table/file for reference
            
        Returns:
            Tuple of (successful_imports, failed_imports)
        """
        created_count = 0
        failed_count = 0
        
        # Check if we have FirstName and LastName columns (new format)
        has_separate_names = 'FirstName' in df.columns and 'LastName' in df.columns
        
        # Get consistent member names mapping
        member_names = self._get_consistent_member_names(df)
        
        # Expected column mappings
        column_mappings = {
            'member': 'Member',
            'doc_id': 'DocID',
            'owner': 'Owner',
            'asset': 'Asset',
            'ticker': 'Ticker',
            'transaction_type': 'Transaction Type',
            'transaction_date': 'Transaction Date',
            'notification_date': 'Notification Date',
            'amount': 'Amount',
            'filing_status': 'Filing Status',
            'description': 'Description'
        }
        
        # Validate required columns exist
        missing_columns = []
        for expected_col in ['Member', 'DocID', 'Asset', 'Transaction Type', 'Transaction Date', 'Notification Date', 'Amount']:
            if expected_col not in df.columns:
                missing_columns.append(expected_col)
        
        if missing_columns:
            logger.error(f"Missing required columns in {source_table}: {missing_columns}")
            return 0, len(df)
        
        logger.info(f"Processing {len(df)} trades from {source_table}")
        
        for idx, row in df.iterrows():
            try:
                # Validate record if validator is available
                if self.validator:
                    validation_result = self.validator.validate_record(row.to_dict())
                    if not validation_result.is_valid:
                        logger.debug(f"Record validation failed at row {idx}: {validation_result.errors}")
                        failed_count += 1
                        continue
                    
                    # Use cleaned data if available
                    if validation_result.cleaned_data:
                        row = pd.Series(validation_result.cleaned_data)
                
                # Extract member information
                member_key = str(row['Member']).strip()
                if not member_key or member_key == 'nan':
                    failed_count += 1
                    continue
                
                # Get consistent member names
                if member_key in member_names:
                    first_name, last_name, full_name, prefix = member_names[member_key]
                else:
                    first_name, last_name = self._parse_name_from_member(member_key)
                    full_name = f"{first_name} {last_name}".strip()
                    prefix = ""
                
                # Get or create member
                member = self.member_crud.get_by_name(member_key)
                if not member:
                    logger.warning(f"Member not found for key: {member_key}")
                    failed_count += 1
                    continue
                
                # Extract trade data with better validation
                doc_id = str(row['DocID']).strip()
                owner = str(row['Owner']).strip() if 'Owner' in df.columns and pd.notna(row['Owner']) else "Unknown"
                asset = str(row['Asset']).strip()
                ticker = str(row['Ticker']).strip() if 'Ticker' in df.columns and pd.notna(row['Ticker']) else ""
                
                # Handle malformed data where columns are shifted
                transaction_type_raw = str(row['Transaction Type']).strip()
                transaction_date_raw = str(row['Transaction Date']).strip()
                notification_date_raw = str(row['Notification Date']).strip()
                amount_raw = str(row['Amount']).strip()
                
                # Try to determine which field is which based on content patterns
                transaction_type = self._extract_transaction_type(transaction_type_raw, transaction_date_raw, notification_date_raw, amount_raw)
                transaction_date = self._extract_transaction_date(transaction_type_raw, transaction_date_raw, notification_date_raw, amount_raw)
                notification_date = self._extract_notification_date(transaction_type_raw, transaction_date_raw, notification_date_raw, amount_raw)
                amount = self._extract_amount(transaction_type_raw, transaction_date_raw, notification_date_raw, amount_raw)
                
                filing_status = str(row['Filing Status']).strip() if 'Filing Status' in df.columns and pd.notna(row['Filing Status']) else "New"
                description = str(row['Description']).strip() if 'Description' in df.columns and pd.notna(row['Description']) else ""
                
                # Extract asset description for raw_asset_description field
                raw_asset_description = self._extract_asset_description(row)
                
                # Parse amount into amount_min, amount_max, or amount_exact
                amount_min, amount_max, amount_exact = self._parse_amount_to_fields(amount)
                
                # Create trade record with proper validation
                trade_data = CongressionalTradeCreate(
                    member_id=member.id,
                    doc_id=doc_id,
                    owner=owner if owner and owner != "Unknown" else None,
                    raw_asset_description=raw_asset_description,
                    ticker=ticker if ticker else None,
                    transaction_type=transaction_type if transaction_type else "P",  # Default to Purchase if empty
                    transaction_date=self._parse_date_string(transaction_date) if transaction_date else None,  # Allow None for missing dates
                    notification_date=self._parse_date_string(notification_date) if notification_date else None,  # Allow None for missing dates
                    amount_min=amount_min,
                    amount_max=amount_max,
                    amount_exact=amount_exact,
                    filing_status="N",  # Use "N" for New instead of "New"
                    comment=description if description else None
                )
                
                self.trade_crud.create(trade_data)
                created_count += 1
                
                if created_count % 100 == 0:
                    logger.info(f"Processed {created_count} trades from {source_table}")
                    
            except Exception as e:
                logger.warning(f"Failed to import trade at row {idx}: {e}")
                failed_count += 1
        
        logger.info(f"Trade import for {source_table}: {created_count} successful, {failed_count} failed")
        return created_count, failed_count
    
    def _parse_amount_range(self, amount_str: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Parse amount range strings like '$1,001 - $15,000' into min/max values in cents.
        
        Args:
            amount_str: Amount string from CSV
            
        Returns:
            Tuple of (min_cents, max_cents)
        """
        if not amount_str or pd.isna(amount_str):
            return None, None
        
        try:
            # Remove common characters
            cleaned = str(amount_str).replace('$', '').replace(',', '').strip()
            
            # Handle ranges
            if ' - ' in cleaned:
                parts = cleaned.split(' - ')
                if len(parts) == 2:
                    min_val = float(parts[0].strip()) * 100  # Convert to cents
                    max_val = float(parts[1].strip()) * 100
                    return int(min_val), int(max_val)
            
            # Handle single values
            if cleaned.replace('.', '').isdigit():
                val = float(cleaned) * 100
                return int(val), int(val)
            
            # Handle special cases like "$50,001 +"
            if '+' in cleaned:
                min_val = float(cleaned.replace('+', '').strip()) * 100
                return int(min_val), None
                
        except Exception as e:
            logger.debug(f"Failed to parse amount '{amount_str}': {e}")
        
        return None, None
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string into date object."""
        if not date_str or pd.isna(date_str):
            return None
        
        try:
            if isinstance(date_str, str):
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y']:
                    try:
                        return datetime.strptime(date_str, fmt).date()
                    except ValueError:
                        continue
            elif hasattr(date_str, 'date'):
                return date_str.date()
        except Exception:
            pass
        
        return None
    
    async def enrich_member_data(self) -> Dict[str, int]:
        """
        Enrich member data with additional information from external APIs.
        
        This would fetch chamber, party, state, district info from:
        - congress.gov API
        - Propublica Congress API
        - Ballotpedia
        
        Returns:
            Dict with enrichment statistics
        """
        # Get all members without complete data
        result = await self.session.execute(
            select(CongressMember).where(
                (CongressMember.chamber.is_(None)) |
                (CongressMember.party.is_(None)) |
                (CongressMember.state.is_(None))
            )
        )
        members = result.scalars().all()
        
        logger.info(f"Found {len(members)} members needing data enrichment")
        
        enriched_count = 0
        
        # TODO: Implement external API calls to enrich member data
        # For now, we'll just mark this as a placeholder
        
        for member in members:
            try:
                # Placeholder for external API enrichment
                # This would call Congress.gov API, Propublica, etc.
                
                # For now, just update with placeholder data
                if not member.chamber:
                    # Simple heuristic based on naming patterns or other data
                    member.chamber = "house"  # Default assumption
                
                if not member.party:
                    member.party = "unknown"
                
                if not member.state:
                    member.state = "unknown"
                
                enriched_count += 1
                
            except Exception as e:
                logger.error(f"Failed to enrich data for member {member.full_name}: {e}")
                continue
        
        await self.session.commit()
        
        logger.info(f"Enriched data for {enriched_count} members")
        return {
            "members_processed": len(members),
            "members_enriched": enriched_count
        }
    
    def enrich_member_data_sync(self) -> Dict[str, int]:
        """
        Synchronous version of enrich_member_data for use with sync sessions.
        
        Enrich member data with additional information from external APIs.
        
        This would fetch chamber, party, state, district info from:
        - congress.gov API
        - Propublica Congress API
        - Ballotpedia
        
        Returns:
            Dict with enrichment statistics
        """
        # Get all members without complete data
        from sqlalchemy import select
        result = self.session.execute(
            select(CongressMember).where(
                (CongressMember.chamber.is_(None)) |
                (CongressMember.party.is_(None)) |
                (CongressMember.state.is_(None))
            )
        )
        members = result.scalars().all()
        
        logger.info(f"Found {len(members)} members to enrich")
        
        enriched_count = 0
        failed_count = 0
        
        for member in members:
            try:
                # TODO: Implement actual API calls to enrich member data
                # For now, just mark as processed
                enriched_count += 1
                
                if enriched_count % 50 == 0:
                    logger.info(f"Enriched {enriched_count} members...")
                    
            except Exception as e:
                logger.error(f"Failed to enrich member {member.full_name}: {e}")
                failed_count += 1
                continue
        
        self.session.commit()
        
        result = {
            "members_enriched": enriched_count,
            "members_failed": failed_count,
            "total_processed": enriched_count + failed_count
        }
        
        logger.info(f"Member enrichment complete: {result}")
        return result

    def _extract_transaction_type(self, col1: str, col2: str, col3: str, col4: str) -> str:
        """
        Extract transaction type from potentially malformed columns.
        Transaction type should be 'P' (Purchase), 'S' (Sale), or 'E' (Exchange).
        Prefers blank over wrong data.
        """
        # Look for valid transaction types - be very strict
        for col in [col1, col2, col3, col4]:
            if col.strip().upper() in ['P', 'S', 'E']:
                return col.strip().upper()
        
        # Don't try to guess - return blank if no valid type found
        return ""
    
    def _extract_transaction_date(self, col1: str, col2: str, col3: str, col4: str) -> str:
        """
        Extract transaction date from potentially malformed columns.
        Look for date patterns like MM/DD/YYYY. Prefers blank over wrong data.
        """
        import re
        
        # Only accept proper date format MM/DD/YYYY
        date_pattern = r'^\d{1,2}/\d{1,2}/\d{4}$'
        
        for col in [col1, col2, col3, col4]:
            if re.match(date_pattern, col.strip()):
                return col.strip()
        
        # Don't provide fallback - return blank if no valid date found
        return ""
    
    def _extract_notification_date(self, col1: str, col2: str, col3: str, col4: str) -> str:
        """
        Extract notification date from potentially malformed columns.
        Look for date patterns like MM/DD/YYYY. Prefers blank over wrong data.
        """
        import re
        
        # Only accept proper date format MM/DD/YYYY
        date_pattern = r'^\d{1,2}/\d{1,2}/\d{4}$'
        
        # Look for second date (notification date is usually after transaction date)
        dates_found = []
        for col in [col1, col2, col3, col4]:
            if re.match(date_pattern, col.strip()):
                dates_found.append(col.strip())
        
        if len(dates_found) >= 2:
            return dates_found[1]  # Return second date found
        elif len(dates_found) == 1:
            return dates_found[0]  # Return the only date found
        
        # Don't provide fallback - return blank if no valid date found
        return ""
    
    def _extract_amount(self, col1: str, col2: str, col3: str, col4: str) -> str:
        """
        Extract amount from potentially malformed columns.
        Look for dollar amount patterns like $1,001 or $15,001.
        Prefers blank over wrong data.
        """
        import re
        
        # Only accept proper dollar amount format
        amount_pattern = r'^\$[\d,]+$'
        
        for col in [col1, col2, col3, col4]:
            if re.match(amount_pattern, col.strip()):
                return col.strip()
        
        # Don't provide fallback - return blank if no valid amount found
        return ""
    
    def _extract_asset_description(self, row: pd.Series) -> str:
        """
        Extract asset description from the row data.
        """
        asset = str(row['Asset']).strip() if 'Asset' in row and pd.notna(row['Asset']) else ""
        ticker = str(row['Ticker']).strip() if 'Ticker' in row and pd.notna(row['Ticker']) else ""
        description = str(row['Description']).strip() if 'Description' in row and pd.notna(row['Description']) else ""
        
        # Combine available information
        parts = []
        if asset:
            parts.append(asset)
        if ticker:
            parts.append(f"({ticker})")
        if description:
            parts.append(description)
        
        return " - ".join(parts) if parts else "Unknown Asset"

    def _parse_date_string(self, date_str: str) -> Optional[date]:
        """
        Parse date string in MM/DD/YYYY format to date object.
        Returns None if parsing fails.
        """
        if not date_str or date_str.strip() == '':
            return None
        
        try:
            from datetime import datetime
            # Parse MM/DD/YYYY format
            return datetime.strptime(date_str.strip(), '%m/%d/%Y').date()
        except ValueError:
            return None

    def _parse_amount_to_fields(self, amount_str: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Parse amount string into amount_min, amount_max, and amount_exact fields.
        
        Args:
            amount_str: Amount string from CSV (e.g., "$15,001 - $50,000", "$1,000", "None")
            
        Returns:
            Tuple of (amount_min, amount_max, amount_exact) in cents
        """
        if not amount_str or amount_str.strip() == '' or amount_str.strip().lower() == 'none':
            # If no amount, set a minimal range of $1 to indicate unknown amount
            return 100, 100, None  # $1 - $1 range
        
        try:
            # Clean the string
            cleaned = amount_str.strip()
            
            # Remove dollar signs and commas
            cleaned = cleaned.replace('$', '').replace(',', '')
            
            # Check if it's a range (contains " - ")
            if ' - ' in cleaned:
                parts = cleaned.split(' - ')
                if len(parts) == 2:
                    try:
                        min_val = int(float(parts[0].strip()) * 100)  # Convert to cents
                        max_val = int(float(parts[1].strip()) * 100)
                        return min_val, max_val, None
                    except ValueError:
                        pass
            
            # Check if it's a single exact value
            try:
                exact_val = int(float(cleaned) * 100)  # Convert to cents
                return None, None, exact_val
            except ValueError:
                pass
            
            # If parsing fails, default to $1 range
            logger.debug(f"Could not parse amount '{amount_str}', defaulting to $1 range")
            return 100, 100, None  # $1 - $1 range
            
        except Exception as e:
            logger.debug(f"Error parsing amount '{amount_str}': {e}")
            return 100, 100, None  # $1 - $1 range


# Main import functions for scripts

async def import_congressional_data_from_csvs(session: AsyncSession, 
                                            csv_directory: str) -> Dict[str, int]:
    """
    Main function to import congressional data from CSV files.
    
    Args:
        session: Database session
        csv_directory: Path to directory containing CSV files
        
    Returns:
        Dict with import statistics
    """
    ingester = CongressionalDataIngester(session)
    return await ingester.import_congressional_data_from_csvs(csv_directory)


async def import_congressional_data_from_sqlite(session: AsyncSession,
                                              sqlite_path: str) -> Dict[str, int]:
    """
    Main function to import congressional data from SQLite database.
    
    Args:
        session: Database session
        sqlite_path: Path to SQLite database file
        
    Returns:
        Dict with import statistics
    """
    ingester = CongressionalDataIngester(session)
    return await ingester.import_from_sqlite_database(sqlite_path)


async def enrich_member_profiles(session: AsyncSession) -> Dict[str, int]:
    """
    Main function to enrich member profile data from external APIs.
    
    Args:
        session: Database session
        
    Returns:
        Dict with enrichment statistics
    """
    ingester = CongressionalDataIngester(session)
    return await ingester.enrich_member_data() 