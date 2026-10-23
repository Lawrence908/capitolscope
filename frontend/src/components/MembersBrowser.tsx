import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import type { CongressMember, MemberFilters, PaginatedResponse } from '../types';
import apiClient from '../services/api';
import { DisclosureGauge, HatchMark, PageHeader, PartyTag, Spinner, affiliation, partyMeta } from './ui';
import { STATE_NAMES, fmtDate, memberRole, roundDays } from './members/memberFormat';

type SortKey = NonNullable<MemberFilters['sort_by']>;
type SortOrder = 'asc' | 'desc';

const PAGE_SIZE = 50;

const COLUMNS: { key: SortKey; label: string; defaultOrder: SortOrder; align?: 'right' | 'center' }[] = [
  { key: 'name', label: 'Name', defaultOrder: 'asc' },
  { key: 'state', label: 'Affiliation', defaultOrder: 'asc' },
  { key: 'chamber', label: 'Chamber', defaultOrder: 'asc' },
  { key: 'trades', label: 'Trades', defaultOrder: 'desc', align: 'right' },
  { key: 'last_filing', label: 'Last filing', defaultOrder: 'desc' },
  { key: 'avg_days', label: 'Avg. days to disclose', defaultOrder: 'desc', align: 'center' },
  { key: 'late', label: 'Late', defaultOrder: 'desc', align: 'right' },
];
const SORT_KEYS = new Set<string>(COLUMNS.map((c) => c.key));

const STATE_OPTIONS = Object.entries(STATE_NAMES).sort((a, b) => a[1].localeCompare(b[1]));

const chamberLabel = (c: string | null | undefined): string =>
  (c || '').toLowerCase().startsWith('s') ? 'Senate' : (c || '').toLowerCase().startsWith('h') ? 'House' : '–';

/** PartyTag + "D-NJ-5"; tolerates missing party/state. */
const Affiliation: React.FC<{ m: CongressMember }> = ({ m }) => {
  const known = partyMeta(m.party).label !== '?';
  const text = affiliation(m.party, m.state, m.chamber?.toLowerCase().startsWith('h') ? m.district : null);
  if (!known && !text) return <span className="font-ui text-xs text-content-faint">Not on file</span>;
  return (
    <span className="inline-flex items-center gap-2">
      {known && <PartyTag party={m.party} />}
      <span className="font-ui text-sm text-content-muted">{text}</span>
    </span>
  );
};

const AvgDays: React.FC<{ days: number | null | undefined }> = ({ days }) => {
  const d = roundDays(days);
  if (d == null) return <span className="font-ui text-xs text-content-faint">–</span>;
  return (
    <span className="inline-flex items-center gap-2">
      <DisclosureGauge days={d} size="xs" />
      <span className={`w-14 font-ui text-sm tabular-nums ${d > 45 ? 'font-bold text-accent' : 'text-content'}`}>
        {d} day{d === 1 ? '' : 's'}
      </span>
    </span>
  );
};

const LateCount: React.FC<{ n: number | null | undefined }> = ({ n }) =>
  n ? (
    <span className="inline-flex items-center justify-end gap-2">
      <HatchMark className="h-3 w-5" title="Filed after the 45-day limit" />
      <span className="font-display text-xl font-extrabold tabular-nums text-content">{n.toLocaleString()}</span>
    </span>
  ) : (
    <span className="font-ui text-sm tabular-nums text-content-faint">0</span>
  );

const selectCls = 'input-field py-2 text-sm';
const labelCls = 'mb-1 block font-ui text-xs font-semibold text-content-faint';

