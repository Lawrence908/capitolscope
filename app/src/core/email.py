"""
Email service for CapitolScope.

This module provides email functionality using SendGrid API with fallback to SMTP.
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
import secrets
import hashlib
import base64

from core.config import get_settings
from core.email_templates import (
    render_email, email_button, email_heading, email_panel, p,
    BODY, INK, FAINT, ACCENT_DK, BRASS, SANS, MONO,
)
from domains.users.models import User

logger = logging.getLogger(__name__)

# Frontend base URL for links in emails (prod site).
FRONTEND_URL = "https://capitolscope.chrislawrence.ca"

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logger.warning("SendGrid not available. Install with: pip install sendgrid")

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    SMTP_AVAILABLE = True
except ImportError:
    SMTP_AVAILABLE = False
    logger.warning("SMTP not available")


class EmailService:
    """Email service for sending notifications and password resets."""
    
    def __init__(self):
        self.settings = get_settings()
        self.sendgrid_client = None
        self._sent_subscription_confirmations = set()  # Track sent confirmations to prevent duplicates
        
        # Debug logging for email configuration
        logger.info(f"Email configuration - EMAIL_HOST: {self.settings.EMAIL_HOST}")
        logger.info(f"Email configuration - EMAIL_USER: {self.settings.EMAIL_USER}")
        logger.info(f"Email configuration - EMAIL_FROM: {self.settings.EMAIL_FROM}")
        logger.info(f"Email configuration - SENDGRID_API_KEY: {'Set' if self.settings.SENDGRID_API_KEY else 'Not set'}")
        
        # Initialize SendGrid if available
        if SENDGRID_AVAILABLE and self.settings.SENDGRID_API_KEY:
            try:
                self.sendgrid_client = SendGridAPIClient(api_key=self.settings.SENDGRID_API_KEY.get_secret_value())
                logger.info("SendGrid client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid client: {e}")
                self.sendgrid_client = None
    
    async def send_password_reset_email(self, user: User, reset_token: str) -> bool:
        """Send password reset email to user."""
        try:
            reset_url = f"{FRONTEND_URL}/reset-password?token={reset_token}"
            
            subject = "Reset Your CapitolScope Password"
            html_content = self._create_password_reset_html(user, reset_url)
            text_content = self._create_password_reset_text(user, reset_url)
            
            return await self._send_email(
                to_email=user.email,
                to_name=user.display_name or user.first_name or user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {e}")
            return False
    
    async def send_welcome_email(self, user: User) -> bool:
        """Send welcome email to new user."""
        try:
            subject = "Welcome to CapitolScope!"
            html_content = self._create_welcome_html(user)
            text_content = self._create_welcome_text(user)
            
            return await self._send_email(
                to_email=user.email,
                to_name=user.display_name or user.first_name or user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {e}")
            return False
    
    async def send_subscription_confirmation_email(self, user: User, tier: str, interval: str) -> bool:
        """Send subscription confirmation email to user."""
        # Create a unique key for this confirmation to prevent duplicates
        confirmation_key = f"{user.id}_{tier}_{interval}_{datetime.now().strftime('%Y-%m-%d')}"
        
        if confirmation_key in self._sent_subscription_confirmations:
            logger.info(f"Subscription confirmation email already sent to user {user.id} for {tier} {interval}")
            return True
        
        try:
            subject = f"Welcome to CapitolScope {tier.title()}!"
            html_content = self._create_subscription_confirmation_html(user, tier, interval)
            text_content = self._create_subscription_confirmation_text(user, tier, interval)
            
            success = await self._send_email(
                to_email=user.email,
                to_name=user.display_name or user.first_name or user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            if success:
                self._sent_subscription_confirmations.add(confirmation_key)
                logger.info(f"Sent subscription confirmation email to user {user.id} for {tier} {interval}")
            
            return success
        except Exception as e:
            logger.error(f"Failed to send subscription confirmation email to {user.email}: {e}")
            return False
    
    async def _send_email(
        self, 
        to_email: str, 
        to_name: str, 
        subject: str, 
        html_content: str, 
        text_content: str
    ) -> bool:
        """Send email using SendGrid or SMTP fallback."""
        
        # Try SendGrid first
        if self.sendgrid_client:
            try:
                from_email = Email(self.settings.SENDGRID_FROM_EMAIL)
                to_email_obj = To(to_email)
                content = Content("text/html", html_content)
                mail = Mail(from_email, to_email_obj, subject, content)
                
                response = self.sendgrid_client.send(mail)
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Email sent successfully via SendGrid to {to_email}")
                    return True
                else:
                    logger.error(f"SendGrid error: {response.status_code} - {response.body}")
            except Exception as e:
                logger.error(f"SendGrid failed: {e}")
        else:
            logger.debug("SendGrid not available or not configured")
        
        # Fallback to SMTP
        if SMTP_AVAILABLE and self.settings.EMAIL_HOST:
            try:
                logger.debug(f"Attempting SMTP email to {to_email}")
                return self._send_smtp_email(to_email, to_name, subject, html_content, text_content)
            except Exception as e:
                logger.error(f"SMTP failed: {e}")
        else:
            logger.debug(f"SMTP not available. SMTP_AVAILABLE={SMTP_AVAILABLE}, EMAIL_HOST={self.settings.EMAIL_HOST}")
        
        # If both fail, log and return False
        logger.error(f"All email methods failed for {to_email}")
        return False
    
    def _send_smtp_email(
        self, 
        to_email: str, 
        to_name: str, 
        subject: str, 
        html_content: str, 
        text_content: str
    ) -> bool:
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            # Gmail (and SPF/DKIM alignment) requires the From to be the
            # authenticated sending address, so prefer EMAIL_FROM over the
            # SendGrid default which points at an unowned domain.
            msg['From'] = self.settings.EMAIL_FROM or self.settings.SENDGRID_FROM_EMAIL
            msg['To'] = to_email
            
            # Attach both text and HTML parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send via SMTP
            with smtplib.SMTP(self.settings.EMAIL_HOST, self.settings.EMAIL_PORT) as server:
                if self.settings.EMAIL_USE_TLS:
                    server.starttls()
                
                if self.settings.EMAIL_USER and self.settings.EMAIL_PASSWORD:
                    server.login(
                        self.settings.EMAIL_USER, 
                        self.settings.EMAIL_PASSWORD.get_secret_value()
                    )
                
                server.send_message(msg)
                logger.info(f"Email sent successfully via SMTP to {to_email}")
                return True
                
        except Exception as e:
            logger.error(f"SMTP email failed: {e}")
            return False
    
    def _create_password_reset_html(self, user: User, reset_url: str) -> str:
        """Create HTML content for password reset email."""
        name = user.display_name or user.first_name or "there"
        body = (
            email_heading("Reset your password")
            + p(f"Hello {name},")
            + p("We received a request to reset the password for your CapitolScope account.")
            + email_button(reset_url, "Reset Password")
            + p("If you didn't request this, you can safely ignore this email — your password won't change.")
            + p("For your security, this link expires in 24 hours.")
        )
        return render_email(
            title="Reset Your Password",
            body_html=body,
            preheader="Reset your CapitolScope password",
            footer_note="You received this because a password reset was requested for your account.",
        )
    
    def _create_password_reset_text(self, user: User, reset_url: str) -> str:
        """Create text content for password reset email."""
        return f"""
        Reset Your CapitolScope Password
        
        Hello {user.display_name or user.first_name or 'there'},
        
        We received a request to reset your password for your CapitolScope account.
        
        Click the link below to reset your password:
        {reset_url}
        
        If you didn't request this password reset, you can safely ignore this email.
        
        This link will expire in 24 hours for security reasons.
        
        Best regards,
        The CapitolScope Team
        """
    
    def _get_logo_base64(self) -> str:
        """Get logo as base64 data URL."""
        # Commented out - email image embedding is unreliable across clients
        # Using emoji approach instead which works everywhere
        return ""

    def _stat_row(self, items: List[tuple]) -> str:
        """A 3-up row of mono figures + labels (matches the app's StatTile)."""
        cells = "".join(
            f'<td align="center" style="padding:8px 10px;">'
            f'<div style="font-family:{MONO};font-size:22px;font-weight:600;color:{ACCENT_DK};">{value}</div>'
            f'<div style="font-family:{MONO};font-size:10px;letter-spacing:0.12em;text-transform:uppercase;'
            f'color:{FAINT};margin-top:4px;">{label}</div></td>'
            for value, label in items
        )
        return (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:24px 0;border-top:1px solid {INK}11;border-bottom:1px solid {INK}11;">'
            f"<tr>{cells}</tr></table>"
        )

    def _create_welcome_html(self, user: User) -> str:
        """Create HTML content for welcome email."""
        name = user.display_name or user.first_name or "there"
        now_items = [
            "Browse real-time congressional trading disclosures",
            "Search trades by member, company, or amount",
            "Set up trade alerts by member, ticker, or dollar threshold",
            "Open the Scrutiny leaderboard for who's worth a closer look",
        ]
        li = "".join(f'<li style="margin:6px 0;color:{BODY};">{x}</li>' for x in now_items)
        panel = email_panel(
            f'<div style="font-family:{SANS};font-weight:600;color:{INK};margin-bottom:8px;">Where to start</div>'
            f'<ul style="margin:0;padding-left:18px;font-family:{SANS};font-size:14px;line-height:1.7;">{li}</ul>',
            accent=True,
        )
        body = (
            email_heading(f"Welcome aboard, {name}")
            + p(
                "You've joined the most comprehensive platform for tracking congressional "
                "trading disclosures. Here's where to begin."
            )
            + panel
            + self._stat_row([("500+", "Congress members"), ("23K+", "Trades tracked"), ("$2B+", "Total volume")])
            + email_button(f"{FRONTEND_URL}/dashboard", "Start Exploring")
            + p(
                f'Questions? Reach out at '
                f'<a href="mailto:capitolscope@gmail.com" style="color:{ACCENT_DK};">capitolscope@gmail.com</a>.'
            )
        )
        return render_email(
            title="Welcome to CapitolScope",
            body_html=body,
            preheader="Welcome to CapitolScope — start exploring congressional trades",
            footer_links=[("Website", FRONTEND_URL), ("Support", "mailto:capitolscope@gmail.com")],
        )
    
    def _create_welcome_text(self, user: User) -> str:
        """Create text content for welcome email."""
        return f"""
        🏛️ Welcome to CapitolScope!
        
        Hello {user.display_name or user.first_name or 'there'},
        
        You've just joined the most comprehensive platform for tracking congressional trading activity! 🎉
        
        🎯 What you can do right now:
        • Browse real-time congressional trading data
        • Search trades by member, company, or amount
        • Set up alerts for specific congress members (Coming Soon)
        • Analyze trading patterns and trends (Coming Soon)
        
        🚀 Key Features Available to You:
        • Real-time Tracking: Monitor congressional trades as they happen
        • Advanced Search: Filter by member, ticker, date range, and transaction type
        • Portfolio Analysis: Compare congressional portfolios and performance (Coming Soon)
        • Market Insights: Understand the impact of congressional activity on markets (Coming Soon)
        • Custom Alerts: Get notified when specific members make trades (Coming Soon)
        • Data Export: Download trade data for your own analysis (Coming Soon)
        
        📊 Platform Stats:
        • 500+ Congress Members tracked
        • 23,000+ Trades monitored
        • $2B+ Total trading volume analyzed
        
        🚀 Get Started: http://localhost:5173/dashboard
        
        Questions? Reach out to us at capitolscope@gmail.com
        
        Best regards,
        The CapitolScope Team
        
        © 2025 CapitolScope - Empowering transparency in congressional trading
        """

    def _create_subscription_confirmation_html(self, user: User, tier: str, interval: str) -> str:
        """Create HTML content for subscription confirmation email."""
        # Define features based on tier
        features = self._get_tier_features(tier)
        pricing = self._get_tier_pricing(tier, interval)
        
        name = user.display_name or user.first_name or "there"
        savings_row = (
            f'<div style="margin:4px 0;"><strong style="color:{INK};">Savings:</strong> {pricing["savings"]}</div>'
            if pricing.get("savings")
            else ""
        )
        details = email_panel(
            f'<div style="font-family:{SANS};font-weight:600;color:{INK};margin-bottom:10px;">Subscription details</div>'
            f'<div style="margin:4px 0;"><strong style="color:{INK};">Plan:</strong> {tier.title()} '
            f'<span style="font-family:{MONO};font-size:11px;letter-spacing:0.1em;color:{BRASS};">[{tier.upper()}]</span></div>'
            f'<div style="margin:4px 0;"><strong style="color:{INK};">Billing:</strong> {interval.title()}</div>'
            f'<div style="margin:4px 0;"><strong style="color:{INK};">Amount:</strong> '
            f'<span style="font-family:{MONO};">${pricing["price"]}/{pricing["period"]}</span></div>'
            f"{savings_row}",
            accent=True,
        )
        feats = "".join(
            f'<li style="margin:8px 0;color:{BODY};"><span style="margin-right:8px;">{f["icon"]}</span>'
            f'<strong style="color:{INK};">{f["name"]}:</strong> {f["description"]}</li>'
            for f in features
        )
        benefits = email_panel(
            f'<div style="font-family:{SANS};font-weight:600;color:{INK};margin-bottom:8px;">Your {tier.title()} benefits</div>'
            f'<ul style="margin:0;padding-left:18px;font-family:{SANS};font-size:14px;line-height:1.6;">{feats}</ul>'
        )
        body = (
            email_heading(f"Welcome to {tier.title()}, {name}")
            + p(
                "Your subscription is active. You now have access to the premium features that "
                "give you a deeper read on congressional trading activity."
            )
            + details
            + benefits
            + email_button(f"{FRONTEND_URL}/dashboard", "Access Your Dashboard")
            + p(
                f'Questions about your subscription? Contact us at '
                f'<a href="mailto:capitolscope@gmail.com" style="color:{ACCENT_DK};">capitolscope@gmail.com</a>.'
            )
        )
        return render_email(
            title=f"Welcome to CapitolScope {tier.title()}",
            body_html=body,
            preheader=f"Your CapitolScope {tier.title()} subscription is active",
            footer_links=[("Website", FRONTEND_URL), ("Support", "mailto:capitolscope@gmail.com")],
        )
    
    def _create_subscription_confirmation_text(self, user: User, tier: str, interval: str) -> str:
        """Create text content for subscription confirmation email."""
        features = self._get_tier_features(tier)
        pricing = self._get_tier_pricing(tier, interval)
        
        features_text = '\n'.join([f"• {feature['icon']} {feature['name']}: {feature['description']}" for feature in features])
        
        return f"""
        🏛️ Welcome to CapitolScope {tier.title()}!
        
        Hello {user.display_name or user.first_name or 'there'},
        
        Your subscription has been successfully activated! 🎉
        
        📋 Subscription Details:
        • Plan: {tier.title()}
        • Billing Cycle: {interval.title()}
        • Amount: ${pricing['price']}/{pricing['period']}
        {f"• Savings: {pricing['savings']}" if pricing.get('savings') else ""}
        
        🚀 Your {tier.title()} Benefits:
        {features_text}
        
        💡 Pro Tip: Make the most of your {tier.title()} subscription by exploring all the advanced features. Start with the dashboard to see your personalized insights!
        
        🚀 Get Started: https://capitolscope.chrislawrence.ca/dashboard
        
        Questions about your subscription? Contact us at capitolscope@gmail.com
        
        Best regards,
        The CapitolScope Team
        
        © 2025 CapitolScope - Empowering transparency in congressional trading
        """
    
    def _get_tier_features(self, tier: str) -> List[dict]:
        """Get features for a specific tier based on PremiumSignup component."""
        all_features = [
            # Free features (available to all)
            {"name": "Basic Search & Browse", "description": "Search and filter congressional trading data", "icon": "🔍", "tiers": ["free", "pro", "premium", "enterprise"]},
            {"name": "Member Profiles", "description": "Detailed profiles of congress members and their trading history", "icon": "👤", "tiers": ["free", "pro", "premium", "enterprise"]},
            {"name": "Two-Factor Authentication", "description": "Enhanced security for your account", "icon": "🔒", "tiers": ["free", "pro", "premium", "enterprise"]},
            {"name": "Active Sessions", "description": "Manage your login sessions across devices", "icon": "🖥️", "tiers": ["free", "pro", "premium", "enterprise"]},
            {"name": "Trade Alerts", "description": "Get notified of new congressional trades in real-time", "icon": "🔔", "tiers": ["free", "pro", "premium", "enterprise"]},
            {"name": "Basic Portfolio Analytics", "description": "Basic portfolio performance and analytics", "icon": "📊", "tiers": ["free", "pro", "premium", "enterprise"]},
            {"name": "Export to CSV", "description": "Export trading data to CSV format", "icon": "📄", "tiers": ["free", "pro", "premium", "enterprise"]},
            
            # Pro features
            {"name": "Full Historical Data", "description": "Complete access to all historical trading data", "icon": "📈", "tiers": ["pro", "premium", "enterprise"]},
            {"name": "Weekly Summaries", "description": "Comprehensive weekly trading activity reports", "icon": "📋", "tiers": ["pro", "premium", "enterprise"]},
            {"name": "Multiple Buyer Alerts", "description": "Alerts when 5+ members buy same stock in 3 months", "icon": "👥", "tiers": ["pro", "premium", "enterprise"]},
            {"name": "High-Value Trade Alerts", "description": "Alerts for trades over $1M", "icon": "💰", "tiers": ["pro", "premium", "enterprise"]},
            {"name": "Saved Portfolios / Watchlists", "description": "Save and track your favorite portfolios", "icon": "⭐", "tiers": ["pro", "premium", "enterprise"]},
            
            # Premium features
            {"name": "TradingView-Style Charts", "description": "Interactive stock charts with trade overlays", "icon": "📊", "tiers": ["premium", "enterprise"]},
            {"name": "Advanced Portfolio Analytics", "description": "Advanced trading patterns and insights", "icon": "📈", "tiers": ["premium", "enterprise"]},
            {"name": "Sector/Committee-based Filters", "description": "Filter trades by congressional committees and sectors", "icon": "🏛️", "tiers": ["premium", "enterprise"]},
            {"name": "API Access (Rate-limited)", "description": "Programmatic access to trading data", "icon": "🔌", "tiers": ["premium", "enterprise"]},
            {"name": "Custom Alert Configurations", "description": "Create custom alerts for specific criteria", "icon": "⚙️", "tiers": ["premium", "enterprise"]},
            
            # Enterprise features
            {"name": "Advanced Analytics Dashboard", "description": "Advanced analytics and pattern recognition", "icon": "📊", "tiers": ["enterprise"]},
            {"name": "White-Label Dashboard Options", "description": "Custom branding and deployment options", "icon": "🏢", "tiers": ["enterprise"]},
            {"name": "Priority Support", "description": "Priority customer support and assistance", "icon": "🎯", "tiers": ["enterprise"]},
            {"name": "Increased API Limits", "description": "Higher rate limits for API access", "icon": "🚀", "tiers": ["enterprise"]},
            {"name": "Team Seats / Admin Panel", "description": "Manage team access and permissions", "icon": "👥", "tiers": ["enterprise"]},
        ]
        
        # Filter features for the specific tier
        return [feature for feature in all_features if tier.lower() in feature["tiers"]]
    
    def _get_tier_pricing(self, tier: str, interval: str) -> dict:
        """Get pricing information for a specific tier and interval."""
        pricing = {
            "pro": {
                "monthly": {"price": 5.99, "period": "month", "savings": None},
                "yearly": {"price": 59.99, "period": "year", "savings": "Save 17%"}
            },
            "premium": {
                "monthly": {"price": 14.99, "period": "month", "savings": None},
                "yearly": {"price": 149.99, "period": "year", "savings": "Save 17%"}
            },
            "enterprise": {
                "monthly": {"price": 49.99, "period": "month", "savings": None},
                "yearly": {"price": 499.99, "period": "year", "savings": "Save 17%"}
            }
        }
        
        return pricing.get(tier.lower(), {}).get(interval.lower(), {"price": 0, "period": "month", "savings": None})


# Global email service instance
email_service = EmailService() 