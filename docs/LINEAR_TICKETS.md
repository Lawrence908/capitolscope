# CapitolScope Linear Tickets

## 🎯 **EPIC: Core Transaction Viewing System**

### **CAP-10: Transaction List Page**
**Priority:** High  
**Estimate:** 3 days  
**Labels:** `frontend`, `core-feature`

**Description:**
Create a main transactions page that displays all congressional trading data in a sortable, filterable table.

**Acceptance Criteria:**
- [ ] Display transactions in a paginated table
- [ ] Sort by congress member, date, amount, ticker
- [ ] Filter by member, date range, transaction type
- [ ] Search functionality across all fields
- [ ] Export to CSV/Excel
- [ ] Responsive design for mobile/desktop

**Technical Requirements:**
- React/Next.js frontend
- API endpoint for transaction data
- Database queries with proper indexing
- Real-time updates for new transactions

---

### **CAP-11: Individual Member Profile Page**
**Priority:** High  
**Estimate:** 4 days  
**Labels:** `frontend`, `member-profile`

**Description:**
Create detailed profile pages for each congress member showing their trading history and portfolio.

**Acceptance Criteria:**
- [ ] Member information (name, district, party)
- [ ] Complete trading history timeline
- [ ] Portfolio summary (current holdings)
- [ ] Transaction statistics (total trades, amounts)
- [ ] Performance metrics
- [ ] Related news/headlines

**Technical Requirements:**
- Dynamic routing (`/member/[id]`)
- Portfolio calculation logic
- Performance analytics
- News API integration

---

## 📈 **EPIC: Stock Database & Price Tracking Infrastructure**

### **CAP-24: Comprehensive Stock Database Setup**
**Priority:** High  
**Estimate:** 5 days  
**Labels:** `backend`, `database`, `stocks`, `foundation`

**Description:**
Build a comprehensive stock database covering all assets traded by congress members, with daily price tracking to enable TradingView-style charts and performance analytics.

**Acceptance Criteria:**
- [ ] Stock database with all S&P 500 companies
- [ ] Dow Jones Industrial Average coverage
- [ ] NASDAQ-100 major companies
- [ ] US Treasury bills, notes, and bonds
- [ ] Corporate bonds and municipal securities
- [ ] ETFs and mutual funds commonly traded
- [ ] Cryptocurrency tracking for disclosed crypto trades
- [ ] REITs and commodity funds
- [ ] Stock metadata (company name, sector, market cap, etc.)

**Technical Requirements:**
- PostgreSQL database with optimized schema
- Ticker symbol standardization and validation
- Company information from reliable data sources
- Sector and industry classification
- Market capitalization tracking
- Asset type categorization

---

### **CAP-25: Daily Price Data Ingestion System**
**Priority:** High  
**Estimate:** 6 days  
**Labels:** `backend`, `data-ingestion`, `automation`

**Description:**
Create an automated system to fetch and store daily price data for all tracked securities, enabling historical performance analysis and real-time portfolio valuation.

**Acceptance Criteria:**
- [ ] Daily OHLC (Open, High, Low, Close) price data
- [ ] Volume data for all tracked securities
- [ ] Dividend and split adjustment handling
- [ ] Historical data backfill (5+ years)
- [ ] Real-time intraday price updates
- [ ] Treasury yield curve data
- [ ] Bond price and yield tracking
- [ ] ETF/mutual fund NAV tracking
- [ ] Data validation and error handling
- [ ] Automated retry mechanisms for failed fetches

**Technical Requirements:**
- Financial data API integration (Alpha Vantage, Polygon, Yahoo Finance)
- Scheduled data ingestion (daily cron jobs)
- Data validation and cleaning pipeline
- Historical data storage optimization
- Rate limiting and API quota management
- Backup data sources for reliability

---

### **CAP-26: Portfolio Performance Engine**
**Priority:** Medium  
**Estimate:** 4 days  
**Labels:** `backend`, `analytics`, `performance`

**Description:**
Build the core engine that calculates portfolio performance, gains/losses, and benchmarking for congressional trades using the stock price database.

**Acceptance Criteria:**
- [ ] Real-time portfolio valuation
- [ ] Historical performance calculation
- [ ] Unrealized/realized gains tracking
- [ ] Benchmark comparison (S&P 500, sector indices)
- [ ] Risk-adjusted returns (Sharpe ratio, etc.)
- [ ] Dividend income tracking
- [ ] Cost basis calculation with FIFO/LIFO
- [ ] Portfolio diversification metrics
- [ ] Performance attribution analysis

**Technical Requirements:**
- Efficient portfolio calculation algorithms
- Real-time price integration
- Historical performance computation
- Benchmark data integration
- Risk metrics calculation
- Tax-loss harvesting analysis

---

## 📊 **EPIC: Portfolio Visualization**

### **CAP-27: TradingView-Style Stock Charts**
**Priority:** Medium  
**Estimate:** 5 days  
**Labels:** `frontend`, `charts`, `visualization`

