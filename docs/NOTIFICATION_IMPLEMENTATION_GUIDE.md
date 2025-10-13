# 🚨 Trade Alert Notification System Implementation Guide

## 📋 **Project Overview**

**Goal:** Implement a comprehensive notification system that allows users to receive email alerts when congress members make trades, with specific focus on individual member tracking (like MTG for Kyle) and high-value trade alerts.

**Key Features:**
- Member-specific trade alerts (e.g., "Notify me when MTG trades")
- Amount-based alerts (e.g., "Notify me of all trades $1M+")
- Ticker-specific alerts (e.g., "Notify me when anyone trades TSLA")
- Email delivery with rich templates
- User preference management
- Real-time triggering from data ingestion

---

## 🏗️ **Architecture Overview**

```
Data Ingestion → Trade Detection → Alert Evaluation → Notification Delivery
     ↓              ↓                ↓                    ↓
Congress.gov   New Trade Found   Rule Matching      Email/SMS/Push
   API         → Trigger Event   → Find Users       → Send Alerts
```

### **Core Components:**

1. **Trade Detection Service** - Identifies new trades and trigger notification processing.
2. **Alert Rule Engine** - Evaluates which users should be notified.
3. **Notification Service** - Handles email delivery and templates.
4. **User Alert Management** - CRUD operations for alert preferences.
5. **Background Tasks** - Async processing and delivery.

---

## 📁 **File Structure & Implementation Plan**

### **Phase 1: Core Services (2-3 days)**

#### **1.1 Trade Detection Service**
```python
# File: app/src/domains/notifications/trade_detection.py
```

**Purpose:** Detect new trades and trigger notification processing.

**Key Methods:**
- `detect_new_trades(since_date)` - Find trades since last check
- `process_new_trade(trade)` - Handle individual new trade
- `batch_process_trades(trades)` - Process multiple trades efficiently

#### **1.2 Alert Rule Engine**
```python
# File: app/src/domains/notifications/alert_engine.py
```

**Purpose:** Evaluate which alert rules should trigger for a given trade.

**Key Methods:**
- `evaluate_member_alerts(trade)` - Find users watching specific member
- `evaluate_amount_alerts(trade)` - Find users with amount thresholds
- `evaluate_ticker_alerts(trade)` - Find users watching specific tickers
- `evaluate_combined_alerts(trade)` - Handle complex rule combinations

#### **1.3 Notification Service**
```python
# File: app/src/domains/notifications/notification_service.py
```

**Purpose:** Handle email delivery, templating, and delivery tracking.

**Key Methods:**
- `send_trade_alert_email(user, trade, alert_rule)` - Send individual alert
- `send_bulk_alerts(notifications)` - Send multiple alerts efficiently
- `generate_email_template(trade, user)` - Create email content
- `track_delivery_status(notification_id, status)` - Track delivery

### **Phase 2: Data Models & Schemas (1 day)**

#### **2.1 Enhanced Alert Models**
```python
# Update: app/src/domains/notifications/models.py
```

**New Models:**
- `TradeAlertRule` - User-defined alert rules
- `AlertTrigger` - Records of triggered alerts
- `NotificationDelivery` - Delivery tracking and status

#### **2.2 Alert Schemas**
```python
# File: app/src/domains/notifications/schemas.py
```

**New Schemas:**
- `TradeAlertRuleCreate` - Create new alert rules
- `AlertTriggerResponse` - Alert trigger details
- `NotificationDeliveryStatus` - Delivery tracking

### **Phase 3: API Endpoints (1 day)**

#### **3.1 Alert Management API**
```python
# Update: app/src/api/notifications.py
```

**New Endpoints:**
- `POST /alerts/member/{member_id}` - Subscribe to member alerts
- `POST /alerts/amount` - Set amount-based alerts
- `POST /alerts/ticker/{ticker}` - Subscribe to ticker alerts
- `GET /alerts/rules` - List user's alert rules
- `DELETE /alerts/rules/{rule_id}` - Delete alert rule
- `PUT /alerts/rules/{rule_id}` - Update alert rule

