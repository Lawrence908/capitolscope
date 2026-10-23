import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { MagnifyingGlassIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline';
import type { CongressionalTrade, TradeFilters, PaginatedResponse } from '../types/index';
import apiClient from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { PageHeader, Spinner } from './ui';
import DisclosureRow from './trades/DisclosureRow';
import { BULLETIN_INPUT, BULLETIN_LABEL, groupByDate, isFutureDated, longDate, weekday } from './trades/feed';

const PAGE_SIZE = 50;

type SortKey = 'filed' | 'traded' | 'traded_asc' | 'amount';

const SORTS: Record<SortKey, { label: string; sort_by: NonNullable<TradeFilters['sort_by']>; sort_order: 'asc' | 'desc' }> = {
  filed: { label: 'Newest filings', sort_by: 'notification_date', sort_order: 'desc' },
  traded: { label: 'Newest trades', sort_by: 'transaction_date', sort_order: 'desc' },
  traded_asc: { label: 'Oldest trades', sort_by: 'transaction_date', sort_order: 'asc' },
  amount: { label: 'Largest amount', sort_by: 'amount', sort_order: 'desc' },
};

const DEFAULT_FILTERS: TradeFilters = { sort_by: 'notification_date', sort_order: 'desc' };

const AMOUNT_RANGES = [
  { label: '$1K to $15K', value: '1001-15000' },
  { label: '$15K to $50K', value: '15001-50000' },
  { label: '$50K to $100K', value: '50001-100000' },
  { label: '$100K to $250K', value: '100001-250000' },
  { label: '$250K to $500K', value: '250001-500000' },
  { label: '$500K to $1M', value: '500001-1000000' },
  { label: '$1M+', value: '1000001-10000000' },
];

const PRO_TIERS = ['PRO', 'PREMIUM', 'ENTERPRISE'];

const sortKeyOf = (f: TradeFilters): SortKey =>
  (Object.keys(SORTS) as SortKey[]).find((k) => SORTS[k].sort_by === f.sort_by && SORTS[k].sort_order === f.sort_order) ||
  'filed';

const TradeBrowser: React.FC = () => {
  const { user } = useAuth();
  const [trades, setTrades] = useState<PaginatedResponse<CongressionalTrade> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<TradeFilters>(DEFAULT_FILTERS);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [exporting, setExporting] = useState(false);

  const fetchTrades = useCallback(
    async (page: number = 1) => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.getTrades(filters, page, PAGE_SIZE);
        setTrades(response);
        setCurrentPage(page);
      } catch (err) {
        setError('Trades could not be loaded. Try again in a moment.');
        console.error('Error fetching trades:', err);
      } finally {
        setLoading(false);
      }
    },
    [filters],
  );

  useEffect(() => {
    fetchTrades(1);
  }, [fetchTrades]);

  const handleFilterChange = (key: keyof TradeFilters, value: string | number | undefined) => {
    setFilters((prev: TradeFilters) => ({
      ...prev,
      [key]:
        value === '' || value === undefined
          ? undefined
          : // List filters are sent as arrays for the backend.
            key === 'parties' || key === 'chambers' || key === 'transaction_types' || key === 'owners' || key === 'tickers'
            ? [key === 'tickers' ? String(value).trim().toUpperCase() : value]
            : value,
    }));
  };

  const handleSort = (key: SortKey) =>
    setFilters((prev) => ({ ...prev, sort_by: SORTS[key].sort_by, sort_order: SORTS[key].sort_order }));

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setFilters((prev: TradeFilters) => ({ ...prev, search: searchQuery.trim() || undefined }));
  };

  const clearFilters = () => {
    setFilters((prev) => ({ sort_by: prev.sort_by, sort_order: prev.sort_order }));
    setSearchQuery('');
  };

  const canExport = !!user && PRO_TIERS.includes((user.subscription_tier || '').toUpperCase());
  const handleExport = async () => {
    try {
      setExporting(true);
      const blob = await apiClient.exportTradesCsv({ ticker: filters.tickers?.[0] });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `capitolscope-trades${filters.tickers?.[0] ? `-${filters.tickers[0]}` : ''}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('CSV export failed:', err);
      setError('The CSV export failed. Try again in a moment.');
    } finally {
      setExporting(false);
    }
  };

  if (loading && !trades) {
    return <Spinner label="Loading trades" />;
  }

  const items = (trades?.items ?? []).filter((t) => !isFutureDated(t));
  const sortKey = sortKeyOf(filters);
  const groupField =
    filters.sort_by === 'notification_date' ? 'notification_date' : filters.sort_by === 'transaction_date' ? 'transaction_date' : null;
  const groups = groupField ? groupByDate(items, groupField) : [{ date: '', items }];
  const buys = items.filter((t) => (t.transaction_type || '').startsWith('P')).length;
  const sells = items.filter((t) => (t.transaction_type || '').startsWith('S')).length;
  const members = new Set(items.map((t) => t.member_id || t.member_name)).size;
  const activeFilterCount = [
    filters.transaction_types,
    filters.parties,
    filters.chambers,
    filters.transaction_date_from,
    filters.transaction_date_to,
    filters.tickers,
    filters.amount_range,
    filters.search,
  ].filter((v) => (Array.isArray(v) ? v.length > 0 : !!v)).length;

  const select = (
    label: string,
    key: keyof TradeFilters,
    value: string,
    options: { value: string; label: string }[],
  ) => (
    <div>
      <label className={BULLETIN_LABEL} htmlFor={`tb-${key}`}>
        {label}
      </label>
      <select
        id={`tb-${key}`}
        value={value}
        onChange={(e) => handleFilterChange(key, e.target.value)}
        className={BULLETIN_INPUT}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );

  return (
    <div>
      <PageHeader
        eyebrow="Disclosures"
        title="All trades"
        subtitle="Every periodic transaction report filed by members of Congress under the STOCK Act. Amounts are the ranges members disclose, not exact values."
        stats={trades?.total ? [{ label: 'Trades', value: trades.total.toLocaleString() }] : undefined}
      />

      {/* Search, sort and filters */}
      <section>
        <form onSubmit={handleSearch} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="min-w-0 flex-1">
            <label className={BULLETIN_LABEL} htmlFor="tb-search">
              Search
            </label>
            <div className="relative">
              <MagnifyingGlassIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-content-faint" />
              <input
                id="tb-search"
                type="search"
                placeholder="Member, ticker or asset"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={`${BULLETIN_INPUT} pl-9`}
              />
            </div>
          </div>
          <div className="sm:w-48">
            <label className={BULLETIN_LABEL} htmlFor="tb-sort">
              Sort
            </label>
            <select
              id="tb-sort"
              value={sortKey}
              onChange={(e) => handleSort(e.target.value as SortKey)}
              className={BULLETIN_INPUT}
            >
              {(Object.keys(SORTS) as SortKey[]).map((k) => (
                <option key={k} value={k}>
                  {SORTS[k].label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary text-sm">
              Search
            </button>
            <button
              type="button"
              onClick={() => setShowFilters((s) => !s)}
              aria-expanded={showFilters}
              className="btn-secondary text-sm"
            >
              Filters{activeFilterCount ? ` (${activeFilterCount})` : ''}
            </button>
            {canExport ? (
              <button type="button" onClick={handleExport} disabled={exporting} className="btn-secondary flex items-center gap-1.5 text-sm disabled:opacity-50">
                <ArrowDownTrayIcon className="h-4 w-4" />
                {exporting ? 'Exporting' : 'CSV'}
              </button>
            ) : (
              <Link to="/premium" className="btn-outline flex items-center gap-1.5 text-sm" title="CSV export is part of Pro">
                <ArrowDownTrayIcon className="h-4 w-4" />
                CSV
              </Link>
            )}
          </div>
        </form>

        {/* Amount quick filters */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="font-ui text-[11px] font-semibold uppercase tracking-[0.08em] text-content-faint">Amount</span>
          {AMOUNT_RANGES.map((r) => {
            const active = filters.amount_range === r.value;
            return (
              <button
                key={r.value}
                type="button"
                aria-pressed={active}
                onClick={() => handleFilterChange('amount_range', active ? undefined : r.value)}
                className={`border-2 px-2 py-0.5 font-ui text-xs font-semibold transition-colors ${
                  active ? 'border-content bg-content text-surface' : 'border-line text-content-muted hover:border-content hover:text-content'
                }`}
              >
                {r.label}
              </button>
            );
          })}
        </div>

        {showFilters && (
          <div className="mt-4 grid grid-cols-1 gap-4 border-t border-line pt-4 sm:grid-cols-2 lg:grid-cols-4">
            {select('Transaction', 'transaction_types', filters.transaction_types?.[0] || '', [
              { value: '', label: 'All' },
              { value: 'P', label: 'Bought' },
              { value: 'S', label: 'Sold' },
              { value: 'E', label: 'Exchanged' },
            ])}
            {select('Party', 'parties', filters.parties?.[0] || '', [
              { value: '', label: 'All' },
              { value: 'D', label: 'Democrat' },
              { value: 'R', label: 'Republican' },
              { value: 'I', label: 'Independent' },
            ])}
            {select('Chamber', 'chambers', filters.chambers?.[0] || '', [
              { value: '', label: 'Both' },
              { value: 'House', label: 'House' },
              { value: 'Senate', label: 'Senate' },
            ])}
            {select('Amount', 'amount_range', filters.amount_range || '', [
              { value: '', label: 'Any amount' },
              { value: '1-1000', label: '$1 to $1,000' },
              ...AMOUNT_RANGES,
            ])}
            <div>
              <label className={BULLETIN_LABEL} htmlFor="tb-ticker">
                Ticker
              </label>
              <input
                id="tb-ticker"
                type="text"
                placeholder="e.g. NVDA"
                value={filters.tickers?.[0] || ''}
                onChange={(e) => handleFilterChange('tickers', e.target.value)}
                className={`${BULLETIN_INPUT} uppercase`}
              />
            </div>
            <div>
              <label className={BULLETIN_LABEL} htmlFor="tb-from">
                Traded from
              </label>
              <input
                id="tb-from"
                type="date"
                value={filters.transaction_date_from || ''}
                onChange={(e) => handleFilterChange('transaction_date_from', e.target.value)}
                className={BULLETIN_INPUT}
              />
            </div>
            <div>
              <label className={BULLETIN_LABEL} htmlFor="tb-to">
                Traded to
              </label>
              <input
                id="tb-to"
                type="date"
                value={filters.transaction_date_to || ''}
                onChange={(e) => handleFilterChange('transaction_date_to', e.target.value)}
                className={BULLETIN_INPUT}
              />
            </div>
            <div className="flex items-end">
              <button type="button" onClick={clearFilters} className="btn-secondary w-full text-sm">
                Clear filters
              </button>
            </div>
          </div>
        )}
      </section>

      {error && (
        <div role="alert" className="mt-4 border-l-4 border-accent bg-surface-inset px-4 py-3 font-ui text-sm text-content">
          {error}
        </div>
      )}

      {trades && (
        <section className="mt-6 section-rule">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-line py-2 font-ui text-xs text-content-faint">
            <span>
              {items.length > 0 ? (
                <>
                  This page: {buys} bought, {sells} sold, {members} member{members === 1 ? '' : 's'}
                </>
              ) : null}
            </span>
            {loading && <span className="font-semibold text-accent">Updating</span>}
          </div>

          {items.length === 0 ? (
            <div className="py-12 text-center">
              <p className="font-display text-2xl font-extrabold text-content">No trades match</p>
              <p className="mt-1 font-ui text-sm text-content-faint">Try fewer filters or a wider date range.</p>
            </div>
          ) : (
            groups.map((g, gi) => (
              <div key={`${g.date}-${gi}`}>
                {groupField && (
                  <h2 className="flex items-baseline gap-3 border-b border-line pb-1.5 pt-4 font-ui text-sm font-bold text-content">
                    {groupField === 'notification_date' ? 'Filed' : 'Traded'} {weekday(g.date)}, {longDate(g.date) || 'date unknown'}
                    <span className="font-normal text-content-faint">
                      {g.items.length} trade{g.items.length === 1 ? '' : 's'}
                    </span>
                  </h2>
                )}
                {g.items.map((t) => (
                  <DisclosureRow key={t.id} trade={t} />
                ))}
              </div>
            ))
          )}

          {trades.pages > 1 && (
            <nav className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t-[3px] border-content pt-3" aria-label="Pagination">
              <p className="font-ui text-sm text-content-muted">
                <span className="tabular-nums text-content">{((currentPage - 1) * PAGE_SIZE + 1).toLocaleString()}</span> to{' '}
                <span className="tabular-nums text-content">{Math.min(currentPage * PAGE_SIZE, trades.total).toLocaleString()}</span> of{' '}
                <span className="tabular-nums text-content">{trades.total.toLocaleString()}</span>
              </p>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => fetchTrades(currentPage - 1)}
                  disabled={!trades.has_prev || loading}
                  className="btn-secondary text-sm disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Previous
                </button>
                <span className="font-ui text-xs font-semibold uppercase tracking-[0.08em] text-content-faint">
                  Page {currentPage} of {trades.pages.toLocaleString()}
                </span>
                <button
                  type="button"
                  onClick={() => fetchTrades(currentPage + 1)}
                  disabled={!trades.has_next || loading}
                  className="btn-secondary text-sm disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </nav>
          )}
        </section>
      )}
    </div>
  );
};

export default TradeBrowser;
