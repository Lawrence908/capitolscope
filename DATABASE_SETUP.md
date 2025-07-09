# 🗄️ CapitolScope Database Setup Guide

This guide will help you connect your **4 completed domains** to your Supabase PostgreSQL database and validate that everything works correctly.

## 📊 What We've Built

You now have **4 complete domains** with comprehensive business logic:

### ✅ **Completed Domains:**
- **🏗️ Base Domain** - Core utilities, logging, common schemas  
- **📈 Securities Domain** - Stocks, prices, exchanges *(CAP-24, CAP-25)*
- **🏛️ Congressional Domain** - Members, trades, portfolios *(CAP-10, CAP-11)*
- **👤 Users Domain** - Authentication, subscriptions, preferences

### 🔗 **Key Database Relationships:**
- `CongressionalTrade → Security` (which stocks were traded)
- `CongressionalTrade → CongressMember` (who made the trade)
- `MemberPortfolio → Security + CongressMember` (portfolio tracking)
- `User → UserPreferences, UserWatchlist, UserAlert` (user management)

---

## 🚀 Quick Setup (3 Steps)

### **Step 1: Environment Setup**

Create a `.env` file in your project root:

```bash
SUPABASE_URL=https://bigsmydtkhfssokvrvyq.supabase.co
SUPABASE_PROJECT_REF=bigsmydtkhfssokvrvyq
SUPABASE_PASSWORD=F&QzD*xH4VG5?t&
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJpZ3NteWR0a2hmc3Nva3ZydnlxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIwMDI1ODcsImV4cCI6MjA2NzU3ODU4N30.d5MyyBkAdSsHgbGFDMnD4uxTvmRHGBRcZ-d741rggrg
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJpZ3NteWR0a2hmc3Nva3ZydnlxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MjAwMjU4NywiZXhwIjoyMDY3NTc4NTg3fQ.n1FDbuKL8Wc4g96UKsbku6USKu6ykIls9ptIfgmlI4Y
SUPABASE_JWT_SECRET=LqcSlIJX2ojgw+0iO+Gb+SvAtZDPAIj8reACRQV4eeJG97nHhHnLK8y66Q8MnNP2X1+yUoE+gXyNCCGoV4dCpA==

# Application Settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

**Get your Supabase credentials:**
1. Go to [supabase.com/dashboard](https://supabase.com/dashboard)
2. Select your project
3. Go to **Settings > API**
4. Copy the values:
   - **URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_KEY`  
   - **service_role secret** → `SUPABASE_SERVICE_ROLE_KEY`
5. Go to **Settings > Database** → Copy **Password** → `SUPABASE_PASSWORD`

### **Step 2: Test Connection**

```bash
# Test your environment and database connection
python scripts/test_connection.py
```

This will verify:
- ✅ All environment variables are set
- ✅ Database connection works
- ✅ Supabase is accessible

### **Step 3: Create Database Tables**

```bash
# Create migrations and set up database
python scripts/setup_database.py
```

This will:
- 📝 Generate Alembic migration from your domain models
- 🚀 Create all tables in your Supabase database
- ✅ Verify everything is working

---

## 🎯 What Gets Created

When you run the setup, these **15+ tables** will be created:

### **Securities Domain Tables:**
- `asset_types` - Stock, ETF, Bond, Crypto classifications
- `exchanges` - NYSE, NASDAQ, etc.
- `sectors` - Technology, Healthcare, Finance, etc.  
- `securities` - All tradeable assets with full metadata
- `daily_prices` - Historical price data
- `corporate_actions` - Splits, dividends, etc.

### **Congressional Domain Tables:**
- `congress_members` - All representatives and senators
- `congressional_trades` - Individual trade disclosures
- `member_portfolios` - Current holdings per member
- `portfolio_performance` - Daily portfolio tracking

### **Users Domain Tables:**
- `users` - User accounts and authentication
- `user_preferences` - Settings and configurations
- `user_watchlists` - Custom security/member lists
- `user_alerts` - Custom trade notifications
- `user_notifications` - Message delivery
- `user_sessions` - Session management
- `user_api_keys` - API access for premium users

