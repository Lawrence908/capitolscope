# 🗄️ CapitolScope Data Migration & Population Guide

This guide covers the complete process of populating your CapitolScope database with stock and congressional trading data.

## 📊 **Current Data Assets**

You have excellent existing data:

### **✅ Congressional Trading Data (2014-2025)**
- **Location**: `data/congress/csv/` 
- **Format**: CSV files (`2025FD.csv`, `2024FD.csv`, etc.)
- **Coverage**: 11+ years of congressional trading disclosures
- **Records**: ~20,000+ individual trades
- **SQLite Backup**: `data/congress/congress_trades.db`

### **✅ Congressional Member Information**
- **Source**: Extracted from trading data CSVs
- **Data**: Member names, some with chamber/party info
- **Count**: 500+ unique congress members over time

### **✅ Stock Data Infrastructure**
- **Scripts**: Relocated to `domains/securities/ingestion.py`
- **Sources**: Yahoo Finance, S&P 500, NASDAQ-100, Dow Jones
- **Coverage**: Major market indices + historically traded securities

---

## 🚀 **Migration Strategy & Execution Order**

### **Phase 1: Securities Database (Foundation)**
```bash
# 1. Seed major market securities (5-10 minutes)
python scripts/seed_securities_database.py

# 2. Optional: Include historical price data (30-60 minutes)
python scripts/seed_securities_database.py --prices
```

**Result**: ~500-800 securities with metadata and optionally 5+ years of daily prices

### **Phase 2: Congressional Data Import**
```bash
# Import from CSV files (recommended - processed data)
python scripts/import_congressional_data.py --csv-dir data/congress/csv

# Alternative: Import from SQLite database 
python scripts/import_congressional_data.py --sqlite data/congress/congress_trades.db

# Optional: Enrich member profiles with external APIs
python scripts/import_congressional_data.py --csv-dir data/congress/csv --enrich-members
```

**Result**: 500+ members, 20,000+ trades with proper relationships

### **Phase 3: Validation & Testing**
```bash
# Start the API server
cd app && python -m uvicorn main:app --reload

# Test the endpoints
curl http://localhost:8000/api/v1/members/
curl http://localhost:8000/api/v1/trades/
curl http://localhost:8000/api/v1/portfolios/

# Access API documentation
open http://localhost:8000/docs
```

---

## 📁 **File Structure Changes**

### **✅ Domain-Based Organization**

```
app/src/domains/
├── securities/
│   ├── ingestion.py          # ← Stock data fetching (from legacy/fetch_stock_data.py)
│   ├── models.py             # Securities, prices, exchanges
│   ├── services.py           # Business logic
│   └── crud.py               # Database operations
├── congressional/
│   ├── ingestion.py          # ← Congressional data import (from legacy/fetch_congress_data.py)
│   ├── models.py             # Members, trades, portfolios
│   ├── services.py           # Trading logic
│   └── crud.py               # Database operations
└── users/                    # ← Already completed
    ├── models.py             # Authentication, subscriptions
    └── ...
```

### **✅ Migration Scripts**

```
scripts/
├── seed_securities_database.py      # ← Major indices seeding
├── import_congressional_data.py     # ← CSV/SQLite data import
├── setup_database.py               # ← Database initialization
└── test_connection.py              # ← Connection testing
```

### **📦 Legacy Files (Preserved)**

```
legacy/ingestion/
├── fetch_stock_data.py              # ← Original stock fetching
├── fetch_congress_data.py           # ← Original PDF parsing & download
└── pdf_parsing_improvements.py     # ← PDF parsing utilities
```

---

## 🔧 **Technical Implementation Details**

### **Securities Ingestion (`domains/securities/ingestion.py`)**

**Features:**
- ✅ **Major Indices**: S&P 500, NASDAQ-100, Dow Jones from Wikipedia
- ✅ **Price Data**: Yahoo Finance integration for historical OHLC
- ✅ **Reference Data**: Asset types, exchanges, sectors auto-created
- ✅ **Error Handling**: Robust retry logic and validation
- ✅ **Batch Processing**: Configurable batch sizes for large datasets

**Usage:**
```python
from domains.securities.ingestion import StockDataIngester

async with get_db_session() as session:
    ingester = StockDataIngester(session)
    
    # Populate securities
    result = await ingester.populate_securities_database()
    
    # Fetch price data
    price_result = await ingester.ingest_price_data_for_all_securities()
```

### **Congressional Ingestion (`domains/congressional/ingestion.py`)**

**Features:**
- ✅ **CSV Import**: Direct import from your existing processed CSV files
- ✅ **SQLite Import**: Alternative import from SQLite database backup
- ✅ **Member Extraction**: Automatic member profile creation from trade data
- ✅ **Data Parsing**: Amount ranges, dates, transaction types
- ✅ **Security Linking**: Automatic linking to securities database via tickers
- ✅ **Asset Mapping**: Complete asset type dictionary from original script

