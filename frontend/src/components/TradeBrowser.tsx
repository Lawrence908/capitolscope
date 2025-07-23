import React, { useState, useEffect, useCallback } from 'react';
import { format } from 'date-fns';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import type { CongressionalTrade, TradeFilters, PaginatedResponse } from '../types/index';
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
    setFilters((prev: TradeFilters) => ({
      ...prev,
      [key]: value === '' ? undefined : value,
    }));
  };

  // Handle search
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setFilters((prev: TradeFilters) => ({
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
  const formatAmount = (amount: number | string | undefined | null) => {
    if (amount === undefined || amount === null || amount === '') return 'N/A';
    const num = typeof amount === 'number' ? amount : parseFloat(amount);
    if (isNaN(num)) return 'N/A';
    return `$${num.toLocaleString()}`;
  };

  const formatCentsToDollars = (cents?: number | null) =>
    cents !== undefined && cents !== null
      ? `$${(cents / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : 'N/A';

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

  // Helper for party badge
  const getPartyBadge = (party: string | null | undefined) => {
    if (!party) return <span className="inline-block px-2 py-1 text-xs rounded bg-gray-400 text-white font-semibold" aria-label="Unknown party">Unknown</span>;
    switch (party.toLowerCase()) {
      case 'democratic':
      case 'd':
        return <span className="inline-block px-2 py-1 text-xs rounded bg-blue-600 text-white font-semibold" aria-label="Democratic">Democratic</span>;
      case 'republican':
      case 'r':
        return <span className="inline-block px-2 py-1 text-xs rounded bg-red-600 text-white font-semibold" aria-label="Republican">Republican</span>;
      case 'independent':
      case 'i':
        return <span className="inline-block px-2 py-1 text-xs rounded bg-gray-700 text-white font-semibold" aria-label="Independent">Independent</span>;
      default:
        return <span className="inline-block px-2 py-1 text-xs rounded bg-gray-500 text-white font-semibold" aria-label={party}>{party}</span>;
    }
  };

  // Helper for chamber badge
  const getChamberBadge = (chamber: string | null | undefined) => {
    if (!chamber) return <span className="inline-block px-2 py-1 text-xs rounded bg-gray-400 text-white font-semibold" aria-label="Unknown chamber">Unknown</span>;
    switch (chamber.toLowerCase()) {
      case 'senate':
        return <span className="inline-block px-2 py-1 text-xs rounded bg-purple-700 text-white font-semibold" aria-label="Senate">Senate</span>;
      case 'house':
        return <span className="inline-block px-2 py-1 text-xs rounded bg-green-700 text-white font-semibold" aria-label="House">House</span>;
      default:
        return <span className="inline-block px-2 py-1 text-xs rounded bg-gray-500 text-white font-semibold" aria-label={chamber}>{chamber}</span>;
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

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? 'N/A' : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  };

  // Helper to ensure a string is always passed
  const safeString = (val: string | null | undefined) => (typeof val === 'string' ? val : '');

  return (
    <div className="space-y-6">
      {/* Header with search and filters */}
      <div className="card p-6">
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">Congressional Trades</h2>
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
                  value={filters.transaction_types || ''}
                  onChange={(e) => handleFilterChange('transaction_types', e.target.value as any)}
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
                  value={filters.parties || ''}
                  onChange={(e) => handleFilterChange('parties', e.target.value as any)}
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
                  value={filters.chambers || ''}
                  onChange={(e) => handleFilterChange('chambers', e.target.value as any)}
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
                  value={filters.owners || ''}
                  onChange={(e) => handleFilterChange('owners', e.target.value as any)}
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
                  value={filters.transaction_date_from || ''}
                  onChange={(e) => handleFilterChange('transaction_date_from', e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Date To
                </label>
                <input
                  type="date"
                  value={filters.transaction_date_to || ''}
                  onChange={(e) => handleFilterChange('transaction_date_to', e.target.value)}
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
                  value={filters.tickers?.[0] || ''}
                  onChange={(e) => handleFilterChange('tickers', e.target.value ? e.target.value : undefined)}
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
                  {tradeItems.map((trade: CongressionalTrade) => {
                    const { icon: TypeIcon, color } = getTransactionTypeStyle(trade.transaction_type);
                    
                    return (
                      <tr key={trade.id} className="hover:bg-gray-50 dark:hover:bg-gray-900">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex flex-col">
                            <span className="font-semibold text-gray-900 dark:text-white" aria-label="Member name">
                              {trade.member_name || 'Unknown'}
                            </span>
                            <div className="flex gap-2 mt-1">
                              {getPartyBadge(trade.member_party)}
                              {getChamberBadge(trade.member_chamber)}
                              {(() => { const memberState = trade.member_state ? trade.member_state : ''; return memberState && (
                                <span className="inline-block px-2 py-1 text-xs rounded bg-gray-700 text-white font-semibold" aria-label={memberState || ''}>{memberState}</span>
                              ); })()}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900 dark:text-white font-semibold" aria-label="Ticker">
                            {trade.ticker ? (
                              <span className="font-mono font-semibold">{trade.ticker}</span>
                            ) : (
                              <span className="text-gray-400 dark:text-gray-500">No ticker</span>
                            )}
                          </div>
                          <div className="text-sm text-gray-700 dark:text-gray-300 max-w-xs truncate" aria-label="Asset name">
                            {trade.asset_name}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className={`flex items-center ${color}`}> {/* color is still used for icon */}
                            <TypeIcon className="h-4 w-4 mr-1" />
                            <span className="capitalize text-sm font-semibold text-gray-900 dark:text-white" aria-label="Transaction type">{trade.transaction_type}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white font-semibold" aria-label="Amount">
                          {trade.amount_exact !== undefined && trade.amount_exact !== null
                            ? formatCentsToDollars(trade.amount_exact)
                            : `${formatCentsToDollars(trade.amount_min)} - ${formatCentsToDollars(trade.amount_max)}`}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white" aria-label="Date">
                          {formatDate(safeString(trade.transaction_date))}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white" aria-label="Owner">
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