### **Phase 4: Integration & Background Tasks (1 day)**

#### **4.1 Data Ingestion Integration**
```python
# Update: app/src/domains/congressional/ingestion.py
```

**Integration Points:**
- Hook into `_insert_trades()` method
- Trigger notification processing for new trades
- Batch processing for efficiency

#### **4.2 Background Tasks**
```python
# Update: app/src/background/tasks.py
```

**New Tasks:**
- `process_new_trade_notifications(trade_id)` - Process single trade
- `batch_process_trade_notifications(trade_ids)` - Process multiple trades
- `send_pending_notifications()` - Send queued notifications
- `cleanup_old_alerts(days)` - Clean up old alert data

---

## 🔧 **Detailed Implementation**

### **Step 1: Trade Detection Service**

```python
# app/src/domains/notifications/trade_detection.py

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from domains.congressional.models import CongressionalTrade
from domains.congressional.schemas import CongressionalTradeDetail
from domains.notifications.alert_engine import AlertRuleEngine
from domains.notifications.notification_service import NotificationService
from domains.users.models import User

import logging
logger = logging.getLogger(__name__)


class TradeDetectionService:
    """Service for detecting new trades and triggering notifications."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.alert_engine = AlertRuleEngine(session)
        self.notification_service = NotificationService(session)
    
    async def detect_new_trades(self, since_date: datetime) -> List[CongressionalTradeDetail]:
        """Find all new trades since a given date."""
        try:
            query = select(CongressionalTrade).where(
                CongressionalTrade.created_at >= since_date
            ).order_by(CongressionalTrade.created_at.desc())
            
            result = await self.session.execute(query)
            trades = result.scalars().all()
            
            logger.info(f"Detected {len(trades)} new trades since {since_date}")
            return [CongressionalTradeDetail.from_orm(trade) for trade in trades]
            
        except Exception as e:
            logger.error(f"Error detecting new trades: {e}")
            raise
    
    async def process_new_trade(self, trade: CongressionalTradeDetail) -> Dict[str, Any]:
        """Process a single new trade and trigger notifications."""
        try:
            logger.info(f"Processing new trade: {trade.id} for member {trade.member_id}")
            
            # Step 1: Evaluate alert rules
            triggered_alerts = await self.alert_engine.evaluate_all_alerts(trade)
            
            # Step 2: Send notifications
            notifications_sent = 0
            for alert_rule in triggered_alerts:
                try:
                    await self.notification_service.send_trade_alert_email(
                        alert_rule.user, trade, alert_rule
                    )
                    notifications_sent += 1
                except Exception as e:
                    logger.error(f"Failed to send notification for alert {alert_rule.id}: {e}")
            
            logger.info(f"Trade {trade.id} processed: {notifications_sent} notifications sent")
            
            return {
                "trade_id": trade.id,
                "member_id": trade.member_id,
                "alerts_triggered": len(triggered_alerts),
                "notifications_sent": notifications_sent
            }
            
        except Exception as e:
            logger.error(f"Error processing trade {trade.id}: {e}")
            raise
    
    async def batch_process_trades(self, trades: List[CongressionalTradeDetail]) -> Dict[str, Any]:
        """Process multiple trades efficiently."""
        results = {
            "total_trades": len(trades),
            "processed_trades": 0,
            "total_notifications": 0,
            "errors": []
        }
        
        for trade in trades:
            try:
                result = await self.process_new_trade(trade)
                results["processed_trades"] += 1
                results["total_notifications"] += result["notifications_sent"]
            except Exception as e:
                results["errors"].append({
                    "trade_id": trade.id,
                    "error": str(e)
                })
                logger.error(f"Error processing trade {trade.id}: {e}")
        
        logger.info(f"Batch processing completed: {results}")
        return results
```

### **Step 2: Alert Rule Engine**