const MembersBrowser: React.FC = () => {
  const [params, setParams] = useSearchParams();

  const search = params.get('q') ?? '';
  const chamber = params.get('chamber') ?? '';
  const party = params.get('party') ?? '';
  const state = params.get('state') ?? '';
  const includeAll = params.get('all') === '1';
  const sortParam = params.get('sort') ?? 'trades';
  const sortBy = (SORT_KEYS.has(sortParam) ? sortParam : 'trades') as SortKey;
  const order: SortOrder =
    params.get('order') === 'asc' || params.get('order') === 'desc'
      ? (params.get('order') as SortOrder)
      : COLUMNS.find((c) => c.key === sortBy)?.defaultOrder ?? 'desc';
  const page = Math.max(1, Number(params.get('page')) || 1);

  const [searchText, setSearchText] = useState(search);
  const [data, setData] = useState<PaginatedResponse<CongressMember> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const update = (patch: Record<string, string | null>, resetPage = true) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v == null || v === '') next.delete(k);
      else next.set(k, v);
    }
    if (resetPage) next.delete('page');
    setParams(next, { replace: true });
  };

  // Keep the box in sync when the URL changes from outside (back/forward, links).
  useEffect(() => setSearchText(search), [search]);

  // Debounce typing into the q param.
  useEffect(() => {
    if (searchText.trim() === search) return;
    const t = setTimeout(() => {
      const next = new URLSearchParams(params);
      if (searchText.trim()) next.set('q', searchText.trim());
      else next.delete('q');
      next.delete('page');
      setParams(next, { replace: true });
    }, 300);
    return () => clearTimeout(t);
  }, [searchText, search, params, setParams]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const filters: MemberFilters = {
      search: search || undefined,
      chamber: chamber === 'House' || chamber === 'Senate' ? chamber : undefined,
      party: party || undefined,
      state: state || undefined,
      has_trades: !includeAll,
      sort_by: sortBy,
      sort_order: order,
    };
    apiClient
      .getMembers(filters, page, PAGE_SIZE)
      .then((res) => !cancelled && setData(res))
      .catch(() => !cancelled && setError('Could not load members. Please try again.'))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [search, chamber, party, state, includeAll, sortBy, order, page]);

  const onSort = (key: SortKey) => {
    const col = COLUMNS.find((c) => c.key === key);
    const nextOrder: SortOrder = key === sortBy ? (order === 'asc' ? 'desc' : 'asc') : col?.defaultOrder ?? 'asc';
    update({ sort: key, order: nextOrder });
  };

  const hasFilters = Boolean(search || chamber || party || state || includeAll);
  const items = useMemo(() => data?.items ?? [], [data]);

  return (
    <div>
      <PageHeader
        eyebrow="Members"
        title="Members of Congress"
        subtitle="Every member's disclosed stock trades under the STOCK Act. Sort by activity or by how long filings took, and open a member for their full record."
        stats={data ? [{ label: hasFilters ? 'Matching members' : 'Members with trades', value: data.total.toLocaleString() }] : undefined}
      />

      {/* ---- Filters ---- */}
      <div className="grid gap-4 border-b border-line pb-6 sm:grid-cols-2 lg:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))_auto]">
        <div>
          <label htmlFor="member-search" className={labelCls}>
            Search
          </label>
          <input
            id="member-search"
            type="search"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Name or state code"
            className="input-field py-2 text-sm"
          />
        </div>
        <div>
          <label htmlFor="member-chamber" className={labelCls}>
            Chamber
          </label>
          <select id="member-chamber" value={chamber} onChange={(e) => update({ chamber: e.target.value })} className={selectCls}>
            <option value="">Both chambers</option>
            <option value="House">House</option>
            <option value="Senate">Senate</option>
          </select>
        </div>
        <div>
          <label htmlFor="member-party" className={labelCls}>
            Party
          </label>
          <select id="member-party" value={party} onChange={(e) => update({ party: e.target.value })} className={selectCls}>
            <option value="">All parties</option>
            <option value="D">Democrat</option>
            <option value="R">Republican</option>
            <option value="I">Independent</option>
          </select>
        </div>
        <div>
          <label htmlFor="member-state" className={labelCls}>
            State
          </label>
          <select id="member-state" value={state} onChange={(e) => update({ state: e.target.value })} className={selectCls}>
            <option value="">All states</option>
            {STATE_OPTIONS.map(([code, name]) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col justify-end gap-2">
          <label className="inline-flex items-center gap-2 font-ui text-sm text-content-muted">
            <input
              type="checkbox"
              checked={includeAll}
              onChange={(e) => update({ all: e.target.checked ? '1' : null })}
              className="h-4 w-4 accent-[var(--content)]"
            />
            Include members with no trades
          </label>
          {hasFilters && (
            <button
              type="button"
              onClick={() => setParams(new URLSearchParams(), { replace: true })}
              className="self-start font-ui text-sm font-semibold text-content underline hover:text-accent"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {error && <p className="mt-6 font-ui text-sm font-semibold text-accent">{error}</p>}

      {loading && !data ? (
        <Spinner label="Loading members" />
      ) : items.length === 0 && !loading ? (
        <div className="py-16 text-center">
          <p className="font-display text-3xl font-extrabold text-content">No members match</p>
          <p className="mt-2 font-ui text-sm text-content-faint">Try a different name, or clear the filters.</p>
        </div>
      ) : (
        <div className={`mt-2 transition-opacity ${loading ? 'opacity-60' : ''}`}>
          {/* Desktop table */}
          <table className="hidden w-full text-left lg:table">
            <thead>
              <tr className="border-b-[3px] border-content">
                {COLUMNS.map((c) => {
                  const active = c.key === sortBy;
                  return (
                    <th
                      key={c.key}
                      scope="col"
                      aria-sort={active ? (order === 'asc' ? 'ascending' : 'descending') : 'none'}
                      className={`py-2.5 pr-4 ${c.align === 'right' ? 'text-right' : c.align === 'center' ? 'text-center' : ''}`}
                    >
                      <button
                        type="button"
                        onClick={() => onSort(c.key)}
                        className={`font-ui text-xs font-bold uppercase tracking-[0.06em] ${
                          active ? 'text-accent' : 'text-content-faint hover:text-content'
                        }`}
                      >
                        {c.label}
                        <span aria-hidden className="ml-1 inline-block w-2">
                          {active ? (order === 'asc' ? '▲' : '▼') : ''}
                        </span>
                      </button>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {items.map((m) => (
                <tr key={m.id} className="border-b border-line hover:bg-surface-inset">
                  <td className="py-2.5 pr-4">
                    <Link to={`/members/${m.id}`} className="font-ui text-[15px] font-bold text-content hover:text-accent">
                      {m.full_name}
                    </Link>
                    <div className="font-ui text-xs text-content-faint">{memberRole(m.chamber, m.state, m.district)}</div>
                  </td>
                  <td className="py-2.5 pr-4">
                    <Affiliation m={m} />
                  </td>
                  <td className="py-2.5 pr-4 font-ui text-sm text-content-muted">{chamberLabel(m.chamber)}</td>
                  <td className="py-2.5 pr-4 text-right font-display text-2xl font-extrabold tabular-nums text-content">
                    {(m.trade_count ?? 0).toLocaleString()}
                  </td>
                  <td className="py-2.5 pr-4 font-ui text-sm tabular-nums text-content-muted">
                    {fmtDate(m.last_filing_date) || '–'}
                  </td>
                  <td className="py-2.5 pr-4 text-center">
                    <AvgDays days={m.avg_days_to_disclose} />
                  </td>
                  <td className="py-2.5 pr-4 text-right">
                    <LateCount n={m.late_count} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Mobile list */}
          <div className="lg:hidden">
            <div className="flex items-center gap-2 border-b-[3px] border-content py-2">
              <label htmlFor="member-sort" className="font-ui text-xs font-semibold text-content-faint">
                Sort
              </label>
              <select
                id="member-sort"
                value={`${sortBy}:${order}`}
                onChange={(e) => {
                  const [k, o] = e.target.value.split(':');
                  update({ sort: k, order: o });
                }}
                className="input-field w-auto py-1 text-sm"
              >
                {COLUMNS.flatMap((c) => [
                  <option key={`${c.key}:desc`} value={`${c.key}:desc`}>
                    {c.label}, high to low
                  </option>,
                  <option key={`${c.key}:asc`} value={`${c.key}:asc`}>
                    {c.label}, low to high
                  </option>,
                ])}
              </select>
            </div>
            <ul>
              {items.map((m) => (
                <li key={m.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-line py-3">
                  <div className="min-w-0">
                    <Link to={`/members/${m.id}`} className="block truncate font-ui text-[15px] font-bold text-content hover:text-accent">
                      {m.full_name}
                    </Link>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                      <Affiliation m={m} />
                      <span className="font-ui text-xs text-content-faint">
                        {m.last_filing_date ? `Last filed ${fmtDate(m.last_filing_date)}` : 'No filings'}
                      </span>
                      {m.late_count ? <LateCount n={m.late_count} /> : null}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <AvgDays days={m.avg_days_to_disclose} />
                    <div className="text-right">
                      <div className="font-display text-2xl font-extrabold leading-none tabular-nums text-content">
                        {(m.trade_count ?? 0).toLocaleString()}
                      </div>
                      <div className="font-ui text-[11px] text-content-faint">trades</div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
              <p className="font-ui text-sm text-content-muted">
                {((page - 1) * PAGE_SIZE + 1).toLocaleString()} to {Math.min(page * PAGE_SIZE, data.total).toLocaleString()} of{' '}
                {data.total.toLocaleString()}
              </p>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => update({ page: String(page - 1) }, false)}
                  disabled={!data.has_prev}
                  className="btn-secondary px-4 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Previous
                </button>
                <span className="font-ui text-sm tabular-nums text-content-faint">
                  Page {page} of {data.pages}
                </span>
                <button
                  type="button"
                  onClick={() => update({ page: String(page + 1) }, false)}
                  disabled={!data.has_next}
                  className="btn-secondary px-4 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MembersBrowser;