**Data Transformations:**
```python
# Amount parsing: "$1,001 - $15,000" → min_cents: 100100, max_cents: 1500000
# Date parsing: Multiple formats supported (YYYY-MM-DD, MM/DD/YYYY, etc.)
# Member names: "Last, First" → proper first_name, last_name fields
# Ticker linking: Automatic security_id assignment where possible
```

---

## 📈 **Expected Data Volumes**

### **Post-Migration Database State:**

| **Domain** | **Table** | **Expected Records** | **Source** |
|------------|-----------|---------------------|------------|
| **Securities** | `securities` | ~800 | Major indices |
| | `daily_prices` | ~1M (if --prices) | Yahoo Finance |
| | `asset_types` | ~20 | Reference data |
| **Congressional** | `congress_members` | ~500 | Extracted from CSVs |
| | `congressional_trades` | ~20,000 | Your CSV files |
| **Users** | `users` | 1+ | Admin account |

### **Storage Requirements:**
- **Without Price Data**: ~50MB database
- **With Price Data**: ~500MB-1GB database
- **CSV Processing**: Temporary ~100MB memory usage

---

## 🧪 **Testing & Validation**

### **1. Data Integrity Checks**

```bash
# Check record counts
curl http://localhost:8000/api/v1/members/?limit=1 
# Should show: {"data": {"total": 500+}}

curl http://localhost:8000/api/v1/trades/?limit=1
# Should show: {"data": {"total": 20000+}}

# Check data quality
curl http://localhost:8000/api/v1/members/1
# Should show: complete member profile with names

curl http://localhost:8000/api/v1/trades/1  
# Should show: trade with member_id, security_id linkages
```

### **2. API Endpoint Testing**

```bash
# Test authentication (should work)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@capitolscope.com", "password": "password123"}'

# Test authenticated endpoints (with JWT token)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/portfolios/
```

### **3. Database Validation**

```sql
-- Connect to your Supabase database and run:

-- Check securities linkage
SELECT COUNT(*) as linked_trades 
FROM congressional_trades 
WHERE security_id IS NOT NULL;

-- Check member distribution
SELECT chamber, COUNT(*) as count 
FROM congress_members 
GROUP BY chamber;

-- Check trade date range
SELECT MIN(transaction_date), MAX(transaction_date) 
FROM congressional_trades;
```

---

## 🎯 **Post-Migration Next Steps**

### **Immediate (This Week)**
1. ✅ Run securities seeding
2. ✅ Import congressional data  
3. ✅ Validate API responses
4. ✅ Test authentication flow

### **Short Term (Next 2 Weeks)**
1. **Member Profile Enrichment**: Add chamber, party, state data from external APIs
2. **Portfolio Calculations**: Implement real portfolio performance metrics
3. **Price Data Updates**: Set up scheduled daily price ingestion
4. **Data Quality**: Add validation rules and error monitoring

### **Medium Term (Next Month)**
1. **Advanced Analytics**: Complete CAP-26 portfolio engine
2. **Real-time Updates**: Implement live congressional data monitoring
3. **Email Notifications**: Complete CAP-14 & CAP-15 alert system
4. **Frontend Development**: Start CAP-27 TradingView charts

---

## 🆘 **Troubleshooting**

### **Common Issues & Solutions**

**🔴 Securities Seeding Fails**
```bash
# Check internet connection and run with debug logging
python scripts/seed_securities_database.py --log-level DEBUG

# Alternative: Run without prices first
python scripts/seed_securities_database.py  # Securities only
```

**🔴 Congressional Import Fails**
```bash
# Verify CSV files exist
ls -la data/congress/csv/*FD.csv

# Check for permission issues
python scripts/import_congressional_data.py --csv-dir data/congress/csv --log-level DEBUG
```

**🔴 Database Connection Issues**
```bash
# Test database connection
python scripts/test_connection.py

# Check environment variables
echo $DATABASE_URL
echo $SUPABASE_URL
```

**🔴 API Returns Empty Data**
```bash
# Check database has data
python scripts/import_congressional_data.py --csv-dir data/congress/csv

# Verify authentication setup
curl http://localhost:8000/api/v1/auth/me
```

### **Performance Optimization**

```bash
# For large datasets, use batch processing
python scripts/seed_securities_database.py --batch-size 100

# For faster CSV import, skip member enrichment initially
python scripts/import_congressional_data.py --csv-dir data/congress/csv
# Run enrichment separately later:
python scripts/import_congressional_data.py --enrich-members
```

---

## 🎉 **Success Indicators**

You'll know the migration is successful when:

✅ **Securities Database**: ~800 securities from major indices  
✅ **Congressional Data**: 500+ members, 20,000+ trades  
✅ **API Responses**: Real data instead of placeholder responses  
✅ **Authentication**: JWT tokens working in Swagger UI  
✅ **Data Relationships**: Trades linked to securities and members  
✅ **Performance**: API responses under 500ms  

Your CapitolScope platform will then be ready for frontend development and advanced features! 🚀 