```python
# app/src/domains/notifications/alert_engine.py

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from domains.congressional.schemas import CongressionalTradeDetail
from domains.notifications.models import TradeAlertRule, UserAlert
from domains.users.models import User

import logging
logger = logging.getLogger(__name__)


class AlertRuleEngine:
    """Engine for evaluating alert rules against trades."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def evaluate_all_alerts(self, trade: CongressionalTradeDetail) -> List[TradeAlertRule]:
        """Evaluate all types of alerts for a trade."""
        triggered_alerts = []
        
        # Member-specific alerts
        member_alerts = await self.evaluate_member_alerts(trade)
        triggered_alerts.extend(member_alerts)
        
        # Amount-based alerts
        amount_alerts = await self.evaluate_amount_alerts(trade)
        triggered_alerts.extend(amount_alerts)
        
        # Ticker-specific alerts
        ticker_alerts = await self.evaluate_ticker_alerts(trade)
        triggered_alerts.extend(ticker_alerts)
        
        # Remove duplicates (same user, same alert type)
        unique_alerts = self._deduplicate_alerts(triggered_alerts)
        
        logger.info(f"Trade {trade.id}: {len(unique_alerts)} unique alerts triggered")
        return unique_alerts
    
    async def evaluate_member_alerts(self, trade: CongressionalTradeDetail) -> List[TradeAlertRule]:
        """Find users watching this specific congress member."""
        try:
            query = select(TradeAlertRule).where(
                and_(
                    TradeAlertRule.alert_type == "member_trades",
                    TradeAlertRule.target_id == trade.member_id,
                    TradeAlertRule.is_active == True
                )
            )
            
            result = await self.session.execute(query)
            alerts = result.scalars().all()
            
            logger.debug(f"Found {len(alerts)} member alerts for member {trade.member_id}")
            return alerts
            
        except Exception as e:
            logger.error(f"Error evaluating member alerts: {e}")
            return []
    
    async def evaluate_amount_alerts(self, trade: CongressionalTradeDetail) -> List[TradeAlertRule]:
        """Find users with amount-based alerts that should trigger."""
        try:
            # Get trade amount (use max amount if range)
            trade_amount = trade.amount_max or trade.amount_exact or 0
            
            query = select(TradeAlertRule).where(
                and_(
                    TradeAlertRule.alert_type == "amount_threshold",
                    TradeAlertRule.threshold_value <= trade_amount,
                    TradeAlertRule.is_active == True
                )
            )
            
            result = await self.session.execute(query)
            alerts = result.scalars().all()
            
            logger.debug(f"Found {len(alerts)} amount alerts for trade amount {trade_amount}")
            return alerts
            
        except Exception as e:
            logger.error(f"Error evaluating amount alerts: {e}")
            return []
    
    async def evaluate_ticker_alerts(self, trade: CongressionalTradeDetail) -> List[TradeAlertRule]:
        """Find users watching this specific ticker."""
        if not trade.ticker:
            return []
        
        try:
            query = select(TradeAlertRule).where(
                and_(
                    TradeAlertRule.alert_type == "ticker_trades",
                    TradeAlertRule.target_symbol == trade.ticker.upper(),
                    TradeAlertRule.is_active == True
                )
            )
            
            result = await self.session.execute(query)
            alerts = result.scalars().all()
            
            logger.debug(f"Found {len(alerts)} ticker alerts for {trade.ticker}")
            return alerts
            
        except Exception as e:
            logger.error(f"Error evaluating ticker alerts: {e}")
            return []
    
    def _deduplicate_alerts(self, alerts: List[TradeAlertRule]) -> List[TradeAlertRule]:
        """Remove duplicate alerts for the same user and alert type."""
        seen = set()
        unique_alerts = []
        
        for alert in alerts:
            key = (alert.user_id, alert.alert_type, alert.target_id)
            if key not in seen:
                seen.add(key)
                unique_alerts.append(alert)
        
        return unique_alerts
```

### **Step 3: Notification Service**

