/**
 * Stripe Service for Frontend
 * 
 * This service handles all Stripe-related API calls and provides
 * a clean interface for subscription management.
 */

export interface CheckoutSessionRequest {
  tier: string;
  interval: string;
  success_url?: string;
  cancel_url?: string;
}

export interface CheckoutSessionResponse {
  session_id: string;
  url: string;
  message: string;
}

export interface SubscriptionInfo {
  tier: string;
  status: string;
  start_date?: string;
  end_date?: string;
  is_premium: boolean;
  stripe_customer_id?: string;
  stripe_subscription_id?: string;
  current_period_end?: string;
  cancel_at_period_end?: boolean;
}

export interface PortalSessionResponse {
  url: string;
  message: string;
}

export interface PriceInfo {
  price_id: string;
  amount: number;
  currency: string;
  interval: string;
}

export interface PricesResponse {
  prices: {
    [tier: string]: {
      [interval: string]: PriceInfo;
    };
  };
  message: string;
}

class StripeService {
  private baseUrl: string;
  private getAuthHeaders: () => Record<string, string>;

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_URL || '/api';
    this.getAuthHeaders = () => {
      // Get tokens from localStorage (stored as JSON object)
      const storedTokens = localStorage.getItem('capitolscope_tokens');
      let token = null;
      
      if (storedTokens) {
        try {
          const tokens = JSON.parse(storedTokens);
          token = tokens.access_token;
        } catch (error) {
          console.error('Error parsing stored tokens:', error);
        }
      }
      
      return {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` })
      };
    };
  }

  /**
   * Create a Stripe Checkout session for subscription purchase
   */
  async createCheckoutSession(request: CheckoutSessionRequest): Promise<CheckoutSessionResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/stripe/create-checkout-session`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create checkout session');
    }

    return response.json();
  }

  /**
   * Create a Stripe Customer Portal session for subscription management
   */
  async createPortalSession(returnUrl?: string): Promise<PortalSessionResponse> {
    const url = new URL(`${this.baseUrl}/api/v1/stripe/create-portal-session`);
    if (returnUrl) {
      url.searchParams.set('return_url', returnUrl);
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create portal session');
    }

    return response.json();
  }

  /**
   * Get current user's subscription information
   */
  async getSubscriptionInfo(): Promise<SubscriptionInfo> {
    const response = await fetch(`${this.baseUrl}/api/v1/stripe/subscription`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get subscription info');
    }

    return response.json();
  }

  /**
   * Cancel the current user's subscription
   */
  async cancelSubscription(atPeriodEnd: boolean = true): Promise<{ message: string; cancel_at_period_end: boolean }> {
    const response = await fetch(`${this.baseUrl}/api/v1/stripe/cancel-subscription`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ at_period_end: atPeriodEnd })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to cancel subscription');
    }

    return response.json();
  }

  /**
   * Upgrade or downgrade the current user's subscription
   */
  async upgradeSubscription(newTier: string, interval: string): Promise<CheckoutSessionResponse | { message: string; new_tier: string; interval: string }> {
    const response = await fetch(`${this.baseUrl}/api/v1/stripe/upgrade-subscription`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({
        new_tier: newTier,
        interval: interval
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to upgrade subscription');
    }

    return response.json();
  }

  /**
   * Get available subscription prices and tiers
   */
  async getPrices(): Promise<PricesResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/stripe/prices`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get prices');
    }

    return response.json();
  }

  /**
   * Redirect to Stripe Checkout
   */
  redirectToCheckout(checkoutUrl: string): void {
    window.location.href = checkoutUrl;
  }

  /**
   * Redirect to Stripe Customer Portal
   */
  redirectToPortal(portalUrl: string): void {
    window.location.href = portalUrl;
  }

  /**
   * Handle payment success redirect
   */
  handlePaymentSuccess(): { success: boolean; tier?: string; message?: string } {
    const urlParams = new URLSearchParams(window.location.search);
    const payment = urlParams.get('payment');
    const tier = urlParams.get('tier');

    if (payment === 'success') {
      return {
        success: true,
        tier: tier || undefined,
        message: tier ? `Successfully upgraded to ${tier} tier!` : 'Payment successful!'
      };
    }

    return { success: false };
  }

  /**
   * Handle payment cancellation
   */
  handlePaymentCancellation(): { cancelled: boolean; message?: string } {
    const urlParams = new URLSearchParams(window.location.search);
    const payment = urlParams.get('payment');

    if (payment === 'cancelled') {
      return {
        cancelled: true,
        message: 'Payment was cancelled. You can try again anytime.'
      };
    }

    return { cancelled: false };
  }

  /**
   * Format price for display
   */
  formatPrice(amount: number, currency: string = 'USD'): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  }

  /**
   * Get tier display name
   */
  getTierDisplayName(tier: string): string {
    const tierNames: Record<string, string> = {
      'free': 'Free',
      'pro': 'Pro',
      'premium': 'Premium',
      'enterprise': 'Enterprise'
    };
    return tierNames[tier.toLowerCase()] || tier;
  }

  /**
   * Get interval display name
   */
  getIntervalDisplayName(interval: string): string {
    const intervalNames: Record<string, string> = {
      'monthly': 'Monthly',
      'yearly': 'Yearly'
    };
    return intervalNames[interval.toLowerCase()] || interval;
  }
}

// Export singleton instance
export const stripeService = new StripeService();
export default stripeService;
