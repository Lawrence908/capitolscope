#!/usr/bin/env python3
"""Test script to verify database structure with UUID primary keys."""

import asyncio
from sqlalchemy import text
import sys
sys.path.append('app/src')
from core.database import engine

async def check_database_structure():
    """Check that tables have UUID primary keys."""
    async with engine.begin() as conn:
        # Check primary key data types
        result = await conn.execute(text("""
            SELECT 
                table_name, 
                column_name, 
                data_type 
            FROM information_schema.columns 
            WHERE table_name IN ('users', 'congress_members', 'securities', 'asset_types', 'exchanges', 'sectors') 
                AND column_name = 'id' 
            ORDER BY table_name
        """))
        
        rows = result.fetchall()
        print("Primary Key Data Types:")
        for row in rows:
            print(f"  {row[0]}.{row[1]}: {row[2]}")
        
        # Check foreign key data types
        result = await conn.execute(text("""
            SELECT 
                tc.table_name, 
                kcu.column_name, 
                c.data_type
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.columns c 
                ON kcu.table_name = c.table_name 
                AND kcu.column_name = c.column_name
            WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND c.data_type = 'uuid'
            ORDER BY tc.table_name, kcu.column_name
        """))
        
        rows = result.fetchall()
        print("\nUUID Foreign Keys:")
        for row in rows:
            print(f"  {row[0]}.{row[1]}: {row[2]}")
        
        # Check enum types
        result = await conn.execute(text("""
            SELECT 
                t.typname as enum_name,
                e.enumlabel as enum_value
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname IN ('authprovider', 'userstatus', 'userrole', 'notificationtype', 'notificationchannel')
            ORDER BY t.typname, e.enumsortorder
        """))
        
        rows = result.fetchall()
        print("\nEnum Types:")
        current_enum = None
        for row in rows:
            if row[0] != current_enum:
                current_enum = row[0]
                print(f"  {row[0]}:")
            print(f"    - {row[1]}")

if __name__ == "__main__":
    asyncio.run(check_database_structure()) 