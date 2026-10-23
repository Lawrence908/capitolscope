import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  CheckIcon,
  ShieldCheckIcon,
  BellIcon,
  ChartBarIcon,
  UserGroupIcon,
  SparklesIcon,
  BuildingOfficeIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import DarkModeToggle from './DarkModeToggle';
import stripeService from '../services/stripeService';
import type { SubscriptionInfo } from '../services/stripeService';

// Error Modal Component
interface ErrorModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
}

const ErrorModal: React.FC<ErrorModalProps> = ({ isOpen, onClose, title, message }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4 text-center">
        <div className="relative transform overflow-hidden border-2 border-content bg-surface-raised px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-sm sm:p-6">
          <div className="absolute right-0 top-0 hidden pr-4 pt-4 sm:block">
            <button
              type="button"
              className="text-content-faint hover:text-content focus:outline-none focus-ring"
              onClick={onClose}
            >
              <span className="sr-only">Close</span>
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          <div className="sm:flex sm:items-start">
            <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full sm:mx-0 sm:h-10 sm:w-10">
              <ExclamationTriangleIcon className="h-6 w-6 text-accent" />
            </div>
            <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
              <h3 className="font-display text-3xl font-extrabold leading-none text-content">
                {title}
              </h3>
              <div className="mt-2">
                <p className="text-sm text-content-muted">
                  {message}
                </p>
              </div>
            </div>
          </div>
          <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              className="btn-primary inline-flex w-full justify-center text-sm focus-ring sm:ml-3 sm:w-auto"
              onClick={onClose}
            >
              OK
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Payment Modal Component
interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  type: 'success' | 'cancelled';
  message: string;
  tier?: string;
}

