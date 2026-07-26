import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import type { CongressMember, MemberFilters, PaginatedResponse } from '../types';
import apiClient from '../services/api';
import { PageHeader, Spinner, PartyTag, fmtMoney } from './ui';

const ChamberTag: React.FC<{ chamber: string | null | undefined }> = ({ chamber }) => (
  <span className="rounded-sm bg-surface-inset px-1.5 py-0.5 font-data text-[10px] uppercase tracking-[0.1em] text-content-muted">
    {chamber || 'Unknown'}
  </span>
);

const MembersBrowser: React.FC = () => {
  const [members, setMembers] = useState<PaginatedResponse<CongressMember> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<MemberFilters>({});
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchMembers = useCallback(
    async (page: number = 1) => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.getMembers({ ...filters }, page, 20);
        setMembers(response);
        setCurrentPage(page);
      } catch {
        setError('Failed to fetch members. Please try again.');
      } finally {
        setLoading(false);
      }
    },
    [filters],
  );

  useEffect(() => {
    fetchMembers(1);
  }, [fetchMembers]);

  const handleFilterChange = (key: keyof MemberFilters, value: string | undefined) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value === '' ? undefined : value,
    }));
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setFilters((prev) => ({
      ...prev,
      search: searchQuery || undefined,
    }));
  };

  const clearFilters = () => {
    setFilters({});
    setSearchQuery('');
  };

  if (loading && !members) {
    return <Spinner label="Loading members" />;
  }

  return (
    <div>
      <PageHeader
        eyebrow="CapitolScope · Members"
        title="Congress Members"
        subtitle="Every member with disclosed STOCK Act activity — filter by party, chamber, or state, and open a member for their full trading profile."
        stats={
          members?.total
            ? [{ label: 'Total members', value: members.total.toLocaleString() }]
            : undefined
        }
      />

      {/* Search + filters */}
      <div className="card p-4 lg:p-6">
        <form onSubmit={handleSearch}>
          <input
            type="text"
            placeholder="Search by name, state, or party…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field"
          />
        </form>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-1 block font-data text-[11px] uppercase tracking-[0.12em] text-content-faint">
              Party
            </label>
            <select
              value={filters.party || ''}
              onChange={(e) => handleFilterChange('party', e.target.value)}
              className="input-field"
            >
              <option value="">All Parties</option>
              <option value="Democratic">Democratic</option>
              <option value="Republican">Republican</option>
              <option value="Independent">Independent</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block font-data text-[11px] uppercase tracking-[0.12em] text-content-faint">
              State
            </label>
            <input
              type="text"
              placeholder="e.g., CA, NY"
              value={filters.state || ''}
              onChange={(e) => handleFilterChange('state', e.target.value.toUpperCase())}
              className="input-field"
              maxLength={2}
            />
          </div>
          <div>
            <label className="mb-1 block font-data text-[11px] uppercase tracking-[0.12em] text-content-faint">
              Chamber
            </label>
            <select
              value={filters.chamber || ''}
              onChange={(e) => handleFilterChange('chamber', e.target.value as MemberFilters['chamber'])}
              className="input-field"
            >
              <option value="">All Chambers</option>
              <option value="House">House</option>
              <option value="Senate">Senate</option>
            </select>
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <button onClick={clearFilters} className="btn-secondary text-sm">
            Clear Filters
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-md border border-sev-flag/40 px-4 py-3 font-ui text-sm status-error">
          {error}
        </div>
      )}

      {/* Members table */}
      {members && (
        <div className="card mt-6 overflow-hidden">
          {members.items.length === 0 ? (
            <div className="p-10 text-center">
              <p className="mb-2 font-display text-lg text-content">No members found</p>
              <p className="font-ui text-sm text-content-faint">Try adjusting your filters or check back later.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              {/* Desktop table */}
              <table className="hidden min-w-full lg:table">
                <thead className="bg-surface-inset">
                  <tr>
                    {['Name', 'Party', 'State', 'Chamber', 'Total Trades', 'Total $ Volume', ''].map((h, i) => (
                      <th
                        key={i}
                        className="px-6 py-3 text-left font-data text-[11px] uppercase tracking-[0.12em] text-content-faint"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {members.items.map((member) => (
                    <tr key={member.id} className="transition-colors hover:bg-surface-inset">
                      <td className="whitespace-nowrap px-6 py-4">
                        <Link
                          to={`/members/${member.id}`}
                          className="font-ui font-medium text-content transition-colors hover:text-accent hover:underline"
                        >
                          {member.full_name}
                        </Link>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4">
                        <PartyTag party={member.party} />
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 font-data text-sm text-content-muted">{member.state}</td>
                      <td className="whitespace-nowrap px-6 py-4">
                        <ChamberTag chamber={member.chamber} />
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 font-data text-sm tabular-nums text-content">
                        {member.trade_count?.toLocaleString() ?? '—'}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 font-data text-sm tabular-nums text-content">
                        {member.total_trade_value ? fmtMoney(member.total_trade_value / 100) : '—'}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-right">
                        <Link to={`/members/${member.id}`} className="btn-primary px-3 py-1.5 text-xs">
                          Profile
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Mobile card layout */}
              <div className="space-y-4 p-4 lg:hidden">
                {members.items.map((member) => (
                  <div key={member.id} className="rounded-md border border-line bg-surface-inset p-4">
                    <div className="mb-3 flex items-start justify-between">
                      <div className="flex-1">
                        <Link
                          to={`/members/${member.id}`}
                          className="font-ui text-sm font-medium text-content transition-colors hover:text-accent"
                        >
                          {member.full_name}
                        </Link>
                        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                          <PartyTag party={member.party} />
                          <ChamberTag chamber={member.chamber} />
                          {member.state && (
                            <span className="rounded-sm bg-surface-raised px-1.5 py-0.5 font-data text-[10px] uppercase tracking-[0.1em] text-content-muted">
                              {member.state}
                            </span>
                          )}
                        </div>
                      </div>
                      <Link to={`/members/${member.id}`} className="btn-primary ml-2 px-3 py-1.5 text-xs">
                        Profile
                      </Link>
                    </div>

                    <div className="space-y-2 font-ui text-sm">
                      <div className="flex justify-between">
                        <span className="text-content-faint">Total Trades</span>
                        <span className="font-data tabular-nums text-content">
                          {member.trade_count?.toLocaleString() ?? '—'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-content-faint">Total Volume</span>
                        <span className="font-data tabular-nums text-content">
                          {member.total_trade_value ? fmtMoney(member.total_trade_value / 100) : '—'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Pagination */}
          {members.pages > 1 && (
            <div className="flex items-center justify-between border-t border-line bg-surface-inset px-4 py-3 sm:px-6">
              <div className="flex flex-1 justify-between sm:hidden">
                <button
                  onClick={() => fetchMembers(currentPage - 1)}
                  disabled={!members.has_prev}
                  className="btn-secondary text-sm disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => fetchMembers(currentPage + 1)}
                  disabled={!members.has_next}
                  className="btn-secondary text-sm disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                <p className="font-ui text-sm text-content-muted">
                  Showing{' '}
                  <span className="font-data tabular-nums text-content">{(currentPage - 1) * 20 + 1}</span> to{' '}
                  <span className="font-data tabular-nums text-content">
                    {Math.min(currentPage * 20, members.total)}
                  </span>{' '}
                  of <span className="font-data tabular-nums text-content">{members.total}</span> results
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => fetchMembers(currentPage - 1)}
                    disabled={!members.has_prev}
                    className="btn-outline text-sm disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="font-data text-xs uppercase tracking-[0.1em] text-content-faint">
                    Page {currentPage} of {members.pages}
                  </span>
                  <button
                    onClick={() => fetchMembers(currentPage + 1)}
                    disabled={!members.has_next}
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

export default MembersBrowser;
