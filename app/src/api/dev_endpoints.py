"""
Development endpoints for testing frontend without authentication.
These should be removed in production.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime, timedelta
import random

from core.database import get_db_session
import logging
logger = logging.getLogger(__name__)
from core.responses import success_response, paginated_response

router = APIRouter()

# Mock data for development
MOCK_MEMBERS = [
    {
        "id": 1,
        "bioguide_id": "P000197",
        "first_name": "Nancy",
        "last_name": "Pelosi",
        "full_name": "Nancy Pelosi",
        "party": "Democratic",
        "state": "CA",
        "chamber": "House",
        "in_office": True,
        "total_trades": 45,
        "total_value": 2500000,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    },
    {
        "id": 2,
        "bioguide_id": "T000463",
        "first_name": "Michael",
        "last_name": "Turner",
        "full_name": "Michael Turner",
        "party": "Republican",
        "state": "OH",
        "chamber": "House",
        "in_office": True,
        "total_trades": 23,
        "total_value": 1200000,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    },
    {
        "id": 3,
        "bioguide_id": "S000510",
        "first_name": "Adam",
        "last_name": "Smith",
        "full_name": "Adam Smith",
        "party": "Democratic",
        "state": "WA",
        "chamber": "House",
        "in_office": True,
        "total_trades": 67,
        "total_value": 3400000,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    },
]

MOCK_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX", "SPY", "QQQ"]
MOCK_ASSET_DESCRIPTIONS = [
    "Apple Inc. - Common Stock",
    "Microsoft Corporation - Common Stock",
    "Alphabet Inc. - Class A Common Stock",
    "Amazon.com Inc. - Common Stock",
    "Tesla Inc. - Common Stock",
    "Meta Platforms Inc. - Class A Common Stock",
    "NVIDIA Corporation - Common Stock",
    "Netflix Inc. - Common Stock",
    "SPDR S&P 500 ETF Trust",
    "Invesco QQQ Trust",
]

def generate_mock_trade(trade_id: int) -> Dict[str, Any]:
    """Generate a mock trade for development."""
    member = random.choice(MOCK_MEMBERS)
    ticker = random.choice(MOCK_TICKERS)
    asset_desc = random.choice(MOCK_ASSET_DESCRIPTIONS)
    
    # Generate random dates
    base_date = datetime.now() - timedelta(days=random.randint(1, 365))
    
    return {
        "id": trade_id,
        "member_id": member["id"],
        "member": member,
        "disclosure_date": base_date.strftime("%Y-%m-%d"),
        "transaction_date": (base_date - timedelta(days=random.randint(1, 45))).strftime("%Y-%m-%d"),
        "owner": random.choice(["SP", "JT", "DC", "C"]),
        "ticker": ticker if random.random() > 0.15 else None,  # 15% chance of missing ticker
        "asset_description": asset_desc,
        "asset_type": "Stock",
        "type": random.choice(["purchase", "sale", "exchange"]),
        "amount": random.choice([
            "$1,001 - $15,000",
            "$15,001 - $50,000",
            "$50,001 - $100,000",
            "$100,001 - $250,000",
            "$250,001 - $500,000",
            "$500,001 - $1,000,000",
            "$1,000,001 - $5,000,000",
        ]),
        "amount_min": random.randint(1000, 100000),
        "amount_max": random.randint(100000, 5000000),
        "comment": None,
        "ptr_link": f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{random.randint(2023, 2024)}/{random.randint(10000, 99999)}.pdf",
        "created_at": base_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at": base_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

@router.get("/trades")
async def get_trades_dev(
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    party: Optional[str] = Query(None, description="Party filter"),
    chamber: Optional[str] = Query(None, description="Chamber filter"),
    type: Optional[str] = Query(None, description="Transaction type filter"),
    ticker: Optional[str] = Query(None, description="Ticker filter"),
    owner: Optional[str] = Query(None, description="Owner filter"),
    date_from: Optional[str] = Query(None, description="Date from filter"),
    date_to: Optional[str] = Query(None, description="Date to filter"),
) -> JSONResponse:
    """
    Development endpoint for congressional trades (no auth required).
    """
    logger.info(f"Getting trades for development: page={page}, per_page={per_page}")
    
    # Generate mock trades
    total_trades = 25000  # Simulate 25k trades
    trades = []
    
    start_id = (page - 1) * per_page + 1
    for i in range(per_page):
        trades.append(generate_mock_trade(start_id + i))
    
    # Apply simple filters
    if search:
        trades = [t for t in trades if search.lower() in t.get("member", {}).get("full_name", "").lower() or
                  search.lower() in (t.get("ticker") or "").lower()]
    
    if party:
        trades = [t for t in trades if t.get("member", {}).get("party") == party]
    
    if chamber:
        trades = [t for t in trades if t.get("member", {}).get("chamber") == chamber]
    
    if type:
        trades = [t for t in trades if t.get("type") == type]
    
    if ticker:
        trades = [t for t in trades if t.get("ticker") == ticker]
    
    if owner:
        trades = [t for t in trades if t.get("owner") == owner]
    
    response_data = {
        "items": trades,
        "total": total_trades,
        "page": page,
        "per_page": per_page,
        "pages": (total_trades + per_page - 1) // per_page,
        "has_next": page * per_page < total_trades,
        "has_prev": page > 1,
    }
    
    return JSONResponse(content=response_data)

@router.get("/members")
async def get_members_dev(
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
) -> JSONResponse:
    """
    Development endpoint for congress members (no auth required).
    """
    logger.info(f"Getting members for development: page={page}, per_page={per_page}")
    
    # Generate more mock members
    members = []
    for i in range(per_page):
        member = MOCK_MEMBERS[i % len(MOCK_MEMBERS)].copy()
        member["id"] = (page - 1) * per_page + i + 1
        members.append(member)
    
    response_data = {
        "items": members,
        "total": 535,  # Simulate 535 congress members
        "page": page,
        "per_page": per_page,
        "pages": (535 + per_page - 1) // per_page,
        "has_next": page * per_page < 535,
        "has_prev": page > 1,
    }
    
    return JSONResponse(content=response_data)

@router.get("/data-quality/stats")
async def get_data_quality_stats_dev(
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Development endpoint for data quality stats (no auth required).
    """
    logger.info("Getting data quality stats for development")
    
    stats = {
        "total_trades": 25000,
        "trades_with_ticker": 21250,
        "trades_without_ticker": 3750,
        "null_ticker_percentage": 15.0,
        "unique_members": 535,
        "unique_tickers": 1250,
        "amount_ranges": {
            "$1,001 - $15,000": 8500,
            "$15,001 - $50,000": 7200,
            "$50,001 - $100,000": 4800,
            "$100,001 - $250,000": 3200,
            "$250,001 - $500,000": 1000,
            "$500,001 - $1,000,000": 250,
            "$1,000,001 - $5,000,000": 50,
        },
        "party_distribution": {
            "Democratic": 12500,
            "Republican": 12000,
            "Independent": 500,
        },
        "chamber_distribution": {
            "House": 22000,
            "Senate": 3000,
        },
    }
    
    return JSONResponse(content=stats)

