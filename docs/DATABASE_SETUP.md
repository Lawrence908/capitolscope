# CapitolScope Database Setup Guide

This guide covers the setup and usage of the PostgreSQL database system for CapitolScope.

## 🗄️ Database Architecture

Our PostgreSQL database is designed to support all features outlined in the Linear tickets:

### Core Tables:
- **Securities Master Data**: `securities`, `asset_types`, `exchanges`, `sectors`
- **Congressional Data**: `congress_members`, `congressional_trades`
- **Price Data**: `daily_prices`, `corporate_actions`
- **Portfolio Tracking**: `member_portfolios`, `portfolio_performance`
- **User Management**: `users`, `subscriptions`, `user_preferences`
- **Community Features**: `discussion_topics`, `discussion_posts`, `trade_discussions`
- **Email System**: `email_campaigns`, `email_sends`
- **System Monitoring**: `ingestion_logs`, `api_usage`

## 🚀 Quick Start

### 1. Environment Setup

Create a `.env` file based on the example:

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
DATABASE_URL=postgresql://capitolscope:your_password@localhost:5432/capitolscope
POSTGRES_PASSWORD=your_secure_password
ALPHA_VANTAGE_API_KEY=your_api_key
```

### 2. Start PostgreSQL Database

```bash
# Start the database with Docker
docker-compose up db -d

# Check database health
docker-compose logs db
```

### 3. Initialize Database Schema

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database tables and reference data
python scripts/init_database.py
```

### 4. Migrate Existing Data (Optional)

If you have existing SQLite data:

```bash
# Migrate from SQLite to PostgreSQL
python scripts/migrate_from_sqlite.py
```

## 📊 Database Schema Overview

### Securities Master Data

```sql
-- Main securities table with comprehensive metadata
CREATE TABLE securities (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    asset_type_id INTEGER REFERENCES asset_types(id),
    sector_id INTEGER REFERENCES sectors(id),
    exchange_id INTEGER REFERENCES exchanges(id),
    market_cap BIGINT, -- in cents for precision
    metadata JSONB -- flexible additional data
);
```

### Congressional Trading Data

```sql
-- Normalized congressional trades with data quality tracking
CREATE TABLE congressional_trades (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES congress_members(id),
    security_id INTEGER REFERENCES securities(id),
    transaction_date DATE NOT NULL,
    amount_min INTEGER, -- range in cents
    amount_max INTEGER,
    ticker_confidence DECIMAL(3,2), -- parsing confidence
    parsed_successfully BOOLEAN DEFAULT TRUE
);
```

### Price Data Storage

```sql
-- Optimized for time-series queries
CREATE TABLE daily_prices (
    id BIGSERIAL PRIMARY KEY,
    security_id INTEGER NOT NULL REFERENCES securities(id),
    date DATE NOT NULL,
    close_price INTEGER NOT NULL, -- in cents
    volume BIGINT NOT NULL,
    UNIQUE(security_id, date)
);
```

## 🔧 Using the Database

### Database Connection

```python
from src.database.connection import init_database, db_manager

# Initialize connection
init_database()

# Use in your code
with db_manager.session_scope() as session:
    trades = session.query(CongressionalTrade).limit(10).all()
```

### ORM Models

```python
from src.database.models import CongressMember, CongressionalTrade, Security

# Query congressional trades with member info
with db_manager.session_scope() as session:
    trades = session.query(CongressionalTrade)\
                   .join(CongressMember)\
                   .filter(CongressMember.party == 'D')\
                   .all()
```

### Common Queries

```python
# Get top trading members
top_traders = session.query(
    CongressMember.full_name,
    func.count(CongressionalTrade.id).label('trade_count')
)\
.join(CongressionalTrade)\
.group_by(CongressMember.id)\
.order_by(desc('trade_count'))\
.limit(10).all()

# Get recent large trades
large_trades = session.query(CongressionalTrade)\
    .filter(CongressionalTrade.amount_min >= 100000)\
    .order_by(desc(CongressionalTrade.transaction_date))\
    .limit(50).all()
```

## 📈 Performance Optimizations

### Indexes
- All foreign keys are automatically indexed
- Composite indexes on `(security_id, date)` for price data
- Text search indexes using trigrams for fuzzy matching
- Date-based indexes for time-series queries

### Query Optimization Tips

```python
# Use eager loading for related data
trades_with_members = session.query(CongressionalTrade)\
    .options(joinedload(CongressionalTrade.member))\
    .all()

# Use bulk operations for large datasets
session.bulk_insert_mappings(DailyPrice, price_data_list)
```

## 🔄 Data Migration

### From SQLite to PostgreSQL

The migration script handles:
- ✅ Congressional members extraction and deduplication
- ✅ Securities master data creation
- ✅ Trade data migration with amount parsing
- ✅ Data quality tracking and error handling

```bash
# Run migration
python scripts/migrate_from_sqlite.py

# Check migration results
docker exec -it capitolscope-db psql -U capitolscope -d capitolscope -c "
SELECT 
    (SELECT COUNT(*) FROM congress_members) as members,
    (SELECT COUNT(*) FROM congressional_trades) as trades,
    (SELECT COUNT(*) FROM securities) as securities;
"
```

## 🏗️ Next Steps for CAP-24

Now that the database foundation is ready, CAP-24 (Comprehensive Stock Database Setup) can proceed with:

1. **Populate Securities Master Data**
   ```python
   # Use your existing stock data fetching
   from src.ingestion.fetch_stock_data import get_tickers, get_tickers_company_dict
   
   # Populate securities table with S&P 500, NASDAQ-100, Dow Jones
   tickers = get_tickers()
   # Insert into securities table with proper categorization
   ```

2. **Link Congressional Trades to Securities**
   ```python
   # Match existing trade tickers to securities table
   # Update congressional_trades.security_id
   ```

3. **Add Asset Type Classification**
   ```python
   # Classify securities by type (stocks, ETFs, bonds, crypto, etc.)
   # Update securities.asset_type_id based on ticker patterns
   ```

## 🛠️ Development Workflow

### Database Changes
1. Modify `schema/database_schema.sql` for structure changes
2. Update `src/database/models.py` for ORM changes
3. Create migration scripts for existing data
4. Test with development data

### Adding New Features
```python
# Example: Adding a new table
class NewFeature(Base):
    __tablename__ = 'new_features'
    id = Column(Integer, primary_key=True)
    # ... other fields
```

## 📋 Maintenance

### Backup
```bash
# Create backup
docker exec capitolscope-db pg_dump -U capitolscope capitolscope > backup.sql

# Restore backup
docker exec -i capitolscope-db psql -U capitolscope capitolscope < backup.sql
```

### Monitoring
```python
# Check ingestion logs
with db_manager.session_scope() as session:
    recent_logs = session.query(IngestionLog)\
        .order_by(desc(IngestionLog.started_at))\
        .limit(10).all()
```

## 🔐 Security Considerations

- All passwords stored as hashes using bcrypt
- UUIDs for user IDs to prevent enumeration
- Prepared statements prevent SQL injection
- Connection pooling with reasonable limits
- API usage tracking for rate limiting

---

**Ready to implement CAP-24!** 🚀

The database foundation is now solid and ready for the comprehensive stock database setup. The normalized structure will make portfolio calculations, performance tracking, and TradingView-style charts much more efficient. 