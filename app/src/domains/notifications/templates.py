"""
Email Templates for Congressional Trade Notifications.

This module provides HTML and text email templates for trade alert notifications.
"""

from typing import Optional
from domains.congressional.schemas import CongressionalTradeDetail
from domains.notifications.models import TradeAlertRule
from domains.users.models import User
from core.email_templates import (
    render_email, email_button, email_heading, email_panel, p,
    INK, FAINT, LINE, MONO, SANS,
)

import logging
logger = logging.getLogger(__name__)

FRONTEND_URL = "https://capitolscope.chrislawrence.ca"
BUY_COLOR = "#217a6b"   # verdigris (readable on white)
SELL_COLOR = "#c0555f"  # oxblood (readable on white)


def _dir_color(action_text: Optional[str]) -> str:
    return BUY_COLOR if (action_text or "").lower().startswith("buy") else SELL_COLOR


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
        
        color = _dir_color(action_text)

        def row(label, value):
            return (
                f'<tr><td style="padding:8px 0;font-family:{SANS};font-size:13px;color:{FAINT};">{label}</td>'
                f'<td style="padding:8px 0;font-family:{MONO};font-size:14px;color:{INK};text-align:right;">{value}</td></tr>'
            )

        details = email_panel(
            f'<div style="font-family:{SANS};font-size:15px;font-weight:600;color:{color};margin-bottom:8px;">'
            f'{action_emoji} {action_text} · {trade.ticker or "—"}</div>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            + row("Member", member_name)
            + row("Asset", trade.asset_name or "Unknown asset")
            + row("Amount", amount_str)
            + row("Trade date", trade.transaction_date or "—")
            + row("Filing date", trade.notification_date or "—")
            + "</table>",
            accent=True,
        )

        body = (
            email_heading("New congressional trade detected")
            + p("A trade matching one of your alerts was just disclosed.")
            + details
            + email_button(f"{FRONTEND_URL}/trades", "View Full Trade Details")
            + p(
                f'You received this alert because you\'re subscribed to '
                f'{self._get_alert_description(alert_rule)}.'
            )
        )
        return render_email(
            title="Trade Alert · CapitolScope",
            body_html=body,
            preheader=f"{action_text} {trade.ticker or ''} · {member_name}",
            footer_links=[
                ("Manage Alerts", f"{FRONTEND_URL}/alerts"),
                ("Unsubscribe", f"{FRONTEND_URL}/unsubscribe?email={user.email}"),
            ],
        )
    
    def generate_trade_alert_digest_email(self, user: User, items: list) -> str:
        """Generate a single HTML digest email summarizing many matched trades.

        ``items`` is a list of dicts with keys: member_name, ticker, asset_name,
        action_emoji, action_text, amount_str, transaction_date, trade_id, reason.
        Trades are grouped by member for readability.
        """
        greeting_name = user.first_name or "there"

        # Group rows by member so a member's trades render together.
        by_member: dict = {}
        for item in items:
            by_member.setdefault(item["member_name"], []).append(item)

        member_blocks = []
        for member_name, rows in by_member.items():
            trade_rows = "".join(
                f'<tr>'
                f'<td style="padding:8px 0;border-bottom:1px solid {LINE};font-family:{SANS};font-size:13px;color:{INK};">'
                f'<span style="color:{_dir_color(r["action_text"])};font-weight:600;">{r["action_emoji"]} {r["action_text"]}</span> '
                f'<span style="font-family:{MONO};">{r["ticker"] or r["asset_name"] or "Unknown"}</span></td>'
                f'<td style="padding:8px 0;border-bottom:1px solid {LINE};font-family:{MONO};font-size:13px;color:{INK};text-align:right;">{r["amount_str"]}</td>'
                f'<td style="padding:8px 0;border-bottom:1px solid {LINE};font-family:{MONO};font-size:12px;color:{FAINT};text-align:right;">{r["transaction_date"] or ""}</td>'
                f'</tr>'
                for r in rows
            )
            member_blocks.append(
                email_panel(
                    f'<div style="font-family:{SANS};font-weight:600;color:{INK};margin-bottom:6px;">{member_name} '
                    f'<span style="font-family:{MONO};font-size:12px;color:{FAINT};">· {len(rows)} trade(s)</span></div>'
                    f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">{trade_rows}</table>'
                )
            )

        total = len(items)
        members_count = len(by_member)
        blocks_html = "".join(member_blocks)

        body = (
            email_heading(f"{total} new trade(s) matched your alerts")
            + p(f"Hi {greeting_name}, across {members_count} member(s) you follow — here's the summary.")
            + blocks_html
            + email_button(f"{FRONTEND_URL}/alerts", "View in CapitolScope")
        )
        return render_email(
            title="Trade Alert Digest · CapitolScope",
            body_html=body,
            preheader=f"{total} new congressional trade(s) matched your alerts",
            footer_note="You received this because you set up trade alerts on CapitolScope.",
            footer_links=[
                ("Manage Alerts", f"{FRONTEND_URL}/alerts"),
                ("Unsubscribe", f"{FRONTEND_URL}/unsubscribe?email={user.email}"),
            ],
        )

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



