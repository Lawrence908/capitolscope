-- CapitolScope Database Schema
-- PostgreSQL 14+ Compatible
-- 
-- This schema supports:
-- 1. Securities master data (stocks, bonds, ETFs, crypto, etc.)
-- 2. Congressional trading data with proper normalization
-- 3. User management and subscriptions
-- 4. Daily price data with optimal indexing
-- 5. Portfolio tracking and performance calculation
-- 6. Community features (discussions, comments)
-- 7. Email notifications and preferences
-- 8. API usage tracking and monitoring

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- SECURITIES MASTER DATA
-- ============================================================================

-- Asset types (stocks, bonds, ETFs, etc.)
CREATE TABLE asset_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(5) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Market sectors
CREATE TABLE sectors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    gics_code VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Market exchanges
CREATE TABLE exchanges (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(3) NOT NULL, -- ISO 3166-1 alpha-3
    timezone VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Securities master table (stocks, bonds, ETFs, etc.)
CREATE TABLE securities (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    asset_type_id INTEGER REFERENCES asset_types(id),
    sector_id INTEGER REFERENCES sectors(id),
    exchange_id INTEGER REFERENCES exchanges(id),
    currency VARCHAR(3) DEFAULT 'USD',
    market_cap BIGINT, -- Market cap in cents
    shares_outstanding BIGINT,
    is_active BOOLEAN DEFAULT TRUE,
    isin VARCHAR(12), -- International Securities Identification Number
    cusip VARCHAR(9), -- Committee on Uniform Securities Identification Procedures
    figi VARCHAR(12), -- Financial Instrument Global Identifier
    metadata JSONB, -- Additional metadata (earnings dates, dividends, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, exchange_id)
);

-- ============================================================================
-- CONGRESSIONAL DATA
-- ============================================================================

-- Congressional members
CREATE TABLE congress_members (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    party VARCHAR(1) CHECK (party IN ('D', 'R', 'I')), -- Democrat, Republican, Independent
    chamber VARCHAR(6) CHECK (chamber IN ('House', 'Senate')),
    state VARCHAR(2), -- Two-letter state code
    district VARCHAR(10), -- For House members
    bioguide_id VARCHAR(10) UNIQUE, -- Official bioguide ID
    congress_gov_id VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    term_start DATE,
    term_end DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Congressional trading transactions
CREATE TABLE congressional_trades (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES congress_members(id),
    security_id INTEGER REFERENCES securities(id),
    doc_id VARCHAR(50) NOT NULL, -- Document ID from House/Senate filing
    owner VARCHAR(10) CHECK (owner IN ('SP', 'JT', 'DC', 'C')), -- Spouse, Joint, Dependent Child, Child
    raw_asset_description TEXT, -- Original asset description from filing
    ticker VARCHAR(20), -- Parsed ticker symbol
    transaction_type VARCHAR(2) CHECK (transaction_type IN ('P', 'S', 'E')), -- Purchase, Sale, Exchange
    transaction_date DATE NOT NULL,
    notification_date DATE NOT NULL,
    amount_min INTEGER, -- Amount in cents (minimum)
    amount_max INTEGER, -- Amount in cents (maximum)
    amount_exact INTEGER, -- Exact amount if disclosed
    filing_status VARCHAR(1) CHECK (filing_status IN ('N', 'P', 'A')), -- New, Partial, Amendment
    comment TEXT,
    cap_gains_over_200 BOOLEAN DEFAULT FALSE, -- Capital gains over $200
    
    -- Data quality tracking
    ticker_confidence DECIMAL(3,2), -- Confidence in ticker parsing (0.0-1.0)
    amount_confidence DECIMAL(3,2), -- Confidence in amount parsing
    parsed_successfully BOOLEAN DEFAULT TRUE,
    parsing_notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- PRICE DATA
-- ============================================================================

-- Daily price data (OHLCV)
CREATE TABLE daily_prices (
    id BIGSERIAL PRIMARY KEY,
    security_id INTEGER NOT NULL REFERENCES securities(id),
    date DATE NOT NULL,
    open_price INTEGER NOT NULL, -- Price in cents
    high_price INTEGER NOT NULL,
    low_price INTEGER NOT NULL,
    close_price INTEGER NOT NULL,
    adjusted_close INTEGER, -- Split/dividend adjusted
    volume BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(security_id, date)
);

-- Split and dividend adjustments
CREATE TABLE corporate_actions (
    id SERIAL PRIMARY KEY,
    security_id INTEGER NOT NULL REFERENCES securities(id),
    action_type VARCHAR(20) NOT NULL CHECK (action_type IN ('split', 'dividend', 'spinoff', 'merger')),
    ex_date DATE NOT NULL,
    record_date DATE,
    payment_date DATE,
    ratio DECIMAL(10,6), -- For splits (e.g., 2.0 for 2:1 split)
    amount INTEGER, -- Dividend amount in cents
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- PORTFOLIO TRACKING
-- ============================================================================

-- Calculated member portfolios (derived from trades)
CREATE TABLE member_portfolios (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES congress_members(id),
    security_id INTEGER NOT NULL REFERENCES securities(id),
    shares DECIMAL(15,6) NOT NULL DEFAULT 0, -- Current position
    cost_basis INTEGER NOT NULL DEFAULT 0, -- Total cost basis in cents
    avg_cost_per_share INTEGER, -- Average cost per share in cents
    first_purchase_date DATE,
    last_transaction_date DATE,
    unrealized_gain_loss INTEGER, -- Current unrealized gain/loss in cents
    realized_gain_loss INTEGER DEFAULT 0, -- Total realized gains in cents
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(member_id, security_id)
);

-- Portfolio performance snapshots (daily/weekly/monthly)
CREATE TABLE portfolio_performance (
    id BIGSERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES congress_members(id),
    date DATE NOT NULL,
    total_value INTEGER NOT NULL, -- Total portfolio value in cents
    total_cost_basis INTEGER NOT NULL,
    unrealized_gain_loss INTEGER NOT NULL,
    realized_gain_loss INTEGER NOT NULL,
    daily_return DECIMAL(8,6), -- Daily return percentage
    benchmark_return DECIMAL(8,6), -- S&P 500 return for comparison
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(member_id, date)
);

-- ============================================================================
-- USER MANAGEMENT
-- ============================================================================

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    subscription_tier VARCHAR(20) DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro', 'premium')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- User subscriptions
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired', 'past_due')),
    current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    stripe_subscription_id VARCHAR(100) UNIQUE,
    stripe_customer_id VARCHAR(100),
    amount INTEGER NOT NULL, -- Amount in cents
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User preferences
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email_notifications BOOLEAN DEFAULT TRUE,
    trade_alerts BOOLEAN DEFAULT FALSE,
    newsletter_frequency VARCHAR(20) DEFAULT 'weekly' CHECK (newsletter_frequency IN ('none', 'daily', 'weekly', 'monthly')),
    alert_threshold INTEGER DEFAULT 100000, -- Alert for trades above this amount (cents)
    watchlist_members INTEGER[], -- Array of member IDs to watch
    preferred_timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- ============================================================================
-- EMAIL NOTIFICATIONS
-- ============================================================================

-- Email campaigns/newsletters
CREATE TABLE email_campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    template_id VARCHAR(100),
    scheduled_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    recipient_count INTEGER DEFAULT 0,
    open_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'scheduled', 'sending', 'sent', 'failed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Individual email sends
CREATE TABLE email_sends (
    id BIGSERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES email_campaigns(id),
    user_id UUID REFERENCES users(id),
    email VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed')),
    external_id VARCHAR(100), -- SendGrid/Mailgun message ID
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    clicked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- COMMUNITY FEATURES
-- ============================================================================

-- Discussion boards/topics
CREATE TABLE discussion_topics (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',
    created_by UUID REFERENCES users(id),
    is_pinned BOOLEAN DEFAULT FALSE,
    is_locked BOOLEAN DEFAULT FALSE,
    post_count INTEGER DEFAULT 0,
    last_post_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Discussion posts
CREATE TABLE discussion_posts (
    id BIGSERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES discussion_topics(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    content TEXT NOT NULL,
    parent_post_id BIGINT REFERENCES discussion_posts(id), -- For replies
    is_edited BOOLEAN DEFAULT FALSE,
    edited_at TIMESTAMP WITH TIME ZONE,
    like_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trade-specific discussions
CREATE TABLE trade_discussions (
    id SERIAL PRIMARY KEY,
    trade_id INTEGER NOT NULL REFERENCES congressional_trades(id),
    topic_id INTEGER NOT NULL REFERENCES discussion_topics(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trade_id)
);

-- ============================================================================
-- SYSTEM TABLES
-- ============================================================================

-- Data ingestion logs
CREATE TABLE ingestion_logs (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL, -- 'congress', 'stock_prices', 'alpha_vantage', etc.
    batch_id UUID DEFAULT uuid_generate_v4(),
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    metadata JSONB,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- API usage tracking
CREATE TABLE api_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    endpoint VARCHAR(200) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Congressional trades indexes
CREATE INDEX idx_congressional_trades_member_id ON congressional_trades(member_id);
CREATE INDEX idx_congressional_trades_security_id ON congressional_trades(security_id);
CREATE INDEX idx_congressional_trades_transaction_date ON congressional_trades(transaction_date);
CREATE INDEX idx_congressional_trades_notification_date ON congressional_trades(notification_date);
CREATE INDEX idx_congressional_trades_ticker ON congressional_trades(ticker);
CREATE INDEX idx_congressional_trades_amount ON congressional_trades(amount_min, amount_max);

-- Price data indexes
CREATE INDEX idx_daily_prices_security_date ON daily_prices(security_id, date);
CREATE INDEX idx_daily_prices_date ON daily_prices(date);

-- Portfolio indexes
CREATE INDEX idx_member_portfolios_member_id ON member_portfolios(member_id);
CREATE INDEX idx_portfolio_performance_member_date ON portfolio_performance(member_id, date);

-- Securities indexes
CREATE INDEX idx_securities_ticker ON securities(ticker);
CREATE INDEX idx_securities_asset_type ON securities(asset_type_id);
CREATE INDEX idx_securities_active ON securities(is_active);

-- User indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_api_usage_user_endpoint ON api_usage(user_id, endpoint);

-- Text search indexes
CREATE INDEX idx_securities_name_trgm ON securities USING gin(name gin_trgm_ops);
CREATE INDEX idx_congress_members_name_trgm ON congress_members USING gin(full_name gin_trgm_ops);

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_securities_updated_at BEFORE UPDATE ON securities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_congress_members_updated_at BEFORE UPDATE ON congress_members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_congressional_trades_updated_at BEFORE UPDATE ON congressional_trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Complete trade information with member and security details
CREATE VIEW v_trade_details AS
SELECT 
    ct.id,
    ct.doc_id,
    cm.full_name as member_name,
    cm.party,
    cm.state,
    cm.chamber,
    s.ticker,
    s.name as security_name,
    at.name as asset_type,
    ct.transaction_type,
    ct.transaction_date,
    ct.notification_date,
    ct.amount_min,
    ct.amount_max,
    ct.amount_exact,
    ct.owner,
    ct.filing_status
FROM congressional_trades ct
JOIN congress_members cm ON ct.member_id = cm.id
LEFT JOIN securities s ON ct.security_id = s.id
LEFT JOIN asset_types at ON s.asset_type_id = at.id;

-- Current portfolio values
CREATE VIEW v_current_portfolios AS
SELECT 
    mp.member_id,
    cm.full_name as member_name,
    mp.security_id,
    s.ticker,
    s.name as security_name,
    mp.shares,
    mp.cost_basis,
    mp.avg_cost_per_share,
    dp.close_price as current_price,
    (mp.shares * dp.close_price / 100.0) as current_value,
    mp.unrealized_gain_loss
FROM member_portfolios mp
JOIN congress_members cm ON mp.member_id = cm.id
JOIN securities s ON mp.security_id = s.id
LEFT JOIN daily_prices dp ON s.id = dp.security_id 
    AND dp.date = (SELECT MAX(date) FROM daily_prices WHERE security_id = s.id)
WHERE mp.shares > 0;

-- ============================================================================
-- SAMPLE DATA INSERTION
-- ============================================================================

-- Insert asset types
INSERT INTO asset_types (code, name, description) VALUES
('ST', 'Stocks (including ADRs)', 'Common and preferred stocks including American Depositary Receipts'),
('EF', 'Exchange Traded Funds (ETF)', 'Exchange traded funds'),
('MF', 'Mutual Funds', 'Mutual funds and similar pooled investments'),
('GS', 'Government Securities and Agency Debt', 'US Treasury and agency securities'),
('CS', 'Corporate Securities (Bonds and Notes)', 'Corporate bonds and notes'),
('CT', 'Cryptocurrency', 'Digital assets and cryptocurrencies'),
('RE', 'Real Estate Invest. Trust (REIT)', 'Real estate investment trusts'),
('OP', 'Options', 'Stock and index options'),
('FU', 'Futures', 'Commodity and financial futures'),
('OT', 'Other', 'Other investment types not specified above');

-- Insert major exchanges
INSERT INTO exchanges (code, name, country, timezone) VALUES
('NYSE', 'New York Stock Exchange', 'USA', 'America/New_York'),
('NASDAQ', 'NASDAQ', 'USA', 'America/New_York'),
('AMEX', 'American Stock Exchange', 'USA', 'America/New_York'),
('OTC', 'Over The Counter', 'USA', 'America/New_York');

-- Insert sample sectors
INSERT INTO sectors (name, gics_code) VALUES
('Technology', '45'),
('Healthcare', '35'),
('Financials', '40'),
('Consumer Discretionary', '25'),
('Communication Services', '50'),
('Industrials', '20'),
('Consumer Staples', '30'),
('Energy', '10'),
('Utilities', '55'),
('Real Estate', '60'),
('Materials', '15'); 