import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import type { CongressMember, MemberFilters, PaginatedResponse } from '../types';
import apiClient from '../services/api';

const MembersBrowser: React.FC = () => {
  const [members, setMembers] = useState<PaginatedResponse<CongressMember> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<MemberFilters>({});
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchMembers = useCallback(async (page: number = 1) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getMembers({ ...filters }, page, 20);
      setMembers(response);
      setCurrentPage(page);
    } catch (err) {
      setError('Failed to fetch members. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [filters]);

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

  if (loading && !members) {
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
            <h2 className="text-xl font-semibold text-white">Congress Members</h2>
            <p className="text-sm text-gray-600 mt-1">
              {members?.total ? `${members.total.toLocaleString()} total members` : 'Loading...'}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={clearFilters}
              className="btn-secondary flex items-center gap-2"
            >
              Clear Filters
            </button>
          </div>
        </div>
        {/* Search bar */}
        <form onSubmit={handleSearch} className="mt-4">
          <div className="relative">
            <input
              type="text"
              placeholder="Search by name, state, or party..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field pl-4"
            />
          </div>
        </form>
        {/* Filters panel */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Party</label>
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
            <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
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
            <label className="block text-sm font-medium text-gray-700 mb-1">Chamber</label>
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
        </div>
      </div>
      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <span className="text-red-400 font-bold mr-2">!</span>
            <div className="ml-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        </div>
      )}
      {/* Members table */}
      {members && (
        <div className="card overflow-hidden">
          {members.items.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              <p className="text-lg font-semibold mb-2">No members found</p>
              <p className="text-sm">Try adjusting your filters or check back later.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Party</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">State</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Chamber</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Total Trades</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Total $ Volume</th>
                    <th className="px-6 py-3"></th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {members.items.map((member) => (
                    <tr key={member.id} className="hover:bg-gray-50 dark:hover:bg-gray-900">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Link to={`/members/${member.id}`} className="font-semibold text-primary-600 dark:text-primary-400 hover:underline">
                          {member.full_name}
                        </Link>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">{getPartyBadge(member.party)}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{member.state}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{getChamberBadge(member.chamber)}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{member.trade_count?.toLocaleString() ?? 'N/A'}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{member.total_trade_value ? `$${(member.total_trade_value / 100).toLocaleString()}` : 'N/A'}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <Link to={`/members/${member.id}`} className="btn-primary btn-sm">Profile</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {/* Pagination */}
          {members.pages > 1 && (
            <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
              <div className="flex-1 flex justify-between sm:hidden">
                <button
                  onClick={() => fetchMembers(currentPage - 1)}
                  disabled={!members.has_prev}
                  className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => fetchMembers(currentPage + 1)}
                  disabled={!members.has_next}
                  className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Showing{' '}
                    <span className="font-medium">{(currentPage - 1) * 20 + 1}</span>{' '}
                    to{' '}
                    <span className="font-medium">{Math.min(currentPage * 20, members.total)}</span>{' '}
                    of{' '}
                    <span className="font-medium">{members.total}</span> results
                  </p>
                </div>
                <div>
                  <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                    <button
                      onClick={() => fetchMembers(currentPage - 1)}
                      disabled={!members.has_prev}
                      className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <span className="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700">
                      Page {currentPage} of {members.pages}
                    </span>
                    <button
                      onClick={() => fetchMembers(currentPage + 1)}
                      disabled={!members.has_next}
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

export default MembersBrowser; 