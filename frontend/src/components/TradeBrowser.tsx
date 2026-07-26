import React, { useState, useEffect, useCallback } from 'react';

import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  ArrowsRightLeftIcon,
  ArrowDownTrayIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import type { CongressionalTrade, TradeFilters, PaginatedResponse } from '../types/index';
import apiClient from '../services/api';
import { PageHeader, Spinner, PartyTag, fmtMoney } from './ui';

const Pill: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span className="rounded-sm bg-surface-inset px-1.5 py-0.5 font-data text-[10px] uppercase tracking-[0.1em] text-content-muted">
    {children}
  </span>
);

// cents → compact money; blank for missing/zero
const money = (cents?: number | null): string =>
  cents === undefined || cents === null || cents === 0 ? '—' : fmtMoney(cents / 100);

const TradeBrowser: React.FC = () => {
  const [trades, setTrades] = useState<PaginatedResponse<CongressionalTrade> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<TradeFilters>({});
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filterLoading, setFilterLoading] = useState(false);

  // Fetch trades with current filters and pagination
  const fetchTrades = useCallback(
    async (page: number = 1) => {
      try {
        setLoading(true);
        setFilterLoading(true);
        setError(null);

        const response = await apiClient.getTrades(filters, page, 50);
        setTrades(response);
        setCurrentPage(page);
      } catch (err) {
        setError('Failed to fetch trades. Please try again.');
        console.error('Error fetching trades:', err);
      } finally {
        setLoading(false);
        setFilterLoading(false);
      }
    },
    [filters],
  );

  // Initial load
  useEffect(() => {
    fetchTrades(1);
  }, [fetchTrades]);

  // Handle filter changes
  const handleFilterChange = (key: keyof TradeFilters, value: string | number | undefined) => {
    setFilters((prev: TradeFilters) => ({
      ...prev,
      [key]:
        value === ''
          ? undefined
          : // Convert single values to arrays for backend compatibility
            key === 'parties' || key === 'chambers' || key === 'transaction_types' || key === 'owners' || key === 'tickers'
            ? value
              ? [value]
              : undefined
            : value,
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

  // Transaction direction → icon + token color (buy verdigris, sell oxblood, exchange brass)
  const getTransactionTypeStyle = (type: string) => {
    switch (type) {
      case 'P':
        return { icon: ArrowUpIcon, color: 'text-accent' };
      case 'S':
        return { icon: ArrowDownIcon, color: 'text-sev-flag' };
      case 'E':
        return { icon: ArrowsRightLeftIcon, color: 'text-sev-watch' };
      default:
        return { icon: ExclamationTriangleIcon, color: 'text-content-faint' };
    }
  };

  const typeLabel = (t?: string | null) =>
    t === 'P' ? 'Purchase' : t === 'S' ? 'Sale' : t === 'E' ? 'Exchange' : t || 'Unknown';

  const ownerLabel = (o?: string | null) =>
    o === 'SP' ? 'Spouse' : o === 'JT' ? 'Joint' : o === 'DC' ? 'Child' : 'Self';

  const MajorTag = () => (
    <span className="ml-1 rounded-sm border border-sev-watch/40 bg-sev-watch/15 px-1.5 py-0.5 font-data text-[10px] uppercase tracking-[0.08em] text-sev-watch">
      Major
    </span>
  );

  // Patch: Ensure trades.items is always an array
  const tradeItems = trades?.items ?? [];

  if (loading && !trades) {
    return <Spinner label="Loading trades" />;
  }

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    return isNaN(date.getTime())
      ? '—'
      : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const safeString = (val: string | null | undefined) => (typeof val === 'string' ? val : '');

  const AmountCell: React.FC<{ trade: CongressionalTrade }> = ({ trade }) => {
    if (trade.amount_exact !== undefined && trade.amount_exact !== null) {
      return (
        <span className="flex items-center">
          {money(trade.amount_exact)}
          {trade.amount_exact >= 1000000 && <MajorTag />}
        </span>
      );
    }
    if (
      trade.amount_min !== undefined &&
      trade.amount_min !== null &&
      trade.amount_max !== undefined &&
      trade.amount_max !== null
    ) {
      return (
        <span className="flex items-center">
          {money(trade.amount_min)} – {money(trade.amount_max)}
          {trade.amount_max >= 1000000 && <MajorTag />}
        </span>
      );
    }
    return <span>—</span>;
  };

  const quickFilters = [
    { label: '$1K–$15K', value: '1001-15000' },
    { label: '$15K–$50K', value: '15001-50000' },
    { label: '$50K–$100K', value: '50001-100000' },
    { label: '$100K–$250K', value: '100001-250000' },
    { label: '$250K–$500K', value: '250001-500000' },
    { label: '$500K–$1M', value: '500001-1000000' },
    { label: '$1M+', value: '1000001-10000000' },
  ];

  return (
    <div>
      <PageHeader
        eyebrow="CapitolScope · Disclosures"
        title="Trade Browser"
        subtitle="Every disclosed congressional transaction — search and filter by member, ticker, party, chamber, amount, and date across public STOCK Act filings."
        stats={trades?.total ? [{ label: 'Total trades', value: trades.total.toLocaleString() }] : undefined}
      />

      {/* Search + filters */}
      <div className="card p-4 lg:p-6">
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          {trades && trades.total > 0 && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-data text-[11px] uppercase tracking-[0.08em] text-content-faint">
              <span className="text-accent">{trades.items.filter((t) => t.transaction_type === 'P').length} buys</span>
              <span className="text-sev-flag">{trades.items.filter((t) => t.transaction_type === 'S').length} sells</span>
              <span>{trades.items.filter((t) => t.amount_exact && t.amount_exact >= 1000000).length} major</span>
              <span>{new Set(trades.items.map((t) => t.member_name)).size} members</span>
              {filterLoading && (
                <span className="flex items-center text-accent">
                  <span className="mr-1 h-3 w-3 animate-spin rounded-full border-b border-current" />
                  Updating…
                </span>
              )}
            </div>
          )}

          <div className="flex w-full gap-2 sm:w-auto">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="btn-secondary flex flex-1 items-center gap-2 text-sm sm:flex-none"
            >
              <FunnelIcon className="h-4 w-4" />
              <span className="hidden sm:inline">Filters</span>
            </button>
            <button
              onClick={() => alert('Export functionality coming soon!')}
              className="btn-secondary flex flex-1 items-center gap-2 text-sm sm:flex-none"
            >
              <ArrowDownTrayIcon className="h-4 w-4" />
              <span className="hidden sm:inline">Export</span>
            </button>
          </div>
        </div>

        {/* Search bar */}
        <form onSubmit={handleSearch} className="mt-4">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-content-faint" />
            <input
              type="text"
              placeholder="Search by member name, ticker, or asset description…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field pl-10"
            />
          </div>
        </form>

        {/* Quick Amount Filters */}
        <div className="mt-4">
          <span className="mr-2 font-data text-[11px] uppercase tracking-[0.12em] text-content-faint">Quick filters</span>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {quickFilters.map((filter) => {
              const active = filters.amount_range === filter.value;
              return (
                <button
                  key={filter.value}
                  onClick={() => handleFilterChange('amount_range', filter.value)}
                  className={`rounded-full border px-3 py-1 font-data text-[11px] transition-colors ${
                    active
                      ? 'border-accent bg-accent text-[#071310]'
                      : 'border-line bg-surface-inset text-content-muted hover:border-accent'
                  }`}
                >
                  {filter.label}
                </button>
              );
            })}
            {filters.amount_range && (
              <button
                onClick={() => handleFilterChange('amount_range', undefined)}
                className="px-2 py-1 font-data text-[11px] text-content-faint hover:text-content"
              >
                ✕ Clear
              </button>
            )}
          </div>
        </div>

        {/* Filters panel */}
        {showFilters && (
          <div className="mt-4 rounded-md border border-line bg-surface-inset p-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                {
                  label: 'Transaction Type',
                  el: (
                    <select
                      value={filters.transaction_types || ''}
                      onChange={(e) => handleFilterChange('transaction_types', e.target.value)}
                      className="input-field"
                    >
                      <option value="">All Types</option>
                      <option value="P">Purchase</option>
                      <option value="S">Sale</option>
                      <option value="E">Exchange</option>
                    </select>
                  ),
                },
                {
                  label: 'Party',
                  el: (
                    <select
                      value={filters.parties || ''}
                      onChange={(e) => handleFilterChange('parties', e.target.value)}
                      className="input-field"
                    >
                      <option value="">All Parties</option>
                      <option value="R">Republican</option>
                      <option value="D">Democratic</option>
                      <option value="I">Independent</option>
                    </select>
                  ),
                },
                {
                  label: 'Chamber',
                  el: (
                    <select
                      value={filters.chambers || ''}
                      onChange={(e) => handleFilterChange('chambers', e.target.value)}
                      className="input-field"
                    >
                      <option value="">All Chambers</option>
                      <option value="House">House</option>
                      <option value="Senate">Senate</option>
                    </select>
                  ),
                },
                {
                  label: 'Date From',
                  el: (
                    <input
                      type="date"
                      value={filters.transaction_date_from || ''}
                      onChange={(e) => handleFilterChange('transaction_date_from', e.target.value)}
                      className="input-field"
                    />
                  ),
                },
                {
                  label: 'Date To',
                  el: (
                    <input
                      type="date"
                      value={filters.transaction_date_to || ''}
                      onChange={(e) => handleFilterChange('transaction_date_to', e.target.value)}
                      className="input-field"
                    />
                  ),
                },
                {
                  label: 'Ticker',
                  el: (
                    <input
                      type="text"
                      placeholder="e.g., AAPL, MSFT"
                      value={filters.tickers?.[0] || ''}
                      onChange={(e) => handleFilterChange('tickers', e.target.value ? e.target.value : undefined)}
                      className="input-field"
                    />
                  ),
                },
                {
                  label: 'Amount Range',
                  el: (
                    <select
                      value={filters.amount_range || ''}
                      onChange={(e) => handleFilterChange('amount_range', e.target.value)}
                      className="input-field"
                    >
                      <option value="">All Amounts</option>
                      <option value="1-1000">$1 – $1,000</option>
                      <option value="1001-15000">$1,001 – $15,000</option>
                      <option value="15001-50000">$15,001 – $50,000</option>
                      <option value="50001-100000">$50,001 – $100,000</option>
                      <option value="100001-250000">$100,001 – $250,000</option>
                      <option value="250001-500000">$250,001 – $500,000</option>
                      <option value="500001-1000000">$500,001 – $1,000,000</option>
                      <option value="1000001-10000000">$1,000,001+</option>
                    </select>
                  ),
                },
              ].map((f) => (
                <div key={f.label}>
                  <label className="mb-1 block font-data text-[11px] uppercase tracking-[0.12em] text-content-faint">
                    {f.label}
                  </label>
                  {f.el}
                </div>
              ))}
              <div className="flex items-end">
                <button type="button" onClick={clearFilters} className="btn-secondary w-full text-sm">
                  Clear Filters
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="mt-4 flex items-center gap-3 rounded-md border border-sev-flag/40 px-4 py-3 status-error">
          <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" />
          <p className="font-ui text-sm">{error}</p>
        </div>
      )}

      {/* Trades table */}
      {trades && (
        <div className="card mt-6 overflow-hidden">
          {tradeItems.length === 0 ? (
            <div className="p-10 text-center">
              <p className="mb-2 font-display text-lg text-content">No trades found</p>
              <p className="font-ui text-sm text-content-faint">Try adjusting your filters or check back later.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              {/* Desktop table */}
              <table className="hidden min-w-full lg:table">
                <thead className="bg-surface-inset">
                  <tr>
                    {['Member', 'Asset', 'Type', 'Amount', 'Date', 'Owner'].map((h) => (
                      <th
                        key={h}
                        className="px-6 py-3 text-left font-data text-[11px] uppercase tracking-[0.12em] text-content-faint"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {tradeItems.map((trade: CongressionalTrade) => {
                    const { icon: TypeIcon, color } = getTransactionTypeStyle(trade.transaction_type || '');
                    return (
                      <tr key={trade.id} className="transition-colors hover:bg-surface-inset">
                        <td className="whitespace-nowrap px-6 py-4">
                          <div className="flex flex-col">
                            <span className="font-ui font-medium text-content">{trade.member_name || 'Unknown'}</span>
                            <div className="mt-1 flex items-center gap-1.5">
                              <PartyTag party={trade.member_party} />
                              {trade.member_chamber && <Pill>{trade.member_chamber}</Pill>}
                              {trade.member_state && <Pill>{trade.member_state}</Pill>}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="font-data text-sm font-medium text-content">
                            {trade.ticker ? trade.ticker : <span className="text-content-faint">No ticker</span>}
                          </div>
                          <div className="max-w-xs truncate font-ui text-sm text-content-faint">{trade.asset_name}</div>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <div className={`flex items-center ${color}`}>
                            <TypeIcon className="mr-1 h-4 w-4" />
                            <span className="font-ui text-sm font-medium">{typeLabel(trade.transaction_type)}</span>
                          </div>
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 font-data text-sm tabular-nums text-content">
                          <AmountCell trade={trade} />
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 font-data text-sm tabular-nums text-content-muted">
                          {formatDate(safeString(trade.transaction_date))}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 font-ui text-sm text-content-muted">
                          {ownerLabel(trade.owner)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {/* Mobile card layout */}
              <div className="space-y-4 p-4 lg:hidden">
                {tradeItems.map((trade: CongressionalTrade) => {
                  const { icon: TypeIcon, color } = getTransactionTypeStyle(trade.transaction_type || '');
                  return (
                    <div key={trade.id} className="rounded-md border border-line bg-surface-inset p-4">
                      <div className="mb-3 flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-ui text-sm font-medium text-content">{trade.member_name || 'Unknown'}</h3>
                          <div className="mt-1 flex flex-wrap items-center gap-1.5">
                            <PartyTag party={trade.member_party} />
                            {trade.member_chamber && <Pill>{trade.member_chamber}</Pill>}
                            {trade.member_state && <Pill>{trade.member_state}</Pill>}
                          </div>
                        </div>
                        <div className={`ml-2 flex items-center ${color}`}>
                          <TypeIcon className="mr-1 h-4 w-4" />
                          <span className="font-ui text-xs font-medium">{typeLabel(trade.transaction_type)}</span>
                        </div>
                      </div>

                      <div className="space-y-2 font-ui text-sm">
                        <div className="flex justify-between gap-3">
                          <span className="text-content-faint">Asset</span>
                          <div className="text-right">
                            <div className="font-data font-medium text-content">
                              {trade.ticker ? trade.ticker : <span className="text-content-faint">No ticker</span>}
                            </div>
                            {trade.asset_name && (
                              <div className="max-w-40 truncate font-ui text-xs text-content-faint">{trade.asset_name}</div>
                            )}
                          </div>
                        </div>
                        <div className="flex justify-between gap-3">
                          <span className="text-content-faint">Amount</span>
                          <span className="font-data tabular-nums text-content">
                            <AmountCell trade={trade} />
                          </span>
                        </div>
                        <div className="flex justify-between gap-3">
                          <span className="text-content-faint">Date</span>
                          <span className="font-data tabular-nums text-content-muted">
                            {formatDate(safeString(trade.transaction_date))}
                          </span>
                        </div>
                        <div className="flex justify-between gap-3">
                          <span className="text-content-faint">Owner</span>
                          <span className="text-content-muted">{ownerLabel(trade.owner)}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Pagination */}
          {trades.pages > 1 && (
            <div className="flex items-center justify-between border-t border-line bg-surface-inset px-4 py-3 sm:px-6">
              <div className="flex flex-1 justify-between sm:hidden">
                <button
                  onClick={() => fetchTrades(currentPage - 1)}
                  disabled={!trades.has_prev}
                  className="btn-secondary text-sm disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => fetchTrades(currentPage + 1)}
                  disabled={!trades.has_next}
                  className="btn-secondary text-sm disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                <p className="font-ui text-sm text-content-muted">
                  Showing <span className="font-data tabular-nums text-content">{(currentPage - 1) * 50 + 1}</span> to{' '}
                  <span className="font-data tabular-nums text-content">{Math.min(currentPage * 50, trades.total)}</span> of{' '}
                  <span className="font-data tabular-nums text-content">{trades.total}</span> results
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => fetchTrades(currentPage - 1)}
                    disabled={!trades.has_prev}
                    className="btn-outline text-sm disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="font-data text-xs uppercase tracking-[0.1em] text-content-faint">
                    Page {currentPage} of {trades.pages}
                  </span>
                  <button
                    onClick={() => fetchTrades(currentPage + 1)}
                    disabled={!trades.has_next}
                    className="btn-outline text-sm disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Next
                  </button>
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
