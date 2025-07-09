#!/usr/bin/env python3
"""
Simple database connection test for CapitolScope.

This script quickly tests if your environment variables are set correctly
and if you can connect to your Supabase database.
"""

import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "app" / "src"
sys.path.insert(0, str(src_path))

def test_environment():
    """Test environment configuration."""
    print("🔍 Checking environment variables...")
    
    try:
        from core.config import settings
        
        required_vars = {
            "SUPABASE_URL": settings.SUPABASE_URL,
            "SUPABASE_PASSWORD": str(settings.SUPABASE_PASSWORD),
            "SUPABASE_KEY": str(settings.SUPABASE_KEY),
            "SUPABASE_SERVICE_ROLE_KEY": str(settings.SUPABASE_SERVICE_ROLE_KEY),
            "SUPABASE_JWT_SECRET": str(settings.SUPABASE_JWT_SECRET),
        }
        
        missing_vars = []
        for var_name, var_value in required_vars.items():
            if not var_value or var_value == "None":
                missing_vars.append(var_name)
                print(f"  ❌ {var_name}: MISSING")
            else:
                # Mask sensitive values for display
                display_value = var_value[:8] + "..." if len(var_value) > 8 else "SET"
                print(f"  ✅ {var_name}: {display_value}")
        
        if missing_vars:
            print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("\nPlease add them to your .env file:")
            for var in missing_vars:
                print(f"  {var}=your-value-here")
            return False
        
        print("\n✅ All required environment variables are set!")
        
        # Test database URL construction
        db_url = settings.database_url
        if "postgresql" in db_url and "supabase" in db_url:
            print(f"✅ Database URL looks correct: {db_url.split('@')[1] if '@' in db_url else 'OK'}")
        else:
            print(f"⚠️ Database URL format: {db_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False


async def test_database_connection():
    """Test actual database connection."""
    print("\n🔗 Testing database connection...")
    
    try:
        from core.database import DatabaseManager
        
        db_manager = DatabaseManager()
        await db_manager.initialize()
        success = await db_manager.test_connection()
        await db_manager.close()
        
        if success:
            print("✅ Database connection successful!")
            return True
        else:
            print("❌ Database connection failed!")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Try: pip install -e . from the app/ directory")
        return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        print("\n💡 Common issues:")
        print("  • Check your SUPABASE_URL format: https://xyz.supabase.co")
        print("  • Verify DATABASE_PASSWORD is correct")
        print("  • Ensure your Supabase project is active")
        print("  • Check network connectivity")
        return False


def print_setup_guide():
    """Print setup instructions."""
    print("\n📋 Setup Guide:")
    print("=" * 50)
    print("1. Create a .env file in your project root with:")
    print("""
# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_PASSWORD=your-database-password
SUPABASE_JWT_SECRET=your-super-secret-jwt-key-change-this

# Application Settings  
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
""")
    
    print("2. Get your Supabase credentials from:")
    print("   https://supabase.com/dashboard/project/your-project/settings/api")
    
    print("\n3. Install dependencies:")
    print("   pip install -e .              # Basic install")
    print("   pip install -e .[dev]         # With dev tools")
    
    print("\n4. Run database setup:")
    print("   python scripts/setup_database.py")


async def main():
    """Main test function."""
    print("🧪 CapitolScope Database Connection Test")
    print("=" * 40)
    
    # Test environment variables
    env_ok = test_environment()
    
    if not env_ok:
        print_setup_guide()
        return 1
    
    # Test database connection
    try:
        import asyncio
        db_ok = await test_database_connection()
        
        if db_ok:
            print("\n🎉 Everything looks good!")
            print("\nNext steps:")
            print("1. Run: python scripts/setup_database.py")
            print("2. Start API: cd app && python -m uvicorn main:app --reload")
            return 0
        else:
            print("\n❌ Database connection failed. Check your credentials.")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 