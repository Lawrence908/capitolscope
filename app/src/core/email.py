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
from domains.users.models import User

logger = logging.getLogger(__name__)

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
            reset_url = f"http://localhost:5173/reset-password?token={reset_token}"
            
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
            msg['From'] = self.settings.SENDGRID_FROM_EMAIL
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
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reset Your Password</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1f2937; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .button {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>CapitolScope</h1>
                    <p>Congressional Trading Transparency Platform</p>
                </div>
                <div class="content">
                    <h2>Reset Your Password</h2>
                    <p>Hello {user.display_name or user.first_name or 'there'},</p>
                    <p>We received a request to reset your password for your CapitolScope account.</p>
                    <p>Click the button below to reset your password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </p>
                    <p>If you didn't request this password reset, you can safely ignore this email.</p>
                    <p>This link will expire in 24 hours for security reasons.</p>
                </div>
                <div class="footer">
                    <p>© 2025 CapitolScope. All rights reserved.</p>
                    <p>If you have any questions, please contact our support team.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
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

    def _create_welcome_html(self, user: User) -> str:
        """Create HTML content for welcome email."""
        logo_data_url = self._get_logo_base64()
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to CapitolScope</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #2d3748; margin: 0; padding: 0; background-color: #f7fafc; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 20px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 32px; font-weight: 700; display: flex; align-items: center; justify-content: center; gap: 10px; }}
                .header h1 img {{ width: 40px; height: 40px; }}
                .header p {{ margin: 10px 0 0 0; font-size: 16px; opacity: 0.9; }}
                .content {{ padding: 40px 30px; }}
                .welcome-text {{ font-size: 18px; color: #4a5568; margin-bottom: 30px; }}
                .features {{ background: #f8fafc; padding: 25px; border-radius: 8px; margin: 25px 0; }}
                .features h3 {{ color: #2d3748; margin-top: 0; font-size: 20px; }}
                .features ul {{ margin: 0; padding-left: 20px; }}
                .features li {{ margin: 8px 0; color: #4a5568; }}
                .cta-section {{ text-align: center; margin: 35px 0; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3); transition: transform 0.2s; }}
                .button:hover {{ transform: translateY(-2px); }}
                .stats {{ display: flex; justify-content: space-around; margin: 30px 0; text-align: center; }}
                .stat {{ flex: 1; padding: 20px; }}
                .stat-number {{ font-size: 24px; font-weight: 700; color: #667eea; }}
                .stat-label {{ font-size: 14px; color: #718096; margin-top: 5px; }}
                .footer {{ background: #2d3748; color: white; padding: 30px 20px; text-align: center; }}
                .footer p {{ margin: 5px 0; }}
                .social-links {{ margin: 20px 0; }}
                .social-links a {{ color: #a0aec0; text-decoration: none; margin: 0 10px; }}
                .highlight {{ background: #ebf8ff; border-left: 4px solid #3182ce; padding: 15px; margin: 20px 0; }}
                .coming-soon {{ text-decoration: line-through; color: #a0aec0; }}
                .coming-soon-label {{ background: #f7fafc; color: #718096; font-size: 12px; padding: 2px 6px; border-radius: 4px; margin-left: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏛️ CapitolScope</h1>
                    <p>Your Window into Congressional Trading Activity</p>
                </div>
                <div class="content">
                    <div class="welcome-text">
                        <h2>Welcome aboard, {user.display_name or user.first_name or 'there'}! 👋</h2>
                        <p>You've just joined the most comprehensive platform for tracking congressional trading activity. Get ready to discover insights that could transform your investment strategy.</p>
                    </div>
                    
                    <div class="highlight">
                        <strong>🎯 What you can do right now:</strong>
                        <ul>
                            <li>Browse real-time congressional trading data</li>
                            <li>Search trades by member, company, or amount</li>
                            <li style="text-decoration: line-through; color: #a0aec0;">Set up alerts for specific congress members <span style="background: #f7fafc; color: #718096; font-size: 12px; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">Coming Soon</span></li>
                            <li style="text-decoration: line-through; color: #a0aec0;">Analyze trading patterns and trends <span style="background: #f7fafc; color: #718096; font-size: 12px; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">Coming Soon</span></li>
                        </ul>
                    </div>
                    
                    <div class="features">
                        <h3>🚀 Key Features Available to You</h3>
                        <ul>
                            <li><strong>Real-time Tracking:</strong> Monitor congressional trades as they happen</li>
                            <li><strong>Advanced Search:</strong> Filter by member, ticker, date range, and transaction type</li>
                            <li style="text-decoration: line-through; color: #a0aec0;"><strong>Portfolio Analysis:</strong> Compare congressional portfolios and performance <span style="background: #f7fafc; color: #718096; font-size: 12px; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">Coming Soon</span></li>
                            <li style="text-decoration: line-through; color: #a0aec0;"><strong>Market Insights:</strong> Understand the impact of congressional activity on markets <span style="background: #f7fafc; color: #718096; font-size: 12px; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">Coming Soon</span></li>
                            <li style="text-decoration: line-through; color: #a0aec0;"><strong>Custom Alerts:</strong> Get notified when specific members make trades <span style="background: #f7fafc; color: #718096; font-size: 12px; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">Coming Soon</span></li>
                            <li style="text-decoration: line-through; color: #a0aec0;"><strong>Data Export:</strong> Download trade data for your own analysis <span style="background: #f7fafc; color: #718096; font-size: 12px; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">Coming Soon</span></li>
                        </ul>
                    </div>
                    
                    <div class="stats">
                        <div class="stat">
                            <div class="stat-number">500+</div>
                            <div class="stat-label">Congress Members</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">23K+</div>
                            <div class="stat-label">Trades Tracked</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">$2B+</div>
                            <div class="stat-label">Total Volume</div>
                        </div>
                    </div>
                    
                    <div class="cta-section">
                        <a href="https://capitolscope.chrislawrence.ca/dashboard" class="button">🚀 Start Exploring Now</a>
                    </div>
                    
                    <p style="text-align: center; color: #718096; font-size: 14px;">
                        Questions? Reach out to us at <a href="mailto:capitolscope@gmail.com" style="color: #667eea;">capitolscope@gmail.com</a>
                    </p>
                </div>
                <div class="footer">
                    <p><strong>© 2025 CapitolScope</strong></p>
                    <p>Empowering transparency in congressional trading</p>
                    <div class="social-links">
                        <a href="https://twitter.com/capitolscopeusa">Twitter</a> |
                        <a href="https://capitolscope.chrislawrence.ca">Website</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
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
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to CapitolScope {tier.title()}!</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #2d3748; margin: 0; padding: 0; background-color: #f7fafc; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 20px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 32px; font-weight: 700; display: flex; align-items: center; justify-content: center; gap: 10px; }}
                .header p {{ margin: 10px 0 0 0; font-size: 16px; opacity: 0.9; }}
                .content {{ padding: 40px 30px; }}
                .welcome-text {{ font-size: 18px; color: #4a5568; margin-bottom: 30px; }}
                .subscription-details {{ background: #f8fafc; padding: 25px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #667eea; }}
                .subscription-details h3 {{ color: #2d3748; margin-top: 0; font-size: 20px; }}
                .features {{ background: #f8fafc; padding: 25px; border-radius: 8px; margin: 25px 0; }}
                .features h3 {{ color: #2d3748; margin-top: 0; font-size: 20px; }}
                .features ul {{ margin: 0; padding-left: 20px; }}
                .features li {{ margin: 8px 0; color: #4a5568; }}
                .feature-item {{ display: flex; align-items: center; margin: 12px 0; }}
                .feature-icon {{ margin-right: 12px; font-size: 18px; }}
                .cta-section {{ text-align: center; margin: 35px 0; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3); transition: transform 0.2s; }}
                .button:hover {{ transform: translateY(-2px); }}
                .footer {{ background: #2d3748; color: white; padding: 30px 20px; text-align: center; }}
                .footer p {{ margin: 5px 0; }}
                .social-links {{ margin: 20px 0; }}
                .social-links a {{ color: #a0aec0; text-decoration: none; margin: 0 10px; }}
                .highlight {{ background: #ebf8ff; border-left: 4px solid #3182ce; padding: 15px; margin: 20px 0; }}
                .tier-badge {{ display: inline-block; background: #667eea; color: white; padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: 600; margin-left: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏛️ CapitolScope</h1>
                    <p>Your Window into Congressional Trading Activity</p>
                </div>
                <div class="content">
                    <div class="welcome-text">
                        <h2>Welcome to {tier.title()}, {user.display_name or user.first_name or 'there'}! 🎉</h2>
                        <p>Your subscription has been successfully activated! You now have access to premium features that will give you deeper insights into congressional trading activity.</p>
                    </div>
                    
                    <div class="subscription-details">
                        <h3>📋 Subscription Details</h3>
                        <p><strong>Plan:</strong> {tier.title()} <span class="tier-badge">{tier.upper()}</span></p>
                        <p><strong>Billing Cycle:</strong> {interval.title()}</p>
                        <p><strong>Amount:</strong> ${pricing['price']}/{pricing['period']}</p>
                        {f"<p><strong>Savings:</strong> {pricing['savings']}</p>" if pricing.get('savings') else ""}
                    </div>
                    
                    <div class="features">
                        <h3>🚀 Your {tier.title()} Benefits</h3>
                        <ul>
                            {''.join([f'<li class="feature-item"><span class="feature-icon">{feature["icon"]}</span> <strong>{feature["name"]}:</strong> {feature["description"]}</li>' for feature in features])}
                        </ul>
                    </div>
                    
                    <div class="highlight">
                        <strong>💡 Pro Tip:</strong> Make the most of your {tier.title()} subscription by exploring all the advanced features. Start with the dashboard to see your personalized insights!
                    </div>
                    
                    <div class="cta-section">
                        <a href="https://capitolscope.chrislawrence.ca/dashboard" class="button">🚀 Access Your Dashboard</a>
                    </div>
                    
                    <p style="text-align: center; color: #718096; font-size: 14px;">
                        Questions about your subscription? Contact us at <a href="mailto:capitolscope@gmail.com" style="color: #667eea;">capitolscope@gmail.com</a>
                    </p>
                </div>
                <div class="footer">
                    <p><strong>© 2025 CapitolScope</strong></p>
                    <p>Empowering transparency in congressional trading</p>
                    <div class="social-links">
                        <a href="https://twitter.com/capitolscopeusa">Twitter</a> |
                        <a href="https://capitolscope.chrislawrence.ca">Website</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
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