**Description:**
Create interactive stock charts similar to TradingView that show congressional trades overlaid on price movements, providing immediate context for trading decisions.

**Acceptance Criteria:**
- [ ] Interactive candlestick/line charts
- [ ] Congressional trade markers on timeline
- [ ] Multiple timeframes (1D, 1W, 1M, 1Y, 5Y)
- [ ] Technical indicators (moving averages, RSI, MACD)
- [ ] Volume overlay charts
- [ ] Trade annotation with member details
- [ ] Buy/sell signal visualization
- [ ] Portfolio performance overlay
- [ ] Comparison with market indices
- [ ] Mobile-responsive chart interaction

**Technical Requirements:**
- TradingView widget integration or Chart.js
- Real-time data streaming
- Historical data visualization
- Trade event overlay system
- Performance calculation display
- Interactive tooltip system

---

### **CAP-12: Member Portfolio Dashboard**
**Priority:** Medium  
**Estimate:** 5 days  
**Labels:** `frontend`, `charts`, `portfolio`

**Description:**
Create a portfolio dashboard that shows a congress member's holdings like a personal investment account.

**Acceptance Criteria:**
- [ ] Interactive stock charts (like TradingView)
- [ ] Portfolio allocation pie chart
- [ ] Performance over time graph
- [ ] Holdings list with current values
- [ ] Transaction history timeline
- [ ] Risk metrics and analysis

**Technical Requirements:**
- Chart.js or TradingView integration
- Real-time stock price data
- Portfolio calculation engine
- Performance tracking algorithms

---

### **CAP-13: Portfolio Comparison Tool**
**Priority:** Low  
**Estimate:** 3 days  
**Labels:** `frontend`, `comparison`

**Description:**
Allow users to compare portfolios between different congress members.

**Acceptance Criteria:**
- [ ] Side-by-side portfolio comparison
- [ ] Overlap analysis (shared holdings)
- [ ] Performance benchmarking
- [ ] Risk comparison metrics
- [ ] Export comparison reports

---

## 📧 **EPIC: Email Notification System**

### **CAP-14: Email Newsletter Infrastructure**
**Priority:** Medium  
**Estimate:** 4 days  
**Labels:** `backend`, `email`, `notifications`

**Description:**
Build the email notification system for alerting users about significant congressional trades.

**Acceptance Criteria:**
- [ ] Email service integration (SendGrid/Mailgun)
- [ ] Newsletter template design
- [ ] Subscriber management system
- [ ] Email preferences (frequency, filters)
- [ ] Unsubscribe functionality
- [ ] Email analytics tracking

**Technical Requirements:**
- Email service API integration
- Template engine
- Subscriber database
- Email queue system

---

### **CAP-15: Trade Alert System**
**Priority:** Medium  
**Estimate:** 3 days  
**Labels:** `backend`, `alerts`

**Description:**
Create automated alerts for significant trades (large amounts, specific stocks, etc.).

**Acceptance Criteria:**
- [ ] Configurable alert thresholds
- [ ] Real-time trade monitoring
- [ ] Email notification triggers
- [ ] Alert history tracking
- [ ] User alert preferences

**Technical Requirements:**
- Real-time data processing
- Alert rule engine
- Notification queuing
- User preference management

---

## 💬 **EPIC: Community Features**

### **CAP-16: Message Board System**
**Priority:** Low  
**Estimate:** 6 days  
**Labels:** `frontend`, `backend`, `community`

**Description:**
Create a community message board where users can discuss congressional trading activity.

**Acceptance Criteria:**
- [ ] Thread-based discussion system
- [ ] User registration and profiles
- [ ] Moderation tools
- [ ] Rich text editor
- [ ] Search and filtering
- [ ] Mobile-responsive design

**Technical Requirements:**
- User authentication system
- Real-time messaging
- Content moderation
- Search functionality

---

### **CAP-17: Trade Discussion Threads**
**Priority:** Low  
**Estimate:** 2 days  
**Labels:** `frontend`, `integration`

**Description:**
Integrate discussion threads with individual trades and member profiles.

**Acceptance Criteria:**
- [ ] Auto-generated discussion threads for large trades
- [ ] Member profile discussion sections
- [ ] Stock-specific discussion boards
- [ ] Thread linking to related trades

---

## 💎 **EPIC: Premium Features**

### **CAP-18: Pro Features Infrastructure**
**Priority:** Medium  
**Estimate:** 5 days  
**Labels:** `backend`, `premium`, `billing`

**Description:**
Build the foundation for premium features and subscription management.

**Acceptance Criteria:**
- [ ] User subscription management
- [ ] Payment processing (Stripe)
- [ ] Feature access control
- [ ] Subscription analytics
- [ ] Billing history

**Technical Requirements:**
- Stripe integration
- Subscription management
- Feature gating system
- Analytics tracking

---

### **CAP-19: Advanced Analytics Dashboard**
**Priority:** Low  
**Estimate:** 7 days  
**Labels:** `frontend`, `premium`, `analytics`

**Description:**
Create advanced analytics features for premium users.

