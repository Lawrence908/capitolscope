import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  UserGroupIcon,
  DocumentTextIcon,
  ArrowTrendingUpIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import type { CongressionalTrade, CongressMember, DataQualityStats } from '../types';
import apiClient from '../services/api';
import { HubFooter } from './HubFooter';

const PublicDashboard: React.FC = () => {
  const [stats, setStats] = useState<DataQualityStats | null>(null);
  const [recentTrades, setRecentTrades] = useState<CongressionalTrade[]>([]);
  const [topMembers, setTopMembers] = useState<CongressMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch data in parallel
        const [statsResponse, tradesResponse, membersResponse] = await Promise.all([
          apiClient.getDataQualityStats(),
          apiClient.getTrades({}, 1, 10),
          apiClient.getTopTradingMembers(10),
        ]);

        setStats(statsResponse.data);
        setRecentTrades(tradesResponse.items || []);
        setTopMembers(membersResponse.data || []);
      } catch (err) {
        setError('Failed to load dashboard data');
        console.error('Dashboard error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-light-primary dark:bg-bg-primary flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-bg-light-primary dark:bg-bg-primary flex items-center justify-center p-4">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4 max-w-md">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Total Trades',
      value: stats?.total_trades?.toLocaleString() || '0',
      icon: DocumentTextIcon,
      color: 'bg-primary-500',
    },
    {
      title: 'Congress Members',
      value: stats?.unique_members?.toLocaleString() || '0',
      icon: UserGroupIcon,
      color: 'bg-secondary-500',
    },
    {
      title: 'Unique Tickers',
      value: stats?.unique_tickers?.toLocaleString() || '0',
      icon: ArrowTrendingUpIcon,
      color: 'bg-neutral-500',
    },
    {
      title: 'Missing Tickers',
      value: `${stats?.null_ticker_percentage?.toFixed(1) || '0'}%`,
      icon: ExclamationTriangleIcon,
      color: 'bg-warning',
    },
  ];

  return (
    <div className="min-h-screen bg-bg-light-primary dark:bg-bg-primary">
      {/* Header with Sign In/Sign Up */}
      <header className="border-b border-neutral-200 dark:border-neutral-700 bg-bg-light-primary dark:bg-bg-primary sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <img 
                src="/favicon-64x64.png" 
                alt="CapitolScope Logo" 
                className="h-8 w-8 sm:h-10 sm:w-10 rounded-lg"
                loading="lazy"
                width="40"
                height="40"
              />
              <h1 className="ml-2 sm:ml-3 text-lg sm:text-xl font-bold text-primary-600 dark:text-primary-400">CapitolScope</h1>
            </div>
            <div className="flex items-center space-x-2 sm:space-x-4">
              <Link
                to="/login"
                className="hidden sm:block text-neutral-300 dark:text-neutral-400 hover:text-heading text-sm transition-colors"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="btn-primary text-sm px-3 py-2 sm:px-4 sm:py-2"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
        {/* Welcome header with CTA */}
        <div className="card p-4 lg:p-6 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-xl lg:text-2xl font-bold text-heading mb-2">
                Congressional Trading Transparency
              </h2>
              <p className="text-sm lg:text-base text-body">
                Explore congressional trading data with powerful filtering and analytics tools. Sign up for free to access advanced features.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <Link
                to="/register"
                className="btn-primary text-center px-6 py-2"
              >
                Sign Up Free
              </Link>
              <Link
                to="/login"
                className="btn-outline text-center px-6 py-2"
              >
                Sign In
              </Link>
            </div>
          </div>
        </div>

        {/* Stats cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6 mb-6">
          {statCards.map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.title}
                className="card-interactive p-4 lg:p-6 transition-all duration-200"
              >
                <div className="flex items-center">
                  <div className={`p-2 lg:p-3 rounded-lg ${stat.color}`}>
                    <Icon className="h-5 w-5 lg:h-6 lg:w-6 text-white" />
                  </div>
                  <div className="ml-3 lg:ml-4">
                    <p className="text-xs lg:text-sm font-medium text-body">
                      {stat.title}
                    </p>
                    <p className="text-lg lg:text-2xl font-semibold text-heading">
                      {stat.value}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Recent trades and top members */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6 mb-6">
          {/* Recent trades */}
          <div className="card p-4 lg:p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base lg:text-lg font-semibold text-heading">Recent Trades</h3>
              <Link
                to="/register"
                className="text-xs lg:text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
              >
                Sign up to view all →
              </Link>
            </div>
            <div className="space-y-3 lg:space-y-4">
              {recentTrades && recentTrades.length > 0 ? recentTrades.slice(0, 5).map((trade, index) => (
                <div key={trade.id || `trade-${index}`} className="flex items-center justify-between py-2 border-b border-neutral-200 dark:border-neutral-700 last:border-b-0">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs lg:text-sm font-medium text-heading truncate">
                      {trade.member_name || 'Unknown'}
                    </p>
                    <p className="text-xs lg:text-sm text-body">
                      {trade.ticker ? (
                        <span className="font-mono">{trade.ticker}</span>
                      ) : (
                        <span className="text-muted">No ticker</span>
                      )}
                      {' • '}
                      <span className="capitalize">{trade.transaction_type || 'Unknown'}</span>
                    </p>
                  </div>
                  <div className="text-right ml-2">
                    <p className="text-xs lg:text-sm text-heading">
                      {trade.estimated_value ? `$${(trade.estimated_value / 100).toLocaleString()}` : 'N/A'}
                    </p>
                    <p className="text-xs text-body">
                      {new Date(trade.transaction_date).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              )) : (
                <div className="text-center py-4 text-body">
                  <p className="text-sm">No recent trades available</p>
                </div>
              )}
            </div>
            {recentTrades && recentTrades.length > 5 && (
              <div className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
                <Link
                  to="/register"
                  className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 text-center block"
                >
                  Sign up to see all {recentTrades.length} recent trades →
                </Link>
              </div>
            )}
          </div>

          {/* Top trading members */}
          <div className="card p-4 lg:p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base lg:text-lg font-semibold text-heading">Top Trading Members</h3>
              <Link
                to="/register"
                className="text-xs lg:text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
              >
                Sign up to view all →
              </Link>
            </div>
            <div className="space-y-3 lg:space-y-4">
              {topMembers && topMembers.length > 0 ? topMembers.slice(0, 5).map((member, index) => (
                <div key={member.id || `member-${index}`} className="flex items-center justify-between py-2 border-b border-neutral-200 dark:border-neutral-700 last:border-b-0">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs lg:text-sm font-medium text-heading truncate">
                      {member.member_name}
                    </p>
                    <p className="text-xs lg:text-sm text-body">
                      {member.party} • {member.state}
                    </p>
                  </div>
                  <div className="text-right ml-2">
                    <p className="text-xs lg:text-sm text-heading">
                      {member.trade_count || 0} trades
                    </p>
                    <p className="text-xs text-body">{member.chamber}</p>
                  </div>
                </div>
              )) : (
                <div className="text-center py-4 text-body">
                  <p className="text-sm">No top members available</p>
                </div>
              )}
            </div>
            {topMembers && topMembers.length > 5 && (
              <div className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
                <Link
                  to="/register"
                  className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 text-center block"
                >
                  Sign up to see all {topMembers.length} top members →
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Party distribution */}
        {stats && (
          <div className="card p-4 lg:p-6 mb-6">
            <h3 className="text-base lg:text-lg font-semibold text-heading mb-4">
              Party Distribution
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {stats.party_distribution && Object.entries(stats.party_distribution).map(([party, count]) => (
                <div key={party} className="text-center">
                  <div className="text-xl lg:text-2xl font-bold text-heading">{count.toString()}</div>
                  <div className="text-xs lg:text-sm text-body">{party}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CTA Section */}
        <div className="card p-6 lg:p-8 bg-gradient-to-r from-primary-50 to-secondary-50 dark:from-primary-900/20 dark:to-secondary-900/20">
          <div className="text-center">
            <h3 className="text-xl lg:text-2xl font-bold text-heading mb-2">
              Ready to dive deeper?
            </h3>
            <p className="text-sm lg:text-base text-body mb-6 max-w-2xl mx-auto">
              Sign up for free to access advanced filtering, member profiles, analytics, and personalized alerts. 
              No credit card required.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/register"
                className="btn-primary px-8 py-3 text-lg"
              >
                Get Started Free
              </Link>
              <Link
                to="/login"
                className="btn-outline px-8 py-3 text-lg"
              >
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-neutral-200 dark:border-neutral-700 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center mb-4 md:mb-0">
              <img 
                src="/capitol-scope-logo.png" 
                alt="CapitolScope Logo" 
                className="h-8 w-8 rounded-lg shadow-glow-primary/20"
                loading="lazy"
                width="32"
                height="32"
              />
              <span className="ml-3 text-sm text-body">
                © 2025 CapitolScope. All rights reserved.
              </span>
            </div>
            
            <div className="flex items-center space-x-6">
              <Link
                to="/privacy"
                className="text-sm text-body hover:text-neutral-300 transition-colors"
              >
                Privacy Policy
              </Link>
              <Link
                to="/terms"
                className="text-sm text-body hover:text-neutral-300 transition-colors"
              >
                Terms of Service
              </Link>
              <a
                href="mailto:capitolscope@gmail.com"
                className="text-sm text-body hover:text-neutral-300 transition-colors"
              >
                Support
              </a>
            </div>
          </div>
        </div>
      </footer>
      
      {/* Hub Footer: link back to main site */}
      <HubFooter />
    </div>
  );
};

export default PublicDashboard;