const PaymentModal: React.FC<PaymentModalProps> = ({ isOpen, onClose, type, message }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4 text-center">
        <div className="relative transform overflow-hidden border-2 border-content bg-surface-raised px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-sm sm:p-6">
          <div className="absolute right-0 top-0 hidden pr-4 pt-4 sm:block">
            <button
              type="button"
              className="text-content-faint hover:text-content focus:outline-none focus-ring"
              onClick={onClose}
            >
              <span className="sr-only">Close</span>
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          <div className="sm:flex sm:items-start">
            <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full sm:mx-0 sm:h-10 sm:w-10">
              {type === 'success' ? (
                <CheckIcon className="h-6 w-6 text-content" />
              ) : (
                <ExclamationTriangleIcon className="h-6 w-6 text-accent" />
              )}
            </div>
            <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
              <h3 className="font-display text-3xl font-extrabold leading-none text-content">
                {type === 'success' ? 'Payment Successful!' : 'Payment Cancelled'}
              </h3>
              <div className="mt-2">
                <p className="text-sm text-content-muted">
                  {message}
                </p>
              </div>
            </div>
          </div>
          <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              className="btn-primary inline-flex w-full justify-center text-sm focus-ring sm:ml-3 sm:w-auto"
              onClick={onClose}
            >
              {type === 'success' ? 'Get Started' : 'OK'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const PremiumSignup: React.FC = () => {
  const [selectedPlan, setSelectedPlan] = useState<'monthly' | 'yearly'>('monthly');
  const [isLoading, setIsLoading] = useState(false);
  const [subscriptionInfo, setSubscriptionInfo] = useState<SubscriptionInfo | null>(null);
  const location = useLocation();
  const [errorModal, setErrorModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
  }>({
    isOpen: false,
    title: '',
    message: '',
  });

  const [paymentModal, setPaymentModal] = useState<{
    isOpen: boolean;
    type: 'success' | 'cancelled';
    message: string;
    tier?: string;
  }>({
    isOpen: false,
    type: 'success',
    message: '',
  });
  
  // Get redirect information from location state
  const redirectInfo = location.state as {
    from?: string;
    requiredTier?: string;
    featureName?: string;
  } | null;

  const plans = {
    monthly: {
      free: { price: 0, period: 'month', savings: null },
      pro: { price: 5.99, period: 'month', savings: null },
      premium: { price: 14.99, period: 'month', savings: null },
      enterprise: { price: 49.99, period: 'month', savings: null },
    },
    yearly: {
      free: { price: 0, period: 'year', savings: null },
      pro: { price: 59.99, period: 'year', savings: 'Save 17%' },
      premium: { price: 149.99, period: 'year', savings: 'Save 17%' },
      enterprise: { price: 499.99, period: 'year', savings: 'Save 17%' },
    },
  };

  const features = [
    {
      name: 'Basic Search & Browse',
      description: 'Search and filter congressional trading data',
      icon: ChartBarIcon,
      free: true,
      pro: true,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Member Profiles',
      description: 'Detailed profiles of congress members and their trading history',
      icon: UserGroupIcon,
      free: true,
      pro: true,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Two-Factor Authentication',
      description: 'Enhanced security for your account',
      icon: ShieldCheckIcon,
      free: true,
      pro: true,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Active Sessions',
      description: 'Manage your login sessions across devices',
      icon: ShieldCheckIcon,
      free: true,
      pro: true,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Trade Alerts',
      description: 'Get notified of new congressional trades in real-time',
      icon: BellIcon,
      free: true,
      pro: true,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Basic Portfolio Analytics',
      description: 'Basic portfolio performance and analytics',
      icon: ChartBarIcon,
      free: true,
      pro: true,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Export to CSV',
      description: 'Export trading data to CSV format',
      icon: ChartBarIcon,
      free: true,
      pro: true,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Limited Historical Data',
      description: 'Access to 3 months of historical trade data',
      icon: ExclamationTriangleIcon,
      free: true,
      pro: false,
      premium: false,
      enterprise: false,
    },
    {
      name: 'Full Historical Data',
      description: 'Complete access to all historical trading data',
      icon: ChartBarIcon,
      free: false,
      pro: true,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Weekly Summaries',
      description: 'Comprehensive weekly trading activity reports',
      icon: ChartBarIcon,
      free: false,
      pro: true,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Multiple Buyer Alerts',
      description: 'Alerts when 5+ members buy same stock in 3 months',
      icon: BellIcon,
      free: false,
      pro: true,
      premium: true,
      enterprise: true,
    },
    {
      name: 'High-Value Trade Alerts',
      description: 'Alerts for trades over $1M',
      icon: BellIcon,
      free: false,
      pro: true,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Saved Portfolios / Watchlists',
      description: 'Save and track your favorite portfolios',
      icon: UserGroupIcon,
      free: false,
      pro: true,
      premium: true,
      enterprise: true,
    },
    {
      name: 'TradingView-Style Charts',
      description: 'Interactive stock charts with trade overlays',
      icon: ChartBarIcon,
      free: false,
      pro: false,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Advanced Portfolio Analytics',
      description: 'Advanced trading patterns and insights',
      icon: ChartBarIcon,
      free: false,
      pro: false,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Sector/Committee-based Filters',
      description: 'Filter trades by congressional committees and sectors',
      icon: ChartBarIcon,
      free: false,
      pro: false,
      premium: true,
      enterprise: true,
    },
    {
      name: 'API Access (Rate-limited)',
      description: 'Programmatic access to trading data',
      icon: SparklesIcon,
      free: false,
      pro: false,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Custom Alert Configurations',
      description: 'Create custom alerts for specific criteria',
      icon: BellIcon,
      free: false,
      pro: false,
      premium: true,
      enterprise: true,
    },
    {
      name: 'Advanced Analytics Dashboard',
      description: 'Advanced analytics and pattern recognition',
      icon: ChartBarIcon,
      free: false,
      pro: false,
      premium: false,
      enterprise: true,
    },
    {
      name: 'White-Label Dashboard Options',
      description: 'Custom branding and deployment options',
      icon: BuildingOfficeIcon,
      free: false,
      pro: false,
      premium: false,
      enterprise: true,
    },
    {
      name: 'Priority Support',
      description: 'Priority customer support and assistance',
      icon: BuildingOfficeIcon,
      free: false,
      pro: false,
      premium: false,
      enterprise: true,
    },
    {
      name: 'Increased API Limits',
      description: 'Higher rate limits for API access',
      icon: SparklesIcon,
      free: false,
      pro: false,
      premium: false,
      enterprise: true,
    },
    {
      name: 'Team Seats / Admin Panel',
      description: 'Manage team access and permissions',
      icon: UserGroupIcon,
      free: false,
      pro: false,
      premium: false,
      enterprise: true,
    },
  ];

  // Handle payment success/cancellation on component mount
  useEffect(() => {
    const paymentSuccess = stripeService.handlePaymentSuccess();
    const paymentCancelled = stripeService.handlePaymentCancellation();
    
    if (paymentSuccess.success) {
      // Show success message and redirect to dashboard
      window.location.href = `/dashboard?payment=success&tier=${paymentSuccess.tier || 'pro'}`;
    }
    
    if (paymentCancelled.cancelled) {
      // Show cancellation message in modal
      setPaymentModal({
        isOpen: true,
        type: 'cancelled',
        message: paymentCancelled.message || 'Payment was cancelled.',
      });
      // Clean up URL params
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // Load subscription info on component mount
  useEffect(() => {
    const loadSubscriptionInfo = async () => {
      try {
        const info = await stripeService.getSubscriptionInfo();
        setSubscriptionInfo(info);
      } catch (error) {
        console.error('Error loading subscription info:', error);
      }
    };
    
    loadSubscriptionInfo();
  }, []);

  const handleUpgrade = async (tier: string) => {
    if (tier === 'free') {
      return; // No action needed for free tier
    }
    
    setIsLoading(true);
    
    try {
      const response = await stripeService.createCheckoutSession({
        tier: tier.toLowerCase(),
        interval: selectedPlan,
        success_url: `${window.location.origin}/dashboard?payment=success&tier=${tier}`,
        cancel_url: `${window.location.origin}/premium?payment=cancelled`
      });
      
      // Redirect to Stripe Checkout
      stripeService.redirectToCheckout(response.url);
      
    } catch (error) {
      console.error('Error creating checkout session:', error);
      setErrorModal({
        isOpen: true,
        title: 'Payment Error',
        message: 'Failed to process payment. Please check your connection and try again. If the problem persists, please contact support.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleManageSubscription = async () => {
    try {
      const response = await stripeService.createPortalSession(
        `${window.location.origin}/premium`
      );
      stripeService.redirectToPortal(response.url);
    } catch (error) {
      console.error('Error creating portal session:', error);
      setErrorModal({
        isOpen: true,
        title: 'Subscription Management Error',
        message: 'Unable to open subscription management. This usually means you don\'t have an active subscription or there was an issue with your Stripe account. Please contact support if this persists.',
      });
    }
  };

  const closeErrorModal = () => {
    setErrorModal(prev => ({ ...prev, isOpen: false }));
  };

  const closePaymentModal = () => {
    setPaymentModal(prev => ({ ...prev, isOpen: false }));
  };

  return (
    <div className="min-h-screen bg-surface">
      {/* Header */}
      <header className="bg-slab text-slab-on">
        <div className="mx-auto flex h-[68px] max-w-[1320px] items-center justify-between px-4 sm:px-8">
          <Link to="/" className="flex shrink-0 items-center gap-2.5" aria-label="CapitolScope home">
            <span aria-hidden="true" className="block h-9 w-1.5 bg-accent" />
            <span className="font-display text-[21px] font-extrabold leading-[0.82] tracking-[0.02em] text-slab-on">
              CAPITOL
              <br />
              SCOPE
            </span>
          </Link>
          <div className="flex items-center gap-4">
            <DarkModeToggle />
            <Link
              to="/dashboard"
              className="font-ui text-sm font-semibold text-slab-muted transition-colors hover:text-slab-on"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        {/* Redirect Banner */}
        {redirectInfo && (
          <div className="mb-8 border-l-4 border-accent bg-surface-inset p-4 lg:p-6">
            <div className="flex items-center">
              <ExclamationTriangleIcon className="mr-3 h-5 w-5 flex-shrink-0 text-accent" />
              <div>
                <h3 className="font-display text-2xl font-extrabold leading-none text-content">
                  {redirectInfo.featureName ? `${redirectInfo.featureName} Requires ${redirectInfo.requiredTier?.toUpperCase()} Subscription` : 'Premium Feature Access Required'}
                </h3>
                <p className="mt-1 font-ui text-sm text-content-muted">
                  {redirectInfo.featureName 
                    ? `You need a ${redirectInfo.requiredTier} subscription to access ${redirectInfo.featureName}.`
                    : 'This feature requires a premium subscription. Choose a plan below to continue.'
                  }
                </p>
                {redirectInfo.from && (
                  <p className="mt-1 font-ui text-xs text-content-faint">
                    Redirected from: {redirectInfo.from}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="mb-8 border-b-[3px] border-content pb-6 sm:mb-10">
          <h1 className="font-display text-6xl font-extrabold leading-[0.9] text-content sm:text-7xl">
            Choose Your Plan
          </h1>
          <p className="mt-4 max-w-3xl font-ui text-[17px] text-content-muted">
            Unlock advanced features to get deeper insights into congressional trading activity and stay ahead of the market.
          </p>
        </div>

        {/* Pricing Toggle */}
        <div className="mb-8 flex">
          <div className="border-2 border-content">
            <div className="flex">
              <button
                onClick={() => setSelectedPlan('monthly')}
                className={`px-4 py-2 font-display text-lg font-extrabold uppercase tracking-[0.02em] transition-colors ${
                  selectedPlan === 'monthly'
                    ? 'bg-content text-surface'
                    : 'text-content-muted hover:text-content'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setSelectedPlan('yearly')}
                className={`px-4 py-2 font-display text-lg font-extrabold uppercase tracking-[0.02em] transition-colors ${
                  selectedPlan === 'yearly'
                    ? 'bg-content text-surface'
                    : 'text-content-muted hover:text-content'
                }`}
              >
                Yearly
              </button>
            </div>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="mb-16 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {/* Free Plan */}
          <div className="flex flex-col border-2 border-content p-6">
                          <div>
                <h3 className="font-display text-4xl font-extrabold uppercase leading-none text-content">Free</h3>
                <div className="mt-4">
                  <span className="font-display text-6xl font-extrabold leading-none tabular-nums text-content">$0</span>
                  <span className="ml-1 font-ui text-sm text-content-faint">/{plans[selectedPlan].free.period}</span>
                </div>
                <p className="mt-2 font-ui text-sm text-content-muted">Perfect for getting started</p>
              </div>
            <div className="mt-auto pt-6">
              <button
                onClick={() => handleUpgrade('free')}
                disabled={isLoading}
                className="w-full btn-outline disabled:opacity-50"
              >
                {isLoading ? 'Processing...' : 'Current Plan'}
              </button>
            </div>
          </div>

          {/* Pro Plan */}
          <div className="relative flex flex-col border-[3px] border-content p-6 pt-10">
            <div className="absolute inset-x-0 top-0">
              <span className="block bg-slab px-3 py-1 text-center font-ui text-[11px] font-bold uppercase tracking-[0.12em] text-slab-on">Most popular</span>
            </div>
                          <div>
                <h3 className="font-display text-4xl font-extrabold uppercase leading-none text-content">Pro</h3>
                <div className="mt-4">
                  <span className="font-display text-6xl font-extrabold leading-none tabular-nums text-content">${plans[selectedPlan].pro.price}</span>
                  <span className="ml-1 font-ui text-sm text-content-faint">/{plans[selectedPlan].pro.period}</span>
                </div>
                {plans[selectedPlan].pro.savings && (
                  <p className="mt-2 font-ui text-sm font-bold text-content">{plans[selectedPlan].pro.savings}</p>
                )}
                <p className="mt-2 font-ui text-sm text-content-muted">For serious investors</p>
              </div>
            <div className="mt-auto pt-6">
              <button
                onClick={() => handleUpgrade('pro')}
                disabled={isLoading}
                className="w-full btn-primary disabled:opacity-50"
              >
                {isLoading ? 'Processing...' : 'Upgrade to Pro'}
              </button>
            </div>
          </div>

          {/* Premium Plan */}
          <div className="flex flex-col border-2 border-content p-6">
                          <div>
                <h3 className="font-display text-4xl font-extrabold uppercase leading-none text-content">Premium</h3>
                <div className="mt-4">
                  <span className="font-display text-6xl font-extrabold leading-none tabular-nums text-content">${plans[selectedPlan].premium.price}</span>
                  <span className="ml-1 font-ui text-sm text-content-faint">/{plans[selectedPlan].premium.period}</span>
                </div>
                {plans[selectedPlan].premium.savings && (
                  <p className="mt-2 font-ui text-sm font-bold text-content">{plans[selectedPlan].premium.savings}</p>
                )}
                <p className="mt-2 font-ui text-sm text-content-muted">For power users</p>
              </div>
            <div className="mt-auto pt-6">
              <button
                onClick={() => handleUpgrade('premium')}
                disabled={isLoading}
                className="w-full btn-secondary disabled:opacity-50"
              >
                {isLoading ? 'Processing...' : 'Upgrade to Premium'}
              </button>
            </div>
          </div>

          {/* Enterprise Plan */}
          <div className="flex flex-col border-2 border-content p-6">
                          <div>
                <h3 className="font-display text-4xl font-extrabold uppercase leading-none text-content">Enterprise</h3>
                <div className="mt-4">
                  <span className="font-display text-6xl font-extrabold leading-none tabular-nums text-content">${plans[selectedPlan].enterprise.price}</span>
                  <span className="ml-1 font-ui text-sm text-content-faint">/{plans[selectedPlan].enterprise.period}</span>
                </div>
                {plans[selectedPlan].enterprise.savings && (
                  <p className="mt-2 font-ui text-sm font-bold text-content">{plans[selectedPlan].enterprise.savings}</p>
                )}
                <p className="mt-2 font-ui text-sm text-content-muted">For organizations</p>
              </div>
            <div className="mt-auto pt-6">
              <button
                onClick={() => handleUpgrade('enterprise')}
                disabled={isLoading}
                className="w-full btn-secondary disabled:opacity-50"
              >
                {isLoading ? 'Processing...' : 'Contact Sales'}
              </button>
            </div>
          </div>
        </div>

        {/* Features Table */}
        <div className="section-rule overflow-hidden">
          <div className="border-b border-line py-3">
            <h2 className="font-display text-4xl font-extrabold leading-none text-content">Feature comparison</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b-2 border-content">
                  <th className="px-6 py-3 text-left font-display text-lg font-extrabold uppercase tracking-[0.02em] text-content">Feature</th>
                  <th className="px-6 py-3 text-center font-display text-lg font-extrabold uppercase tracking-[0.02em] text-content">Free</th>
                  <th className="px-6 py-3 text-center font-display text-lg font-extrabold uppercase tracking-[0.02em] text-content">Pro</th>
                  <th className="px-6 py-3 text-center font-display text-lg font-extrabold uppercase tracking-[0.02em] text-content">Premium</th>
                  <th className="px-6 py-3 text-center font-display text-lg font-extrabold uppercase tracking-[0.02em] text-content">Enterprise</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {features.map((feature, index) => {
                  const Icon = feature.icon;
                  return (
                    <tr key={index} className="transition-colors hover:bg-surface-inset">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <Icon className="mr-3 h-5 w-5 text-content" />
                          <div>
                            <div className="font-ui text-sm font-bold text-content">{feature.name}</div>
                            <div className="font-ui text-sm text-content-muted">{feature.description}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        {feature.free ? (
                          <CheckIcon className="mx-auto h-5 w-5 text-content" />
                        ) : (
                          <span className="text-content-faint" aria-label="Not included">–</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        {feature.pro ? (
                          <CheckIcon className="mx-auto h-5 w-5 text-content" />
                        ) : (
                          <span className="text-content-faint" aria-label="Not included">–</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        {feature.premium ? (
                          <CheckIcon className="mx-auto h-5 w-5 text-content" />
                        ) : (
                          <span className="text-content-faint" aria-label="Not included">–</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        {feature.enterprise ? (
                          <CheckIcon className="mx-auto h-5 w-5 text-content" />
                        ) : (
                          <span className="text-content-faint" aria-label="Not included">–</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="mt-16 max-w-3xl">
          <h2 className="mb-6 border-t-[3px] border-content pt-3 font-display text-4xl font-extrabold leading-none text-content">
            Frequently Asked Questions
          </h2>
                      <div className="space-y-6">
              <div className="border-b border-line pb-5">
                <h3 className="font-ui text-base font-bold text-content">
                  Can I cancel my subscription anytime?
                </h3>
                <p className="mt-2 text-content-muted">
                  Yes, you can cancel your subscription at any time. You'll continue to have access to your current tier features until the end of your current billing period.
                </p>
              </div>
              <div className="border-b border-line pb-5">
                <h3 className="font-ui text-base font-bold text-content">
                  What payment methods do you accept?
                </h3>
                <p className="mt-2 text-content-muted">
                  We accept all major credit cards, debit cards, and PayPal. All payments are processed securely through Stripe.
                </p>
              </div>
              <div className="border-b border-line pb-5">
                <h3 className="font-ui text-base font-bold text-content">
                  Is there a free trial?
                </h3>
                <p className="mt-2 text-content-muted">
                  Yes! You can try Premium features free for 7 days. No credit card required to start your trial.
                </p>
              </div>
              <div className="border-b border-line pb-5">
                <h3 className="font-ui text-base font-bold text-content">
                  How often is the data updated?
                </h3>
                <p className="mt-2 text-content-muted">
                  Our congressional trading data is updated daily from official sources. Premium users get real-time alerts when new trades are reported.
                </p>
              </div>
              <div className="border-b border-line pb-5">
                <h3 className="font-ui text-base font-bold text-content">
                  How does your free tier compare to Capitol Trades?
                </h3>
                <p className="mt-2 text-content-muted">
                  Our free tier includes trade alerts, basic portfolio analytics, and CSV export: features that Capitol Trades reserves for paid users. We believe in transparency and want to give you more value from the start.
                </p>
              </div>
            </div>
        </div>

        {/* Current Subscription Info */}
        {subscriptionInfo && (
          <div className="mt-16 max-w-2xl">
            <div className="section-rule pt-3">
              <h2 className="mb-4 font-display text-4xl font-extrabold leading-none text-content">Current subscription</h2>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-content-muted">Plan:</span>
                  <span className="font-medium text-content">
                    {stripeService.getTierDisplayName(subscriptionInfo.tier)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-content-muted">Status:</span>
                  <span className={`font-medium ${
                    subscriptionInfo.status === 'active' ? 'text-content' : 'text-accent'
                  }`}>
                    {subscriptionInfo.status}
                  </span>
                </div>
                {subscriptionInfo.current_period_end && (
                  <div className="flex justify-between">
                    <span className="text-content-muted">Next billing:</span>
                    <span className="text-content">
                      {new Date(subscriptionInfo.current_period_end).toLocaleDateString()}
                    </span>
                  </div>
                )}
                {subscriptionInfo.cancel_at_period_end && (
                  <div className="border-l-4 border-accent bg-surface-inset p-3">
                    <p className="font-ui text-sm text-content">
                      Your subscription will be canceled at the end of the current billing period.
                    </p>
                  </div>
                )}
              </div>
              
              {subscriptionInfo.stripe_customer_id && subscriptionInfo.status === 'active' && (
                <div className="mt-6">
                  <button
                    onClick={handleManageSubscription}
                    className="btn-outline w-full"
                  >
                    Manage Subscription
                  </button>
                </div>
              )}
              
              {(!subscriptionInfo.stripe_customer_id || subscriptionInfo.status !== 'active') && (
                <div className="mt-6">
                  <p className="text-sm text-content-muted text-center">
                    {!subscriptionInfo.stripe_customer_id 
                      ? 'No active subscription found. Please upgrade to manage your subscription.'
                      : 'Your subscription is not active. Please contact support for assistance.'
                    }
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Contact Support */}
        <div className="mt-16 text-center">
          <p className="text-content-muted">
            Have questions? Contact us at{' '}
            <a href="mailto:capitolscope@gmail.com" className="font-semibold text-accent transition-colors hover:text-accent-strong">
              capitolscope@gmail.com
            </a>
          </p>
        </div>
      </main>
      
      {/* Error Modal */}
      <ErrorModal
        isOpen={errorModal.isOpen}
        onClose={closeErrorModal}
        title={errorModal.title}
        message={errorModal.message}
      />

      {/* Payment Modal */}
      <PaymentModal
        isOpen={paymentModal.isOpen}
        onClose={closePaymentModal}
        type={paymentModal.type}
        message={paymentModal.message}
        tier={paymentModal.tier}
      />
    </div>
  );
};

export default PremiumSignup; 