```python
# app/src/domains/notifications/notification_service.py

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from domains.congressional.schemas import CongressionalTradeDetail
from domains.notifications.models import TradeAlertRule, NotificationDelivery
from domains.notifications.templates import TradeAlertEmailTemplate
from domains.users.models import User
from core.email import EmailService

import logging
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending and tracking notifications."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.email_service = EmailService()
        self.email_template = TradeAlertEmailTemplate()
    
    async def send_trade_alert_email(
        self, 
        user: User, 
        trade: CongressionalTradeDetail, 
        alert_rule: TradeAlertRule
    ) -> bool:
        """Send trade alert email to user."""
        try:
            # Generate email content
            subject = self._generate_email_subject(trade, alert_rule)
            html_content = self.email_template.generate_trade_alert_email(trade, user, alert_rule)
            text_content = self._generate_text_content(trade, alert_rule)
            
            # Send email
            success = await self.email_service._send_email(
                to_email=user.email,
                to_name=user.first_name or user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            # Track delivery
            await self._track_delivery(user.id, trade.id, alert_rule.id, success)
            
            if success:
                logger.info(f"Trade alert email sent to {user.email} for trade {trade.id}")
            else:
                logger.error(f"Failed to send trade alert email to {user.email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending trade alert email to {user.email}: {e}")
            await self._track_delivery(user.id, trade.id, alert_rule.id, False, str(e))
            return False
    
    async def send_bulk_alerts(
        self, 
        notifications: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Send multiple notifications efficiently."""
        results = {
            "total": len(notifications),
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        for notification in notifications:
            try:
                success = await self.send_trade_alert_email(
                    notification["user"],
                    notification["trade"],
                    notification["alert_rule"]
                )
                
                if success:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(str(e))
                logger.error(f"Error in bulk notification: {e}")
        
        logger.info(f"Bulk notification completed: {results}")
        return results
    
    def _generate_email_subject(self, trade: CongressionalTradeDetail, alert_rule: TradeAlertRule) -> str:
        """Generate email subject line."""
        member_name = trade.member_name or f"Member {trade.member_id}"
        
        if alert_rule.alert_type == "member_trades":
            return f"🚨 {member_name} Made a New Trade"
        elif alert_rule.alert_type == "amount_threshold":
            return f"💰 Large Trade Alert: {member_name}"
        elif alert_rule.alert_type == "ticker_trades":
            return f"📈 {trade.ticker} Trade Alert: {member_name}"
        else:
            return f"📊 New Congressional Trade Alert"
    
    def _generate_text_content(self, trade: CongressionalTradeDetail, alert_rule: TradeAlertRule) -> str:
        """Generate plain text email content."""
        member_name = trade.member_name or f"Member {trade.member_id}"
        amount_str = self._format_amount(trade)
        
        return f"""
New Congressional Trade Alert

Member: {member_name}
Stock: {trade.ticker} - {trade.asset_name}
Action: {trade.transaction_type}
Amount: {amount_str}
Date: {trade.transaction_date}

View full details: https://capitolscope.chrislawrence.ca/trade/{trade.id}

Unsubscribe: https://capitolscope.chrislawrence.ca/unsubscribe
        """.strip()
    
    def _format_amount(self, trade: CongressionalTradeDetail) -> str:
        """Format trade amount for display."""
        if trade.amount_exact:
            return f"${trade.amount_exact / 100:,.2f}"
        elif trade.amount_min and trade.amount_max:
            return f"${trade.amount_min / 100:,.2f} - ${trade.amount_max / 100:,.2f}"
        else:
            return "Amount not specified"
    
    async def _track_delivery(
        self, 
        user_id: int, 
        trade_id: int, 
        alert_rule_id: int, 
        success: bool, 
        error_message: Optional[str] = None
    ):
        """Track notification delivery status."""
        try:
            delivery = NotificationDelivery(
                user_id=user_id,
                trade_id=trade_id,
                alert_rule_id=alert_rule_id,
                delivery_status="sent" if success else "failed",
                sent_at=datetime.utcnow(),
                error_message=error_message
            )
            
            self.session.add(delivery)
            await self.session.commit()
            
        except Exception as e:
            logger.error(f"Error tracking delivery: {e}")
```

