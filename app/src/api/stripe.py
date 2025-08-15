"""
Stripe API endpoints for CapitolScope.

This module provides REST API endpoints for Stripe integration including
checkout sessions, webhooks, and subscription management.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from core.auth import get_current_user
from core.services.stripe_service import StripeService
from domains.users.models import User
from domains.users.schemas import SubscriptionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stripe", tags=["stripe"])


from pydantic import BaseModel

class CheckoutSessionRequest(BaseModel):
    tier: str
    interval: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None

@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a Stripe Checkout session for subscription purchase.
    
    Args:
        tier: Subscription tier (pro, premium, enterprise)
        interval: Billing interval (monthly, yearly)
        success_url: Custom success URL
        cancel_url: Custom cancel URL
    """
    try:
        # Validate tier and interval
        valid_tiers = ['pro', 'premium', 'enterprise']
        valid_intervals = ['monthly', 'yearly']
        
        if request.tier not in valid_tiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier. Must be one of: {valid_tiers}"
            )
        
        if request.interval not in valid_intervals:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid interval. Must be one of: {valid_intervals}"
            )
        
        # Create checkout session
        session_data = StripeService.create_checkout_session(
            user=current_user,
            tier=request.tier,
            interval=request.interval,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        )
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create checkout session"
            )
        
        # Update user's Stripe customer ID if it was created
        if session_data.get('customer_id') and not current_user.stripe_customer_id:
            current_user.stripe_customer_id = session_data['customer_id']
            await db.commit()
        
        logger.info(f"Created checkout session for user {current_user.id}: {session_data['session_id']}")
        
        return {
            "session_id": session_data['session_id'],
            "url": session_data['url'],
            "message": "Checkout session created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout session for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/create-portal-session")
async def create_portal_session(
    return_url: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a Stripe Customer Portal session for subscription management.
    """
    try:
        if not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe customer associated with this account"
            )
        
        portal_url = StripeService.create_portal_session(
            user=current_user,
            return_url=return_url
        )
        
        if not portal_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create portal session"
            )
        
        logger.info(f"Created portal session for user {current_user.id}")
        
        return {
            "url": portal_url,
            "message": "Portal session created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating portal session for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/subscription")
async def get_subscription_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> SubscriptionResponse:
    """
    Get current user's subscription information.
    """
    try:
        subscription_info = StripeService.get_user_subscription_info(current_user)
        return subscription_info
        
    except Exception as e:
        logger.error(f"Error getting subscription info for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Handle Stripe webhook events.
    
    This endpoint receives webhook events from Stripe and processes them
    to update user subscriptions and payment status.
    """
    try:
        # Get the raw body and signature header
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )
        
        # Verify and construct the event
        event = StripeService.handle_webhook(payload, sig_header)
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature or payload"
            )
        
        # Process the webhook event
        success = await StripeService.process_webhook_event(event, db)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process webhook event"
            )
        
        logger.info(f"Successfully processed webhook event: {event['type']}")
        
        return {"status": "success", "message": "Webhook processed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/cancel-subscription")
async def cancel_subscription(
    at_period_end: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Cancel the current user's subscription.
    
    Args:
        at_period_end: If True, cancel at the end of the current period
    """
    try:
        if not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe customer associated with this account"
            )
        
        # Get the user's subscription
        subscription_info = StripeService.get_user_subscription_info(current_user)
        
        if not subscription_info.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active subscription found"
            )
        
        # Cancel the subscription
        success = StripeService.cancel_subscription(
            subscription_info.stripe_subscription_id,
            at_period_end=at_period_end
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel subscription"
            )
        
        logger.info(f"Canceled subscription for user {current_user.id}")
        
        return {
            "message": "Subscription canceled successfully",
            "cancel_at_period_end": at_period_end
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling subscription for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/upgrade-subscription")
async def upgrade_subscription(
    new_tier: str,
    interval: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Upgrade or downgrade the current user's subscription.
    
    Args:
        new_tier: New subscription tier (pro, premium, enterprise)
        interval: Billing interval (monthly, yearly)
    """
    try:
        # Validate inputs
        valid_tiers = ['pro', 'premium', 'enterprise']
        valid_intervals = ['monthly', 'yearly']
        
        if new_tier not in valid_tiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier. Must be one of: {valid_tiers}"
            )
        
        if interval not in valid_intervals:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid interval. Must be one of: {valid_intervals}"
            )
        
        # Get current subscription info
        subscription_info = StripeService.get_user_subscription_info(current_user)
        
        if not subscription_info.stripe_subscription_id:
            # No existing subscription, create a new checkout session
            session_data = StripeService.create_checkout_session(
                user=current_user,
                tier=new_tier,
                interval=interval
            )
            
            if not session_data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create checkout session"
                )
            
            return {
                "session_id": session_data['session_id'],
                "url": session_data['url'],
                "message": "Checkout session created for new subscription"
            }
        
        # Get the new price ID
        from core.services.stripe_service import STRIPE_PRICES
        new_price_id = STRIPE_PRICES.get(new_tier, {}).get(interval)
        
        if not new_price_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tier or interval combination"
            )
        
        # Update the subscription
        success = StripeService.update_subscription_tier(
            subscription_info.stripe_subscription_id,
            new_price_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update subscription"
            )
        
        logger.info(f"Updated subscription for user {current_user.id} to {new_tier} {interval}")
        
        return {
            "message": "Subscription updated successfully",
            "new_tier": new_tier,
            "interval": interval
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/prices")
async def get_prices():
    """
    Get available subscription prices and tiers.
    """
    try:
        from core.services.stripe_service import STRIPE_PRICES
        
        # Format prices for frontend consumption
        prices = {}
        for tier, intervals in STRIPE_PRICES.items():
            prices[tier] = {}
            for interval, price_id in intervals.items():
                if price_id:
                    try:
                        price = StripeService.get_price(price_id)
                        if price:
                            prices[tier][interval] = {
                                'price_id': price_id,
                                'amount': price.unit_amount / 100,  # Convert from cents
                                'currency': price.currency,
                                'interval': price.recurring.interval
                            }
                    except Exception as e:
                        logger.error(f"Error getting price {price_id}: {e}")
        
        return {
            "prices": prices,
            "message": "Prices retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Add a helper method to StripeService for getting price details
def get_price(price_id: str):
    """Get Stripe price details."""
    try:
        return stripe.Price.retrieve(price_id)
    except stripe.error.StripeError as e:
        logger.error(f"Error retrieving price {price_id}: {e}")
        return None

# Add the method to StripeService class
StripeService.get_price = staticmethod(get_price)
