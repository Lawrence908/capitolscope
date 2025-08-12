import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CheckIcon,
  StarIcon,
  ShieldCheckIcon,
  BellIcon,
  ChartBarIcon,
  UserGroupIcon,
  SparklesIcon,
  BuildingOfficeIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

const PremiumSignup: React.FC = () => {
  const [selectedPlan, setSelectedPlan] = useState<'monthly' | 'yearly'>('monthly');
  const [isLoading, setIsLoading] = useState(false);

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

  const handleUpgrade = async (tier: string) => {
    setIsLoading(true);
    
    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      // TODO: Implement actual payment processing
      alert(`Payment processing for ${tier} tier will be implemented here. For now, this is a placeholder.`);
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <Link to="/dashboard" className="flex items-center">
              <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h1 className="ml-3 text-xl font-bold text-gray-900 dark:text-white">CapitolScope</h1>
            </Link>
            <Link
              to="/dashboard"
              className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white sm:text-5xl">
            Choose Your Plan
          </h1>
          <p className="mt-4 text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
            Unlock advanced features to get deeper insights into congressional trading activity and stay ahead of the market.
          </p>
        </div>

        {/* Pricing Toggle */}
        <div className="flex justify-center mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-1 shadow-sm">
            <div className="flex">
              <button
                onClick={() => setSelectedPlan('monthly')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  selectedPlan === 'monthly'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setSelectedPlan('yearly')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  selectedPlan === 'yearly'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                Yearly
                <span className="ml-1 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 px-1 rounded">
                  Save 17%
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
          {/* Free Plan */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Free</h3>
              <div className="mt-4">
                <span className="text-4xl font-bold text-gray-900 dark:text-white">$0</span>
                <span className="text-gray-600 dark:text-gray-400">/month</span>
              </div>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Get Started with Transparency
              </p>
              <div className="mt-2">
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                  Better than Capitol Trades
                </span>
              </div>
            </div>

            <div className="mt-8">
              <ul className="space-y-3">
                {features.map((feature) => (
                  <li key={feature.name} className="flex items-start">
                    <div className="flex-shrink-0">
                      {feature.free ? (
                        <CheckIcon className="h-4 w-4 text-green-500" />
                      ) : (
                        <div className="h-4 w-4 border-2 border-gray-300 dark:border-gray-600 rounded"></div>
                      )}
                    </div>
                    <div className="ml-2">
                      <p className={`text-xs ${feature.free ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'}`}>
                        {feature.name}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Pro Plan */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border-2 border-blue-500 relative p-6">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <div className="bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-medium flex items-center">
                <StarIcon className="h-3 w-3 mr-1" />
                Most Popular
              </div>
            </div>

            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Pro</h3>
              <div className="mt-4">
                <span className="text-4xl font-bold text-gray-900 dark:text-white">
                  ${plans[selectedPlan].pro.price}
                </span>
                <span className="text-gray-600 dark:text-gray-400">/{plans[selectedPlan].pro.period}</span>
              </div>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Power for Retail Investors
              </p>
            </div>

            <div className="mt-8">
              <ul className="space-y-3">
                {features.map((feature) => (
                  <li key={feature.name} className="flex items-start">
                    <div className="flex-shrink-0">
                      {feature.pro ? (
                        <CheckIcon className="h-4 w-4 text-green-500" />
                      ) : (
                        <div className="h-4 w-4 border-2 border-gray-300 dark:border-gray-600 rounded"></div>
                      )}
                    </div>
                    <div className="ml-2">
                      <p className={`text-xs ${feature.pro ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'}`}>
                        {feature.name}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-8">
              <button
                onClick={() => handleUpgrade('Pro')}
                disabled={isLoading}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? 'Processing...' : 'Upgrade to Pro'}
              </button>
            </div>
          </div>

          {/* Premium Plan */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border-2 border-purple-500 relative p-6">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <div className="bg-purple-600 text-white px-3 py-1 rounded-full text-xs font-medium flex items-center">
                <SparklesIcon className="h-3 w-3 mr-1" />
                Best Value
              </div>
            </div>

            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Premium</h3>
              <div className="mt-4">
                <span className="text-4xl font-bold text-gray-900 dark:text-white">
                  ${plans[selectedPlan].premium.price}
                </span>
                <span className="text-gray-600 dark:text-gray-400">/{plans[selectedPlan].premium.period}</span>
              </div>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                For Analysts and Devs
              </p>
            </div>

            <div className="mt-8">
              <ul className="space-y-3">
                {features.map((feature) => (
                  <li key={feature.name} className="flex items-start">
                    <div className="flex-shrink-0">
                      {feature.premium ? (
                        <CheckIcon className="h-4 w-4 text-green-500" />
                      ) : (
                        <div className="h-4 w-4 border-2 border-gray-300 dark:border-gray-600 rounded"></div>
                      )}
                    </div>
                    <div className="ml-2">
                      <p className={`text-xs ${feature.premium ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'}`}>
                        {feature.name}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-8">
              <button
                onClick={() => handleUpgrade('Premium')}
                disabled={isLoading}
                className="w-full bg-purple-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? 'Processing...' : 'Upgrade to Premium'}
              </button>
            </div>
          </div>

          {/* Enterprise Plan */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border-2 border-gray-800 relative p-6">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <div className="bg-gray-800 text-white px-3 py-1 rounded-full text-xs font-medium flex items-center">
                <BuildingOfficeIcon className="h-3 w-3 mr-1" />
                Enterprise
              </div>
            </div>

            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Enterprise</h3>
              <div className="mt-4">
                <span className="text-2xl font-bold text-gray-900 dark:text-white">
                  Contact Sales
                </span>
                <span className="text-gray-600 dark:text-gray-400 block text-sm">
                  Starts at ~${plans[selectedPlan].enterprise.price}/month
                </span>
              </div>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Custom Integrations & Teams
              </p>
            </div>

            <div className="mt-8">
              <ul className="space-y-3">
                {features.map((feature) => (
                  <li key={feature.name} className="flex items-start">
                    <div className="flex-shrink-0">
                      {feature.enterprise ? (
                        <CheckIcon className="h-4 w-4 text-green-500" />
                      ) : (
                        <div className="h-4 w-4 border-2 border-gray-300 dark:border-gray-600 rounded"></div>
                      )}
                    </div>
                    <div className="ml-2">
                      <p className={`text-xs ${feature.enterprise ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'}`}>
                        {feature.name}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-8">
              <button
                onClick={() => handleUpgrade('Enterprise')}
                disabled={isLoading}
                className="w-full bg-gray-800 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? 'Processing...' : 'Contact Sales'}
              </button>
            </div>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="mt-16 max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white text-center mb-8">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Can I cancel my subscription anytime?
              </h3>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                Yes, you can cancel your subscription at any time. You'll continue to have access to your current tier features until the end of your current billing period.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                What payment methods do you accept?
              </h3>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                We accept all major credit cards, debit cards, and PayPal. All payments are processed securely through Stripe.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Is there a free trial?
              </h3>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                Yes! You can try Premium features free for 7 days. No credit card required to start your trial.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                How often is the data updated?
              </h3>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                Our congressional trading data is updated daily from official sources. Premium users get real-time alerts when new trades are reported.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                How does your free tier compare to Capitol Trades?
              </h3>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                Our free tier includes trade alerts, basic portfolio analytics, and CSV export—features that Capitol Trades reserves for paid users. We believe in transparency and want to give you more value from the start.
              </p>
            </div>
          </div>
        </div>

        {/* Contact Support */}
        <div className="mt-16 text-center">
          <p className="text-gray-600 dark:text-gray-400">
            Have questions? Contact us at{' '}
            <a href="mailto:support@capitolscope.com" className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300">
              support@capitolscope.com
            </a>
          </p>
        </div>
      </main>
    </div>
  );
};

export default PremiumSignup; 