"""
Stripe Service for CapitolScope

This module provides comprehensive Stripe integration for subscription management,
payment processing, and webhook handling.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from domains.users.models import User, SubscriptionTier
from domains.users.schemas import SubscriptionResponse

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Product and Price IDs
STRIPE_PRODUCTS = {
    'pro': {
        'monthly': os.getenv('STRIPE_PRODUCT_PRO_MONTHLY'),
        'yearly': os.getenv('STRIPE_PRODUCT_PRO_YEARLY')
    },
    'premium': {
        'monthly': os.getenv('STRIPE_PRODUCT_PREMIUM_MONTHLY'),
        'yearly': os.getenv('STRIPE_PRODUCT_PREMIUM_YEARLY')
    },
    'enterprise': {
        'monthly': os.getenv('STRIPE_PRODUCT_ENTERPRISE_MONTHLY'),
        'yearly': os.getenv('STRIPE_PRODUCT_ENTERPRISE_YEARLY')
    }
}

STRIPE_PRICES = {
    'pro': {
        'month': os.getenv('STRIPE_PRICE_PRO_MONTHLY'),
        'year': os.getenv('STRIPE_PRICE_PRO_YEARLY')
    },
    'premium': {
        'month': os.getenv('STRIPE_PRICE_PREMIUM_MONTHLY'),
        'year': os.getenv('STRIPE_PRICE_PREMIUM_YEARLY')
    },
    'enterprise': {
        'month': os.getenv('STRIPE_PRICE_ENTERPRISE_MONTHLY'),
        'year': os.getenv('STRIPE_PRICE_ENTERPRISE_YEARLY')
    }
}

# URL Configuration
SUCCESS_URL = os.getenv('STRIPE_SUCCESS_URL', 'http://localhost:3000/dashboard?payment=success')
CANCEL_URL = os.getenv('STRIPE_CANCEL_URL', 'http://localhost:3000/premium?payment=cancelled')


class StripeService:
    """Service class for Stripe operations."""
    
    @staticmethod
    def create_customer(user: User, email: str) -> Optional[str]:
        """Create a Stripe customer for a user."""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=user.display_name,
                metadata={
                    'user_id': str(user.id),
                    'capitolscope_user': 'true'
                }
            )
            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Stripe customer for user {user.id}: {e}")
            return None
    
    @staticmethod
    def get_customer(customer_id: str) -> Optional[stripe.Customer]:
        """Retrieve a Stripe customer."""
        try:
            return stripe.Customer.retrieve(customer_id)
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving Stripe customer {customer_id}: {e}")
            return None
    
    @staticmethod
    def create_checkout_session(
        user: User,
        tier: str,
        interval: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Stripe Checkout session for subscription.
        
        Args:
            user: The user making the purchase
            tier: Subscription tier (pro, premium, enterprise)
            interval: Billing interval (monthly, yearly)
            success_url: Custom success URL
            cancel_url: Custom cancel URL
        """
        # Map frontend interval names to Stripe interval names
        interval_mapping = {
            'monthly': 'month',
            'yearly': 'year'
        }
        stripe_interval = interval_mapping.get(interval, interval)
        try:
            # Get the price ID for the tier and interval
            price_id = STRIPE_PRICES.get(tier, {}).get(stripe_interval)
            if not price_id:
                logger.error(f"No price found for tier {tier} and interval {stripe_interval}")
                return None
            
            # Create or get Stripe customer
            customer_id = user.stripe_customer_id
            if not customer_id:
                customer_id = StripeService.create_customer(user, user.email)
                if not customer_id:
                    return None
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url or SUCCESS_URL,
                cancel_url=cancel_url or CANCEL_URL,
                metadata={
                    'user_id': str(user.id),
                    'tier': tier,
                    'interval': interval,
                    'capitolscope_subscription': 'true'
                },
                subscription_data={
                    'metadata': {
                        'user_id': str(user.id),
                        'tier': tier,
                        'interval': interval,
                        'capitolscope_subscription': 'true'
                    }
                }
            )
            
            logger.info(f"Created checkout session {session.id} for user {user.id}")
            return {
                'session_id': session.id,
                'url': session.url,
                'customer_id': customer_id
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating checkout session for user {user.id}: {e}")
            return None
    
    @staticmethod
    def create_portal_session(user: User, return_url: Optional[str] = None) -> Optional[str]:
        """Create a Stripe Customer Portal session."""
        try:
            if not user.stripe_customer_id:
                logger.error(f"No Stripe customer ID for user {user.id}")
                return None
            
            session = stripe.billing_portal.Session.create(
                customer=user.stripe_customer_id,
                return_url=return_url or 'http://localhost:3000/dashboard',
                configuration=os.getenv('STRIPE_PORTAL_CONFIGURATION_ID')  # Optional
            )
            
            logger.info(f"Created portal session for user {user.id}")
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating portal session for user {user.id}: {e}")
            return None
    
    @staticmethod
    def get_subscription(subscription_id: str) -> Optional[stripe.Subscription]:
        """Retrieve a Stripe subscription."""
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving subscription {subscription_id}: {e}")
            return None
    
    @staticmethod
    def cancel_subscription(subscription_id: str, at_period_end: bool = True) -> bool:
        """Cancel a Stripe subscription."""
        try:
            if at_period_end:
                stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                stripe.Subscription.cancel(subscription_id)
            
            logger.info(f"Canceled subscription {subscription_id}")
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f"Error canceling subscription {subscription_id}: {e}")
            return False
    
    @staticmethod
    def update_subscription_tier(
        subscription_id: str,
        new_price_id: str,
        proration_behavior: str = 'create_prorations'
    ) -> bool:
        """Update a subscription to a different tier."""
        try:
            stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': stripe.Subscription.retrieve(subscription_id)['items']['data'][0].id,
                    'price': new_price_id,
                }],
                proration_behavior=proration_behavior
            )
            
            logger.info(f"Updated subscription {subscription_id} to new price {new_price_id}")
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f"Error updating subscription {subscription_id}: {e}")
            return False
    
    @staticmethod
    def handle_webhook(payload: bytes, sig_header: str) -> Optional[Dict[str, Any]]:
        """Handle Stripe webhook events."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            logger.info(f"Received webhook event: {event['type']}")
            return event
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return None
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            return None
    
    @staticmethod
    async def process_webhook_event(event: Dict[str, Any], db: AsyncSession) -> bool:
        """Process a Stripe webhook event."""
        event_type = event['type']
        
        try:
            if event_type == 'customer.subscription.created':
                return await StripeService._handle_subscription_created(event, db)
            elif event_type == 'customer.subscription.updated':
                return await StripeService._handle_subscription_updated(event, db)
            elif event_type == 'customer.subscription.deleted':
                return await StripeService._handle_subscription_deleted(event, db)
            elif event_type == 'invoice.payment_succeeded':
                return await StripeService._handle_payment_succeeded(event, db)
            elif event_type == 'invoice.payment_failed':
                return await StripeService._handle_payment_failed(event, db)
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing webhook event {event_type}: {e}")
            return False
    
    @staticmethod
    async def _handle_subscription_created(event: Dict[str, Any], db: AsyncSession) -> bool:
        """Handle subscription.created webhook."""
        subscription = event['data']['object']
        user_id = subscription['metadata'].get('user_id')
        tier = subscription['metadata'].get('tier', 'free')
        
        if not user_id:
            logger.error("No user_id in subscription metadata")
            return False
        
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            logger.error(f"User {user_id} not found")
            return False
        
        # Update user subscription
        user.subscription_tier = SubscriptionTier(tier.upper())
        user.subscription_status = subscription['status']
        user.subscription_start_date = datetime.fromtimestamp(subscription['current_period_start'])
        user.subscription_end_date = datetime.fromtimestamp(subscription['current_period_end'])
        
        await db.commit()
        logger.info(f"Updated user {user_id} subscription to {tier}")
        return True
    
    @staticmethod
    async def _handle_subscription_updated(event: Dict[str, Any], db: AsyncSession) -> bool:
        """Handle subscription.updated webhook."""
        subscription = event['data']['object']
        user_id = subscription['metadata'].get('user_id')
        
        if not user_id:
            return False
        
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            return False
        
        # Update subscription status
        user.subscription_status = subscription['status']
        user.subscription_end_date = datetime.fromtimestamp(subscription['current_period_end'])
        
        await db.commit()
        logger.info(f"Updated subscription status for user {user_id}")
        return True
    
    @staticmethod
    async def _handle_subscription_deleted(event: Dict[str, Any], db: AsyncSession) -> bool:
        """Handle subscription.deleted webhook."""
        subscription = event['data']['object']
        user_id = subscription['metadata'].get('user_id')
        
        if not user_id:
            return False
        
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            return False
        
        # Downgrade to free tier
        user.subscription_tier = SubscriptionTier.FREE
        user.subscription_status = 'canceled'
        user.subscription_end_date = datetime.fromtimestamp(subscription['canceled_at'])
        
        await db.commit()
        logger.info(f"Downgraded user {user_id} to free tier")
        return True
    
    @staticmethod
    async def _handle_payment_succeeded(event: Dict[str, Any], db: AsyncSession) -> bool:
        """Handle invoice.payment_succeeded webhook."""
        invoice = event['data']['object']
        subscription_id = invoice.get('subscription')
        
        if subscription_id:
            subscription = StripeService.get_subscription(subscription_id)
            if subscription:
                user_id = subscription['metadata'].get('user_id')
                if user_id:
                    from sqlalchemy import select
                    result = await db.execute(select(User).where(User.id == int(user_id)))
                    user = result.scalar_one_or_none()
                    if user:
                        user.subscription_status = 'active'
                        await db.commit()
                        logger.info(f"Payment succeeded for user {user_id}")
        
        return True
    
    @staticmethod
    async def _handle_payment_failed(event: Dict[str, Any], db: AsyncSession) -> bool:
        """Handle invoice.payment_failed webhook."""
        invoice = event['data']['object']
        subscription_id = invoice.get('subscription')
        
        if subscription_id:
            subscription = StripeService.get_subscription(subscription_id)
            if subscription:
                user_id = subscription['metadata'].get('user_id')
                if user_id:
                    from sqlalchemy import select
                    result = await db.execute(select(User).where(User.id == int(user_id)))
                    user = result.scalar_one_or_none()
                    if user:
                        user.subscription_status = 'past_due'
                        await db.commit()
                        logger.info(f"Payment failed for user {user_id}")
        
        return True
    
    @staticmethod
    def get_user_subscription_info(user: User) -> SubscriptionResponse:
        """Get comprehensive subscription information for a user."""
        subscription_info = {
            'tier': user.subscription_tier.value,
            'status': user.subscription_status,
            'start_date': user.subscription_start_date,
            'end_date': user.subscription_end_date,
            'is_premium': user.is_premium,
            'stripe_customer_id': user.stripe_customer_id
        }
        
        # Get Stripe subscription details if available
        if user.stripe_customer_id:
            try:
                customer = StripeService.get_customer(user.stripe_customer_id)
                if customer:
                    subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id, limit=1)
                    if subscriptions.data:
                        subscription = subscriptions.data[0]
                        subscription_info.update({
                            'stripe_subscription_id': subscription.id,
                            'current_period_end': datetime.fromtimestamp(subscription.current_period_end),
                            'cancel_at_period_end': subscription.cancel_at_period_end
                        })
            except Exception as e:
                logger.error(f"Error getting Stripe subscription info for user {user.id}: {e}")
        
        return SubscriptionResponse(**subscription_info)
