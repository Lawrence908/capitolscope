import React, { useState, useEffect, useCallback } from 'react';
import { format } from 'date-fns';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import type { CongressionalTrade, TradeFilters, PaginatedResponse } from '../types';
import apiClient from '../services/api';

const TradeBrowser: React.FC = () => {
  const [trades, setTrades] = useState<PaginatedResponse<CongressionalTrade> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<TradeFilters>({});
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Fetch trades with current filters and pagination
  const fetchTrades = useCallback(async (page: number = 1) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.getTrades(filters, page, 50);
      setTrades(response);
      setCurrentPage(page);
    } catch (err) {
      setError('Failed to fetch trades. Please try again.');
      console.error('Error fetching trades:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Initial load
  useEffect(() => {
    fetchTrades(1);
  }, [fetchTrades]);

  // Handle filter changes
  const handleFilterChange = (key: keyof TradeFilters, value: string | number | undefined) => {
    setFilters(prev => ({
      ...prev,
      [key]: value === '' ? undefined : value,
    }));
  };

  // Handle search
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setFilters(prev => ({
      ...prev,
      search: searchQuery || undefined,
    }));
  };

  // Clear filters
  const clearFilters = () => {
    setFilters({});
    setSearchQuery('');
  };

  // Format currency amounts
  const formatAmount = (amount: string) => {
    if (!amount) return 'N/A';
    return amount.replace(/\$/, '$');
  };

  // Get party color
  const getPartyColor = (party: string) => {
    switch (party?.toLowerCase()) {
      case 'republican':
        return 'text-red-600 bg-red-50';
      case 'democratic':
        return 'text-blue-600 bg-blue-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  // Get transaction type icon and color
  const getTransactionTypeStyle = (type: string) => {
    switch (type) {
      case 'purchase':
        return { icon: ArrowUpIcon, color: 'text-green-600' };
      case 'sale':
        return { icon: ArrowDownIcon, color: 'text-red-600' };
      default:
        return { icon: ExclamationTriangleIcon, color: 'text-yellow-600' };
    }
  };

  // Patch: Ensure trades.items is always an array
  const tradeItems = trades?.items ?? [];

  if (loading && !trades) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with search and filters */}
      <div className="card p-6">
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Congressional Trades</h2>
            <p className="text-sm text-gray-600 mt-1">
              {trades?.total ? `${trades.total.toLocaleString()} total trades` : 'Loading...'}
            </p>
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="btn-secondary flex items-center gap-2"
            >
              <FunnelIcon className="h-4 w-4" />
              Filters
            </button>
          </div>
        </div>

        {/* Search bar */}
        <form onSubmit={handleSearch} className="mt-4">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 dark:text-gray-500" />
            <input
              type="text"
              placeholder="Search by member name, ticker, or asset description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field pl-10"
            />
          </div>
        </form>

        {/* Filters panel */}
        {showFilters && (
          <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg transition-colors duration-200">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Transaction Type
                </label>
                <select
                  value={filters.type || ''}
                  onChange={(e) => handleFilterChange('type', e.target.value as any)}
                  className="input-field"
                >
                  <option value="">All Types</option>
                  <option value="purchase">Purchase</option>
                  <option value="sale">Sale</option>
                  <option value="exchange">Exchange</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Party
                </label>
                <select
                  value={filters.party || ''}
                  onChange={(e) => handleFilterChange('party', e.target.value)}
                  className="input-field"
                >
                  <option value="">All Parties</option>
                  <option value="Republican">Republican</option>
                  <option value="Democratic">Democratic</option>
                  <option value="Independent">Independent</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Chamber
                </label>
                <select
                  value={filters.chamber || ''}
                  onChange={(e) => handleFilterChange('chamber', e.target.value as any)}
                  className="input-field"
                >
                  <option value="">All Chambers</option>
                  <option value="House">House</option>
                  <option value="Senate">Senate</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Owner
                </label>
                <select
                  value={filters.owner || ''}
                  onChange={(e) => handleFilterChange('owner', e.target.value as any)}
                  className="input-field"
                >
                  <option value="">All Owners</option>
                  <option value="SP">Spouse</option>
                  <option value="JT">Joint</option>
                  <option value="DC">Dependent Child</option>
                  <option value="C">Self</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Date From
                </label>
                <input
                  type="date"
                  value={filters.date_from || ''}
                  onChange={(e) => handleFilterChange('date_from', e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Date To
                </label>
                <input
                  type="date"
                  value={filters.date_to || ''}
                  onChange={(e) => handleFilterChange('date_to', e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ticker
                </label>
                <input
                  type="text"
                  placeholder="e.g., AAPL, MSFT"
                  value={filters.ticker || ''}
                  onChange={(e) => handleFilterChange('ticker', e.target.value)}
                  className="input-field"
                />
              </div>

              <div className="flex items-end">
                <button
                  type="button"
                  onClick={clearFilters}
                  className="btn-secondary w-full"
                >
                  Clear Filters
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Trades table */}
      {trades && (
        <div className="card overflow-hidden">
          {tradeItems.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              <p className="text-lg font-semibold mb-2">No trades found</p>
              <p className="text-sm">Try adjusting your filters or check back later.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Member
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Asset
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Amount
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Owner
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {tradeItems.map((trade) => {
                    const { icon: TypeIcon, color } = getTransactionTypeStyle(trade.type);
                    
                    return (
                      <tr key={trade.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div>
                              <div className="text-sm font-medium text-gray-900">
                                {trade.member_name || 'Unknown'}
                              </div>
                              <div className="text-sm text-gray-500">
                                <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getPartyColor(trade.member_party || '')}`}>
                                  {trade.member_party}
                                </span>
                                <span className="ml-2">{trade.member_state}</span>
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {trade.ticker ? (
                              <span className="font-mono font-semibold">{trade.ticker}</span>
                            ) : (
                              <span className="text-gray-400">No ticker</span>
                            )}
                          </div>
                          <div className="text-sm text-gray-500 max-w-xs truncate">
                            {trade.asset_description}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className={`flex items-center ${color}`}>
                            <TypeIcon className="h-4 w-4 mr-1" />
                            <span className="capitalize text-sm font-medium">{trade.type}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {formatAmount(trade.amount)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {format(new Date(trade.transaction_date), 'MMM d, yyyy')}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {trade.owner === 'SP' ? 'Spouse' : 
                           trade.owner === 'JT' ? 'Joint' :
                           trade.owner === 'DC' ? 'Child' : 'Self'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {trades.pages > 1 && (
            <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
              <div className="flex-1 flex justify-between sm:hidden">
                <button
                  onClick={() => fetchTrades(currentPage - 1)}
                  disabled={!trades.has_prev}
                  className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => fetchTrades(currentPage + 1)}
                  disabled={!trades.has_next}
                  className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Showing{' '}
                    <span className="font-medium">
                      {(currentPage - 1) * 50 + 1}
                    </span>{' '}
                    to{' '}
                    <span className="font-medium">
                      {Math.min(currentPage * 50, trades.total)}
                    </span>{' '}
                    of{' '}
                    <span className="font-medium">{trades.total}</span> results
                  </p>
                </div>
                <div>
                  <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                    <button
                      onClick={() => fetchTrades(currentPage - 1)}
                      disabled={!trades.has_prev}
                      className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <span className="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700">
                      Page {currentPage} of {trades.pages}
                    </span>
                    <button
                      onClick={() => fetchTrades(currentPage + 1)}
                      disabled={!trades.has_next}
                      className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TradeBrowser; 