**Acceptance Criteria:**
- [ ] Advanced portfolio analytics
- [ ] Trading pattern analysis
- [ ] Insider trading correlation tools
- [ ] Custom alert configurations
- [ ] Data export capabilities
- [ ] API access for premium users

**Technical Requirements:**
- Advanced analytics engine
- Pattern recognition algorithms
- Custom reporting system
- API rate limiting

---

## 🔧 **EPIC: Technical Infrastructure**

### **CAP-20: API Development**
**Priority:** High  
**Estimate:** 4 days  
**Labels:** `backend`, `api`

**Description:**
Build RESTful API endpoints for all frontend features.

**Acceptance Criteria:**
- [ ] Transaction data endpoints
- [ ] Member profile endpoints
- [ ] Portfolio calculation endpoints
- [ ] Search and filtering endpoints
- [ ] API documentation
- [ ] Rate limiting and authentication

**Technical Requirements:**
- FastAPI or Django REST Framework
- JWT authentication
- API documentation (Swagger)
- Rate limiting

---

### **CAP-21: Database Schema Design**
**Priority:** High  
**Estimate:** 3 days  
**Labels:** `backend`, `database`

**Description:**
Design and implement the complete database schema for all features.

**Acceptance Criteria:**
- [ ] User management tables
- [ ] Transaction data tables
- [ ] Portfolio tracking tables
- [ ] Discussion board tables
- [ ] Subscription/billing tables
- [ ] Proper indexing for performance

**Technical Requirements:**
- PostgreSQL database
- Migration system
- Performance optimization
- Backup strategy

---

## 🚀 **EPIC: Deployment & DevOps**

### **CAP-22: Production Deployment**
**Priority:** High  
**Estimate:** 3 days  
**Labels:** `devops`, `deployment`

**Description:**
Deploy the application to production with proper monitoring and scaling.

**Acceptance Criteria:**
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Production environment setup
- [ ] Monitoring and logging
- [ ] SSL certificate setup
- [ ] Domain configuration

**Technical Requirements:**
- AWS/GCP deployment
- Docker containers
- CI/CD pipeline
- Monitoring tools

---

### **CAP-23: Performance Optimization**
**Priority:** Medium  
**Estimate:** 4 days  
**Labels:** `performance`, `optimization`

**Description:**
Optimize application performance for large datasets and high traffic.

**Acceptance Criteria:**
- [ ] Database query optimization
- [ ] Frontend performance improvements
- [ ] Caching implementation
- [ ] CDN setup
- [ ] Load testing
- [ ] Performance monitoring

---

## 📋 **MILESTONE: Foundation (Stock DB + Basic Features)**
**Target Date:** 6 weeks  
**Total Estimate:** 25 days
**Critical Path:** CAP-24 → CAP-25 → CAP-10 → CAP-11

**Tickets:**
- CAP-24: Comprehensive Stock Database Setup (5 days)
- CAP-25: Daily Price Data Ingestion System (6 days)
- CAP-10: Transaction List Page (3 days)
- CAP-11: Individual Member Profile Page (4 days)
- CAP-20: API Development (4 days)
- CAP-21: Database Schema Design (3 days)

## 📋 **MILESTONE: Core Features (Charts + Performance)**
**Target Date:** 10 weeks  
**Total Estimate:** 18 days

**Tickets:**
- CAP-26: Portfolio Performance Engine (4 days)
- CAP-27: TradingView-Style Stock Charts (5 days)
- CAP-12: Member Portfolio Dashboard (5 days)
- CAP-14: Email Newsletter Infrastructure (4 days)

## 📋 **MILESTONE: Production Launch**
**Target Date:** 12 weeks  
**Total Estimate:** 10 days

**Tickets:**
- CAP-22: Production Deployment (3 days)
- CAP-23: Performance Optimization (4 days)
- CAP-15: Trade Alert System (3 days)

## 📋 **MILESTONE: Community & Premium (CAP-16, CAP-18, CAP-19)**
**Target Date:** 16 weeks  
**Total Estimate:** 18 days

---

## 🎯 **Priority Matrix:**

**Critical Foundation (Must Have First):**
- CAP-24: Comprehensive Stock Database Setup
- CAP-25: Daily Price Data Ingestion System
- CAP-20: API Development
- CAP-21: Database Schema Design

**High Priority (Launch Critical):**
- CAP-10: Transaction List Page
- CAP-11: Individual Member Profile Page
- CAP-22: Production Deployment

**Medium Priority (Core Features):**
- CAP-26: Portfolio Performance Engine
- CAP-27: TradingView-Style Stock Charts
- CAP-12: Member Portfolio Dashboard
- CAP-14: Email Newsletter Infrastructure
- CAP-15: Trade Alert System
- CAP-18: Pro Features Infrastructure
- CAP-23: Performance Optimization

**Low Priority (Enhancement):**
- CAP-13: Portfolio Comparison Tool
- CAP-16: Message Board System
- CAP-17: Trade Discussion Threads
- CAP-19: Advanced Analytics Dashboard 