### **Step 4: Email Templates**

```python
# app/src/domains/notifications/templates.py

from typing import Optional
from domains.congressional.schemas import CongressionalTradeDetail
from domains.notifications.models import TradeAlertRule
from domains.users.models import User

import logging
logger = logging.getLogger(__name__)


class TradeAlertEmailTemplate:
    """Email templates for trade alerts."""
    
    def generate_trade_alert_email(
        self, 
        trade: CongressionalTradeDetail, 
        user: User, 
        alert_rule: TradeAlertRule
    ) -> str:
        """Generate HTML email for trade alert."""
        
        # Format data
        member_name = trade.member_name or f"Member {trade.member_id}"
        amount_str = self._format_amount(trade)
        action_emoji = "🟢" if trade.transaction_type == "buy" else "🔴"
        action_text = trade.transaction_type.title()
        
        # Generate HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trade Alert - CapitolScope</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #1a365d; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f8f9fa; }}
        .trade-details {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; }}
        .trade-row {{ display: flex; justify-content: space-between; margin: 10px 0; }}
        .trade-label {{ font-weight: bold; color: #666; }}
        .trade-value {{ color: #333; }}
        .cta-button {{ display: inline-block; background: #3182ce; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 14px; }}
        .unsubscribe {{ color: #999; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 CapitolScope Trade Alert</h1>
        </div>
        
        <div class="content">
            <h2>New Congressional Trade Detected</h2>
            
            <div class="trade-details">
                <div class="trade-row">
                    <span class="trade-label">Congress Member:</span>
                    <span class="trade-value">{member_name}</span>
                </div>
                
                <div class="trade-row">
                    <span class="trade-label">Stock:</span>
                    <span class="trade-value">{trade.ticker} - {trade.asset_name}</span>
                </div>
                
                <div class="trade-row">
                    <span class="trade-label">Action:</span>
                    <span class="trade-value">{action_emoji} {action_text}</span>
                </div>
                
                <div class="trade-row">
                    <span class="trade-label">Amount:</span>
                    <span class="trade-value">{amount_str}</span>
                </div>
                
                <div class="trade-row">
                    <span class="trade-label">Trade Date:</span>
                    <span class="trade-value">{trade.transaction_date}</span>
                </div>
                
                <div class="trade-row">
                    <span class="trade-label">Filing Date:</span>
                    <span class="trade-value">{trade.notification_date}</span>
                </div>
            </div>
            
            <a href="https://capitolscope.chrislawrence.ca/trade/{trade.id}" class="cta-button">
                View Full Trade Details
            </a>
            
            <a href="https://capitolscope.chrislawrence.ca/member/{trade.member_id}" class="cta-button">
                View {member_name}'s Portfolio
            </a>
        </div>
        
        <div class="footer">
            <p>You received this alert because you're subscribed to {self._get_alert_description(alert_rule)}</p>
            <p>
                <a href="https://capitolscope.chrislawrence.ca/alerts/manage" class="unsubscribe">
                    Manage Alert Preferences
                </a> | 
                <a href="https://capitolscope.chrislawrence.ca/unsubscribe?email={user.email}" class="unsubscribe">
                    Unsubscribe
                </a>
            </p>
            <p>&copy; 2025 CapitolScope. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def _format_amount(self, trade: CongressionalTradeDetail) -> str:
        """Format trade amount for display."""
        if trade.amount_exact:
            return f"${trade.amount_exact / 100:,.2f}"
        elif trade.amount_min and trade.amount_max:
            return f"${trade.amount_min / 100:,.2f} - ${trade.amount_max / 100:,.2f}"
        else:
            return "Amount not specified"
    
    def _get_alert_description(self, alert_rule: TradeAlertRule) -> str:
        """Get human-readable description of alert rule."""
        if alert_rule.alert_type == "member_trades":
            return f"alerts for {alert_rule.target_name or f'Member {alert_rule.target_id}'}"
        elif alert_rule.alert_type == "amount_threshold":
            return f"alerts for trades over ${alert_rule.threshold_value / 100:,.2f}"
        elif alert_rule.alert_type == "ticker_trades":
            return f"alerts for {alert_rule.target_symbol} trades"
        else:
            return "trade alerts"
```

