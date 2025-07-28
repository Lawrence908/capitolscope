#!/usr/bin/env python3
import asyncio
import os
from sqlalchemy import text
from src.core.database import get_sync_db_session

async def check_enum_values():
    async for session in get_async_session():
        try:
            result = await session.execute(text("SELECT unnest(enum_range(NULL::subscription_tier_enum))"))
            values = [row[0] for row in result]
            print(f"Enum values: {values}")
            
            # Also check existing subscription_tier values
            result = await session.execute(text("SELECT DISTINCT subscription_tier FROM users"))
            existing_values = [row[0] for row in result]
            print(f"Existing subscription_tier values: {existing_values}")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await session.close()
        break

if __name__ == "__main__":
    asyncio.run(check_enum_values()) 