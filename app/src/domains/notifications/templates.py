"""
Email Templates for Congressional Trade Notifications.

This module provides HTML and text email templates for trade alert notifications.
"""

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
        action_text = trade.transaction_type.title() if trade.transaction_type else "Unknown"
        
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
                    <span class="trade-value">{trade.ticker or 'Unknown'} - {trade.asset_name or 'Unknown Asset'}</span>
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
                    <span class="trade-value">{trade.transaction_date or 'Unknown'}</span>
                </div>
                
                <div class="trade-row">
                    <span class="trade-label">Filing Date:</span>
                    <span class="trade-value">{trade.notification_date or 'Unknown'}</span>
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