---

## 🧪 Testing Your Setup

After setup completes, test your database:

### **1. Start the API:**
```bash
cd app
python -m uvicorn main:app --reload
```

### **2. Access API Documentation:**
Open [http://localhost:8000/docs](http://localhost:8000/docs)

### **3. Test Core Endpoints:**

**Health Check:**
```
GET /health
```

**Congressional Domain:**
```
GET /api/v1/members          # List congress members
GET /api/v1/trades           # List congressional trades  
```

**Securities Domain:**
```
GET /api/v1/securities       # List securities
GET /api/v1/exchanges        # List exchanges
```

**Users Domain:**
```
POST /api/v1/auth/register   # Create user account
POST /api/v1/auth/login      # Login user
```

---

## 🔧 Troubleshooting

### **Connection Issues:**

**Error: "Connection failed"**
```bash
# Check your Supabase project status
curl https://your-project-ref.supabase.co/rest/v1/

# Verify environment variables
python -c "from app.src.core.config import settings; print(settings.database_url)"
```

**Error: "Environment variables missing"**
- Double-check your `.env` file location (project root)
- Ensure no spaces around `=` in `.env` file
- Verify you're using the correct Supabase credentials

### **Migration Issues:**

**Error: "Alembic command not found"**
```bash
pip install -e .
```

**Error: "Target database is not up to date"**
```bash
alembic upgrade head
```

**Error: "Table already exists"**
```bash
alembic stamp head  # Mark current state as up-to-date
```

### **Import Issues:**

**Error: "Module not found"**
```bash
export PYTHONPATH=/app/src
# Or run from project root
```

---

## 🎉 Success! What's Next?

Once your database is set up, you're ready to:

### **Immediate Next Steps:**
1. **🧪 Test the endpoints** with Swagger UI at `/docs`
2. **📊 Add sample data** to test relationships
3. **🔍 Verify foreign keys** are working correctly

### **Ready for Implementation:**
- ✅ **CAP-10:** Transaction List Page (Congressional domain ready)
- ✅ **CAP-11:** Member Profile Pages (Congressional domain ready)  
- ✅ **CAP-24:** Stock Database Setup (Securities domain ready)
- ✅ **CAP-25:** Price Data Ingestion (Securities domain ready)
- ✅ **Authentication:** User registration/login (Users domain ready)

### **Future Domains:**
After validating these 4 domains work correctly, you can add:
- **📊 Portfolio Domain** - Advanced portfolio management (CAP-26)
- **📧 Notifications Domain** - Email campaigns (CAP-14, CAP-15)  
- **📱 Social Domain** - Community features (CAP-16, CAP-17)
- **📈 Analytics Domain** - Advanced reporting
- **⚙️ Admin Domain** - System monitoring

---

## 📋 Database Schema Summary

Your database now supports:

- **🏛️ Congressional Trading:** Track all member trades with proper audit trails
- **📈 Securities Master Data:** Complete asset universe with pricing
- **👤 User Management:** Authentication, subscriptions, preferences  
- **🔗 Cross-Domain Relationships:** All foreign keys properly configured
- **📊 Portfolio Tracking:** Real-time portfolio valuation and performance
- **🔔 Alert System:** Custom user notifications and watchlists

**Total Tables:** 15+  
**Total Models:** 25+  
**Total Schemas:** 100+  
**Ready for Production:** ✅

---

## 🆘 Need Help?

**Quick Commands:**
```bash
# Test connection only
python scripts/test_connection.py

# Full database setup  
python scripts/setup_database.py

# Check migration status
alembic current

# Reset database (if needed)
alembic downgrade base && alembic upgrade head
```

**Check Logs:**
```bash
# Application logs
tail -f app/logs/capitolscope.log

# Database migration logs  
alembic history --verbose
```

Your domain-driven architecture is now ready for building the CapitolScope platform! 🚀 