---

## 🔗 **Integration Points**

### **1. Data Ingestion Integration**

Update the existing ingestion pipeline to trigger notifications:

```python
# Update: app/src/domains/congressional/ingestion.py

# Add to imports
from domains.notifications.trade_detection import TradeDetectionService

class CongressionalDataIngestion:
    def __init__(self, session: Session):
        # ... existing code ...
        self.notification_service = TradeDetectionService(session)
    
    def _insert_trades(self, trades: List[ProcessedTrade]):
        """Insert processed trades into database with diagnostics."""
        # ... existing insertion code ...
        
        # NEW: Trigger notifications for new trades
        if inserted > 0:
            try:
                # Get the newly inserted trades
                new_trades = self._get_newly_inserted_trades(trades)
                
                # Process notifications asynchronously
                from background.tasks import process_new_trade_notifications
                for trade in new_trades:
                    process_new_trade_notifications.delay(trade.id)
                
                logger.info(f"Triggered notification processing for {len(new_trades)} new trades")
            except Exception as e:
                logger.error(f"Error triggering notifications: {e}")
```

### **2. Background Task Integration**

```python
# Update: app/src/background/tasks.py

@celery_app.task(base=DatabaseTask, bind=True)
def process_new_trade_notifications(self, trade_id: int):
    """Process notifications for a newly inserted trade."""
    try:
        logger.info(f"Processing notifications for trade {trade_id}")
        
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        async with db_manager.session_factory() as session:
            # Get trade details
            trade_repo = CongressionalTradeRepository(session)
            trade = await trade_repo.get_by_id(trade_id)
            
            if not trade:
                logger.warning(f"Trade {trade_id} not found")
                return {"status": "error", "message": "Trade not found"}
            
            # Process notifications
            detection_service = TradeDetectionService(session)
            result = await detection_service.process_new_trade(trade)
            
            logger.info(f"Trade {trade_id} notifications processed: {result}")
            return {"status": "success", "result": result}
            
    except Exception as exc:
        logger.error(f"Error processing notifications for trade {trade_id}: {exc}")
        raise self.retry(exc=exc, countdown=300, max_retries=3)
    finally:
        await db_manager.close()
```

---

## 🗄️ **Database Schema Updates**

### **New Tables**

```sql
-- Trade Alert Rules
CREATE TABLE trade_alert_rules (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    alert_type VARCHAR(30) NOT NULL, -- member_trades, amount_threshold, ticker_trades
    target_id INTEGER, -- member_id for member alerts
    target_symbol VARCHAR(10), -- ticker symbol for ticker alerts
    target_name VARCHAR(100), -- human-readable target name
    threshold_value BIGINT, -- amount threshold in cents
    conditions JSONB, -- additional conditions
    notification_channels TEXT[] DEFAULT ARRAY['email'],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Notification Delivery Tracking
CREATE TABLE notification_deliveries (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    trade_id INTEGER NOT NULL REFERENCES congressional_trades(id),
    alert_rule_id INTEGER NOT NULL REFERENCES trade_alert_rules(id),
    delivery_status VARCHAR(20) NOT NULL, -- pending, sent, delivered, failed
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_trade_alert_rules_user_id ON trade_alert_rules(user_id);
CREATE INDEX idx_trade_alert_rules_alert_type ON trade_alert_rules(alert_type);
CREATE INDEX idx_trade_alert_rules_target_id ON trade_alert_rules(target_id);
CREATE INDEX idx_trade_alert_rules_target_symbol ON trade_alert_rules(target_symbol);
CREATE INDEX idx_trade_alert_rules_active ON trade_alert_rules(is_active);
CREATE INDEX idx_notification_deliveries_user_id ON notification_deliveries(user_id);
CREATE INDEX idx_notification_deliveries_trade_id ON notification_deliveries(trade_id);
```

