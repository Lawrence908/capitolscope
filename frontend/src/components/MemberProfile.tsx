import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeftIcon, DocumentTextIcon, ChartBarIcon, UserIcon } from '@heroicons/react/24/outline';
import { apiClient } from '../services/api';
import type { CongressMember, CongressionalTrade } from '../types';

const MemberProfile: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [member, setMember] = useState<CongressMember | null>(null);
  const [recentTrades] = useState<CongressionalTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMemberData = async () => {
      if (!id) return;
      
      try {
        setLoading(true);
        // Use the proper getMember API endpoint
        const memberData = await apiClient.getMember(id);
        console.log('Member data received:', memberData);
        setMember(memberData);
        
        // TODO: Fetch recent trades for this member
        // const tradesResponse = await apiClient.getMemberTrades(id, 1, 10);
        // setRecentTrades(tradesResponse.items);
      } catch (err) {
        setError('Failed to load member data');
        console.error('Error fetching member:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchMemberData();
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600 dark:text-gray-400">Loading member profile...</div>
      </div>
    );
  }

  if (error || !member) {
    return (
      <div className="card p-6">
        <div className="flex items-center mb-4">
          <Link to="/members" className="btn-secondary btn-sm mr-4">
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Members
          </Link>
        </div>
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
            {error || 'Member not found'}
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            The requested member could not be found.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Link to="/members" className="btn-secondary btn-sm mr-4">
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Members
          </Link>
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Last updated: {new Date().toLocaleDateString()}
        </div>
      </div>

      {/* Member Info Card */}
      <div className="card p-6">
        <div className="flex items-start space-x-6">
          <div className="flex-shrink-0">
            <div className="w-24 h-24 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
              <UserIcon className="h-12 w-12 text-gray-400" />
            </div>
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              {member.full_name}
            </h1>
            <div className="flex items-center space-x-4 mb-4">
              {member.party && (
                <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full text-sm font-medium">
                  {member.party === 'D' ? 'Democratic' : member.party === 'R' ? 'Republican' : member.party}
                </span>
              )}
              {member.chamber && (
                <span className="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full text-sm font-medium">
                  {member.chamber}
                </span>
              )}
              {member.state && (
                <span className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-full text-sm font-medium">
                  {member.state}
                </span>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {member.trade_count?.toLocaleString() || 'N/A'}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Total Trades</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {member.total_trade_value ? `$${(member.total_trade_value / 100).toLocaleString()}` : 'N/A'}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Total Volume</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {member.portfolio_value ? `$${(member.portfolio_value / 100).toLocaleString()}` : 'N/A'}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Portfolio Value</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Trades */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 flex items-center">
            <DocumentTextIcon className="h-5 w-5 mr-2" />
            Recent Trades
          </h2>
          <Link to="/trades" className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">
            View all trades →
          </Link>
        </div>
        
        {recentTrades.length > 0 ? (
          <div className="space-y-4">
            {recentTrades.map((trade) => (
              <div key={trade.id} className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700 last:border-b-0">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-gray-900 dark:text-gray-100">
                      {trade.ticker || 'Unknown'}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {trade.transaction_type}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {new Date(trade.transaction_date).toLocaleDateString()}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-medium text-gray-900 dark:text-gray-100">
                    {trade.estimated_value ? `$${(trade.estimated_value / 100).toLocaleString()}` : 'N/A'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <ChartBarIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">No recent trades found</p>
          </div>
        )}
      </div>

      {/* Additional sections can be added here */}
      <div className="card p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">Additional Information</h2>
        <p className="text-gray-600 dark:text-gray-400">
          More detailed member information, voting records, committee assignments, and advanced analytics will be available soon.
        </p>
      </div>
    </div>
  );
};

export default MemberProfile; 