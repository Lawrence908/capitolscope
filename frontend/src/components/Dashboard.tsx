import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  UserGroupIcon,
  DocumentTextIcon,
  ArrowTrendingUpIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { CongressionalTrade, CongressMember, DataQualityStats } from '../types';
import apiClient from '../services/api';

const Dashboard: React.FC = () => {
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

        setStats(statsResponse);
        setRecentTrades(tradesResponse.items);
        setTopMembers(membersResponse);
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
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
          <div className="ml-3">
            <p className="text-sm text-red-800">{error}</p>
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
      color: 'bg-blue-500',
      link: '/trades',
    },
    {
      title: 'Congress Members',
      value: stats?.unique_members?.toLocaleString() || '0',
      icon: UserGroupIcon,
      color: 'bg-green-500',
      link: '/members',
    },
    {
      title: 'Unique Tickers',
      value: stats?.unique_tickers?.toLocaleString() || '0',
      icon: ArrowTrendingUpIcon,
      color: 'bg-purple-500',
      link: '/trades',
    },
    {
      title: 'Missing Tickers',
      value: `${stats?.null_ticker_percentage?.toFixed(1) || '0'}%`,
      icon: ExclamationTriangleIcon,
      color: 'bg-yellow-500',
      link: '/data-quality',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div className="card p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Welcome to CapitolScope
        </h2>
        <p className="text-gray-600">
          Explore congressional trading data with powerful filtering and analytics tools.
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <Link
              key={stat.title}
              to={stat.link}
              className="card p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center">
                <div className={`${stat.color} rounded-md p-3`}>
                  <Icon className="h-6 w-6 text-white" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                  <p className="text-2xl font-semibold text-gray-900">{stat.value}</p>
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Recent trades and top members */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent trades */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Recent Trades</h3>
            <Link
              to="/trades"
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              View all →
            </Link>
          </div>
          <div className="space-y-4">
            {recentTrades.map((trade) => (
              <div key={trade.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {trade.member?.full_name || 'Unknown'}
                  </p>
                  <p className="text-sm text-gray-500">
                    {trade.ticker ? (
                      <span className="font-mono">{trade.ticker}</span>
                    ) : (
                      <span className="text-gray-400">No ticker</span>
                    )}
                    {' • '}
                    <span className="capitalize">{trade.type}</span>
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-900">{trade.amount}</p>
                  <p className="text-xs text-gray-500">
                    {new Date(trade.transaction_date).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top trading members */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Top Trading Members</h3>
            <Link
              to="/members"
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              View all →
            </Link>
          </div>
          <div className="space-y-4">
            {topMembers.map((member) => (
              <div key={member.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {member.full_name}
                  </p>
                  <p className="text-sm text-gray-500">
                    {member.party} • {member.state}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-900">
                    {member.total_trades || 0} trades
                  </p>
                  <p className="text-xs text-gray-500">{member.chamber}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Party distribution */}
      {stats && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Party Distribution
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(stats.party_distribution).map(([party, count]) => (
              <div key={party} className="text-center">
                <div className="text-2xl font-bold text-gray-900">{count}</div>
                <div className="text-sm text-gray-600">{party}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard; 