@router.get("/analytics/top-trading-members")
async def get_top_trading_members_dev(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(10, ge=1, le=100, description="Number of members to return"),
) -> JSONResponse:
    """
    Development endpoint for top trading members (no auth required).
    """
    logger.info(f"Getting top trading members for development: limit={limit}")
    
    members = MOCK_MEMBERS[:limit]
    return JSONResponse(content=members)

@router.get("/analytics/top-traded-tickers")
async def get_top_traded_tickers_dev(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(10, ge=1, le=100, description="Number of tickers to return"),
) -> JSONResponse:
    """
    Development endpoint for top traded tickers (no auth required).
    """
    logger.info(f"Getting top traded tickers for development: limit={limit}")
    
    tickers = [
        {"ticker": "AAPL", "count": 450, "total_value": 45000000},
        {"ticker": "MSFT", "count": 380, "total_value": 38000000},
        {"ticker": "GOOGL", "count": 320, "total_value": 32000000},
        {"ticker": "AMZN", "count": 280, "total_value": 28000000},
        {"ticker": "TSLA", "count": 250, "total_value": 25000000},
        {"ticker": "META", "count": 220, "total_value": 22000000},
        {"ticker": "NVDA", "count": 200, "total_value": 20000000},
        {"ticker": "NFLX", "count": 180, "total_value": 18000000},
        {"ticker": "SPY", "count": 160, "total_value": 16000000},
        {"ticker": "QQQ", "count": 140, "total_value": 14000000},
    ]
    
    return JSONResponse(content=tickers[:limit]) 