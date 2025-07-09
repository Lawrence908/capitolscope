#!/usr/bin/env python3
"""
Database connection test script for CapitolScope.

This script tests the database connection, verifies configuration,
and provides debugging information for troubleshooting.
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import settings
from database.connection import (
    db_manager,
    startup_database,
    shutdown_database,
    check_database_connection,
    get_database_info,
)
from database.models import Base


async def test_basic_connection():
    """Test basic database connection."""
    print("🔗 Testing basic database connection...")
    
    try:
        # Initialize database
        await startup_database()
        
        # Check connection
        is_connected = await check_database_connection()
        if is_connected:
            print("✅ Database connection successful!")
            return True
        else:
            print("❌ Database connection failed!")
            return False
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


async def test_database_info():
    """Test getting database information."""
    print("\n📊 Getting database information...")
    
    try:
        info = await get_database_info()
        print(f"✅ Database info retrieved:")
        for key, value in info.items():
            print(f"   {key}: {value}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to get database info: {e}")
        return False


async def test_health_check():
    """Test database health check."""
    print("\n🏥 Testing database health check...")
    
    try:
        health = await db_manager.health_check()
        print(f"✅ Health check results:")
        for key, value in health.items():
            print(f"   {key}: {value}")
        
        return health.get("status") == "healthy"
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def test_raw_query():
    """Test executing raw SQL queries."""
    print("\n🔍 Testing raw SQL query execution...")
    
    try:
        # Test simple query
        result = await db_manager.execute_raw_query("SELECT 1 as test_value")
        
        if result["success"]:
            print("✅ Raw query successful!")
            print(f"   Result: {result}")
            return True
        else:
            print(f"❌ Raw query failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Raw query error: {e}")
        return False


async def test_session_management():
    """Test session management."""
    print("\n📝 Testing session management...")
    
    try:
        # Test getting a session
        session = await db_manager.get_session()
        print("✅ Session created successfully!")
        
        # Test session scope
        async with db_manager.session_scope() as scoped_session:
            result = await scoped_session.execute("SELECT 1")
            value = result.scalar()
            assert value == 1
            print("✅ Session scope working correctly!")
        
        await session.close()
        return True
        
    except Exception as e:
        print(f"❌ Session management error: {e}")
        return False


async def test_connection_pool():
    """Test connection pool behavior."""
    print("\n🏊 Testing connection pool...")
    
    try:
        # Create multiple sessions simultaneously
        sessions = []
        for i in range(5):
            session = await db_manager.get_session()
            sessions.append(session)
            
        print(f"✅ Created {len(sessions)} sessions successfully!")
        
        # Test concurrent queries
        tasks = []
        for i, session in enumerate(sessions):
            task = session.execute(f"SELECT {i} as session_id")
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        print(f"✅ Executed {len(results)} concurrent queries!")
        
        # Close all sessions
        for session in sessions:
            await session.close()
            
        return True
        
    except Exception as e:
        print(f"❌ Connection pool error: {e}")
        return False


async def test_database_schema():
    """Test database schema inspection."""
    print("\n🏗️ Testing database schema inspection...")
    
    try:
        # Get table information
        query = """
        SELECT table_name, table_schema 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """
        
        result = await db_manager.execute_raw_query(query)
        
        if result["success"]:
            tables = result["rows"]
            print(f"✅ Found {len(tables)} tables in public schema:")
            for table in tables:
                print(f"   - {table['table_name']}")
            return True
        else:
            print(f"❌ Schema inspection failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Schema inspection error: {e}")
        return False


def print_configuration():
    """Print current configuration."""
    print("\n⚙️  Current configuration:")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Database Host: {settings.DATABASE_HOST}")
    print(f"   Database Port: {settings.DATABASE_PORT}")
    print(f"   Database Name: {settings.DATABASE_NAME}")
    print(f"   Database User: {settings.DATABASE_USER}")
    print(f"   Pool Size: {settings.DATABASE_POOL_SIZE}")
    print(f"   Max Overflow: {settings.DATABASE_MAX_OVERFLOW}")
    print(f"   Echo: {settings.DATABASE_ECHO}")
    print(f"   Debug: {settings.DEBUG}")


def check_environment_variables():
    """Check required environment variables."""
    print("\n🔍 Checking environment variables...")
    
    required_vars = [
        "DATABASE_HOST",
        "DATABASE_PORT", 
        "DATABASE_USER",
        "DATABASE_PASSWORD",
        "DATABASE_NAME",
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SECRET_KEY",
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    else:
        print("✅ All required environment variables are set!")
        return True


async def performance_test():
    """Test database performance."""
    print("\n🚀 Running performance test...")
    
    try:
        # Test query performance
        start_time = time.time()
        
        # Run 10 concurrent queries
        tasks = []
        for i in range(10):
            task = db_manager.execute_raw_query("SELECT pg_sleep(0.1), 1 as test_value")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"✅ Executed 10 concurrent queries in {duration:.2f} seconds")
        
        # Check if all queries were successful
        success_count = sum(1 for r in results if r["success"])
        print(f"✅ {success_count}/10 queries successful")
        
        return success_count == 10
        
    except Exception as e:
        print(f"❌ Performance test error: {e}")
        return False


async def cleanup_test():
    """Test cleanup procedures."""
    print("\n🧹 Testing cleanup procedures...")
    
    try:
        # Test closing database connections
        await shutdown_database()
        print("✅ Database shutdown successful!")
        
        # Test that connection is closed
        is_connected = db_manager.is_connected
        if not is_connected:
            print("✅ Database connection properly closed!")
            return True
        else:
            print("❌ Database connection not properly closed!")
            return False
            
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
        return False


async def main():
    """Run all database tests."""
    print("🎯 CapitolScope Database Connection Test Suite")
    print("=" * 50)
    
    # Check environment
    if not check_environment_variables():
        print("\n❌ Environment check failed. Please set required variables.")
        return False
    
    # Print configuration
    print_configuration()
    
    # Run tests
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Database Info", test_database_info),
        ("Health Check", test_health_check),
        ("Raw Query", test_raw_query),
        ("Session Management", test_session_management),
        ("Connection Pool", test_connection_pool),
        ("Schema Inspection", test_database_schema),
        ("Performance Test", performance_test),
        ("Cleanup", cleanup_test),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed + failed} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Database connection is working properly.")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the configuration.")
        return False


if __name__ == "__main__":
    # Run the test suite
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 