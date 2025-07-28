"""
Email service for CapitolScope.

This module provides email functionality using SendGrid API with fallback to SMTP.
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
import secrets
import hashlib

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
    
    def _create_welcome_html(self, user: User) -> str:
        """Create HTML content for welcome email."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to CapitolScope</title>
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
                    <h2>Welcome to CapitolScope!</h2>
                    <p>Hello {user.display_name or user.first_name or 'there'},</p>
                    <p>Thank you for joining CapitolScope! We're excited to have you on board.</p>
                    <p>With CapitolScope, you can:</p>
                    <ul>
                        <li>Track congressional trading activity in real-time</li>
                        <li>Search and filter trades by member, ticker, and amount</li>
                        <li>Get insights into trading patterns and trends</li>
                        <li>Stay informed about market-moving congressional activity</li>
                    </ul>
                    <p style="text-align: center;">
                        <a href="http://localhost:5173/dashboard" class="button">Get Started</a>
                    </p>
                    <p>If you have any questions or need help getting started, don't hesitate to reach out to our support team.</p>
                </div>
                <div class="footer">
                    <p>© 2025 CapitolScope. All rights reserved.</p>
                    <p>Welcome to the future of congressional transparency!</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _create_welcome_text(self, user: User) -> str:
        """Create text content for welcome email."""
        return f"""
        Welcome to CapitolScope!
        
        Hello {user.display_name or user.first_name or 'there'},
        
        Thank you for joining CapitolScope! We're excited to have you on board.
        
        With CapitolScope, you can:
        - Track congressional trading activity in real-time
        - Search and filter trades by member, ticker, and amount
        - Get insights into trading patterns and trends
        - Stay informed about market-moving congressional activity
        
        Get started: http://localhost:5173/dashboard
        
        If you have any questions or need help getting started, don't hesitate to reach out to our support team.
        
        Best regards,
        The CapitolScope Team
        """


# Global email service instance
email_service = EmailService() 