---

## 🧪 **Testing Strategy**

### **Unit Tests**

```python
# tests/domains/notifications/test_trade_detection.py
# tests/domains/notifications/test_alert_engine.py
# tests/domains/notifications/test_notification_service.py
```

### **Integration Tests**

```python
# tests/integration/test_notification_flow.py
# tests/integration/test_email_delivery.py
```

### **End-to-End Tests**

```python
# tests/e2e/test_complete_notification_flow.py
```

---

## 🚀 **Deployment Checklist**

### **Environment Variables**
```bash
# Email Configuration
SENDGRID_API_KEY=your_sendgrid_key
SENDGRID_FROM_EMAIL=noreply@capitolscope.com
SENDGRID_FROM_NAME=CapitolScope

# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### **Database Migrations**
```bash
# Create migration for new tables
alembic revision --autogenerate -m "Add notification tables"

# Apply migration
alembic upgrade head
```

### **Service Configuration**
```bash
# Start Celery worker for background tasks
celery -A app.src.background.celery_app worker --loglevel=info

# Start Celery beat for scheduled tasks
celery -A app.src.background.celery_app beat --loglevel=info
```

---

## 📊 **Monitoring & Analytics**

### **Key Metrics to Track**
- Number of alerts triggered per day
- Email delivery success rate
- User engagement with alerts
- Most popular alert types
- Peak notification times

### **Logging**
```python
# Structured logging for notifications
logger.info("Trade alert processed", extra={
    "trade_id": trade.id,
    "member_id": trade.member_id,
    "alerts_triggered": len(triggered_alerts),
    "notifications_sent": notifications_sent
})
```

---

## 🎯 **Quick Start for Kyle's MTG Alerts**

### **1. Create Alert Rule**
```python
# When Kyle signs up and wants MTG alerts
alert_rule = TradeAlertRule(
    user_id=kyle_user_id,
    name="MTG Trade Alerts",
    description="Get notified when Marjorie Taylor Greene makes trades",
    alert_type="member_trades",
    target_id=mtg_member_id,  # MTG's member ID in database
    target_name="Marjorie Taylor Greene",
    notification_channels=["email"],
    is_active=True
)
```

### **2. Test the Flow**
```python
# Manual test of notification flow
async def test_mtg_alert():
    # Simulate new MTG trade
    trade = CongressionalTradeDetail(
        id=12345,
        member_id=mtg_member_id,
        member_name="Marjorie Taylor Greene",
        ticker="TSLA",
        asset_name="Tesla Inc",
        transaction_type="buy",
        amount_exact=5000000,  # $50,000
        transaction_date=date.today()
    )
    
    # Process notification
    detection_service = TradeDetectionService(session)
    result = await detection_service.process_new_trade(trade)
    
    print(f"Notifications sent: {result['notifications_sent']}")
```

---

## 🔄 **Future Enhancements**

### **Phase 2 Features**
- SMS notifications
- Push notifications
- Advanced filtering (committee membership, sector)
- Custom alert schedules
- Alert aggregation (daily/weekly summaries)

### **Phase 3 Features**
- Machine learning for unusual activity detection
- Social media integration (Twitter bot)
- API for third-party integrations
- White-label notification system

---

## 📝 **Implementation Notes**

1. **Start Simple**: Begin with member-specific alerts (MTG for Kyle)
2. **Test Thoroughly**: Use small test dataset before production
3. **Monitor Performance**: Watch for database query performance
4. **Rate Limiting**: Implement email rate limiting to avoid spam
5. **User Experience**: Make it easy to manage alert preferences
6. **Compliance**: Ensure email compliance (unsubscribe links, etc.)

This implementation guide provides a complete roadmap for building a robust notification system that will scale from Kyle's MTG alerts to a comprehensive platform feature.
