import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiClient } from '../services/api';
import type {
  CongressMember,
  CongressionalTrade,
  EquityCurveResult,
  MemberDisclosureStats,
  MirrorHoldingsResult,
} from '../types';
import { DISCLOSURE_LIMIT_DAYS, DisclosureGauge, HatchMark, PartyTag, Spinner, fmtMoney, partyMeta } from './ui';
import DisclosureRow from './trades/DisclosureRow';
import LineChart from './charts/LineChart';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import {
  fmtDate,
  isHouse,
  isSenate,
  memberRole,
  roundDays,
  shortCommittee,
  stateName,
  yearOf,
} from './members/memberFormat';

const TRADES_PAGE = 50;

// Canvas charts cannot read CSS variables, so mirror the Bulletin ink and
// benchmark tokens (index.css --content / --bench) per theme.
const CHART_INK = { light: '#121417', dark: '#f3f3ef' };
const CHART_BENCH = { light: '#9ca1a9', dark: '#6f747c' };

const SectionHead: React.FC<{ title: React.ReactNode; note?: React.ReactNode }> = ({ title, note }) => (
  <div className="mb-1 flex items-end justify-between gap-4 border-b-[3px] border-content pb-2">
    <h2 className="font-display text-4xl font-extrabold leading-none text-content">{title}</h2>
    {note != null && <p className="text-right font-ui text-sm text-content-muted">{note}</p>}
  </div>
);

const Empty: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="py-8 font-ui text-sm text-content-faint">{children}</p>
);

/** Ink bar on an inset track; `fraction` is 0..1 of the track. */
const InkBar: React.FC<{ fraction: number; className?: string }> = ({ fraction, className = 'h-3' }) => (
  <div className={`w-full bg-surface-inset ${className}`}>
    <div className="h-full bg-content" style={{ width: `${Math.max(1.5, Math.min(1, fraction) * 100)}%` }} />
  </div>
);

/** Group trades (already newest-filing-first) by their filing date. */
const groupByFiling = (trades: CongressionalTrade[]) => {
  const groups: { date: string; trades: CongressionalTrade[] }[] = [];
  for (const t of trades) {
    const d = (t.notification_date || '').slice(0, 10);
    const last = groups[groups.length - 1];
    if (last && last.date === d) last.trades.push(t);
    else groups.push({ date: d, trades: [t] });
  }
  return groups;
};

const monthLabel = (iso: string): string => {
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
  return Number.isNaN(d.getTime()) ? iso.slice(0, 7) : d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
};

const MemberProfile: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { isDarkMode } = useTheme();
  const { isAuthenticated } = useAuth();

  const [member, setMember] = useState<CongressMember | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [stats, setStats] = useState<MemberDisclosureStats | null>(null);
  const [portfolio, setPortfolio] = useState<MirrorHoldingsResult | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(true);
  const [performance, setPerformance] = useState<EquityCurveResult | null>(null);
  const [performanceLoading, setPerformanceLoading] = useState(true);

  const [trades, setTrades] = useState<CongressionalTrade[]>([]);
  const [tradesTotal, setTradesTotal] = useState(0);
  const [tradesPage, setTradesPage] = useState(1);
  const [tradesHasNext, setTradesHasNext] = useState(false);
  const [tradesLoading, setTradesLoading] = useState(true);

  const [alertState, setAlertState] = useState<'idle' | 'saving' | 'done' | 'error'>('idle');

  // Member + everything that hangs off it, loaded independently so one slow
  // panel (holdings, performance) never blocks the rest of the page.
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setMember(null);
    setStats(null);
    setPortfolio(null);
    setPerformance(null);
    setTrades([]);
    setTradesPage(1);
    setAlertState('idle');
    setPortfolioLoading(true);
    setPerformanceLoading(true);
    setTradesLoading(true);

    apiClient
      .getMember(id)
      .then((m) => {
        if (cancelled) return;
        if (m) setMember(m);
        else setError('Member not found');
      })
      .catch(() => !cancelled && setError('Member not found'))
      .finally(() => !cancelled && setLoading(false));

    apiClient
      .getMemberStats(id)
      .then((s) => !cancelled && setStats(s ?? null))
      .catch(() => !cancelled && setStats(null));

    apiClient
      .getMemberPortfolio(id)
      .then((p) => !cancelled && setPortfolio(p ?? null))
      .catch(() => !cancelled && setPortfolio(null))
      .finally(() => !cancelled && setPortfolioLoading(false));

    apiClient
      .getMemberPerformance(id)
      .then((p) => !cancelled && setPerformance(p ?? null))
      .catch(() => !cancelled && setPerformance(null))
      .finally(() => !cancelled && setPerformanceLoading(false));

    apiClient
      .getMemberTrades(id, 1, TRADES_PAGE)
      .then((res) => {
        if (cancelled) return;
        setTrades(res.items);
        setTradesTotal(res.total);
        setTradesHasNext(res.has_next);
      })
      .catch(() => !cancelled && setTrades([]))
      .finally(() => !cancelled && setTradesLoading(false));

    return () => {
      cancelled = true;
    };
  }, [id]);

  const loadMoreTrades = useCallback(async () => {
    if (!id) return;
    setTradesLoading(true);
    try {
      const next = tradesPage + 1;
      const res = await apiClient.getMemberTrades(id, next, TRADES_PAGE);
      setTrades((prev) => [...prev, ...res.items]);
      setTradesPage(next);
      setTradesHasNext(res.has_next);
    } catch {
      setTradesHasNext(false);
    } finally {
      setTradesLoading(false);
    }
  }, [id, tradesPage]);

  const createAlert = useCallback(async () => {
    if (!id || !member) return;
    setAlertState('saving');
    try {
      await apiClient.createMemberAlert(id, {
        name: `${member.full_name} trades`,
        member_name: member.full_name,
      });
      setAlertState('done');
    } catch {
      setAlertState('error');
    }
  }, [id, member]);

  const tradeGroups = useMemo(() => groupByFiling(trades), [trades]);

  const sectors = useMemo(() => {
    const all = (portfolio?.sector_allocation ?? []).filter((s) => (s.weight_pct ?? 0) > 0);
    const top = all.slice(0, 6);
    const rest = all.slice(6).reduce((acc, s) => acc + (s.weight_pct ?? 0), 0);
    const rows = top.map((s) => ({ sector: s.sector, weight: s.weight_pct ?? 0 }));
    if (rest > 0.05) rows.push({ sector: 'Other', weight: rest });
    const max = Math.max(1, ...rows.map((r) => r.weight));
    return { rows, max };
  }, [portfolio]);

  const holdings = useMemo(() => {
    const total = portfolio?.totals.market_value ?? 0;
    const rows = (portfolio?.holdings ?? []).slice(0, 10).map((h) => ({
      ...h,
      share: total > 0 ? (h.market_value / total) * 100 : 0,
    }));
    const max = Math.max(0.01, ...rows.map((r) => r.share));
    return { rows, max };
  }, [portfolio]);

  const chart = useMemo(() => {
    const series = performance?.series ?? [];
    if (series.length < 2) return null;
    const peak = Math.max(...series.map((p) => Math.max(p.portfolio_value || 0, p.spy_value || 0)));
    const [div, unit] = peak >= 1e6 ? [1e6, '$M'] : peak >= 1e3 ? [1e3, '$K'] : [1, '$'];
    const ink = isDarkMode ? CHART_INK.dark : CHART_INK.light;
    const bench = isDarkMode ? CHART_BENCH.dark : CHART_BENCH.light;
    // pointRadius is a Chart.js dataset option not (yet) in LineChartData's
    // type; passing the dataset as a variable keeps it type-safe.
    const portfolioDs = {
      label: 'Portfolio',
      data: series.map((p) => +(p.portfolio_value / div).toFixed(2)),
      borderColor: ink,
      backgroundColor: ink,
      borderWidth: 4,
      fill: false,
      tension: 0.15,
      pointRadius: 0,
    };
    const spyDs = {
      label: 'SPY, same cash flows',
      data: series.map((p) => (p.spy_value == null ? Number.NaN : +(p.spy_value / div).toFixed(2))),
      borderColor: bench,
      backgroundColor: bench,
      borderWidth: 3,
      fill: false,
      tension: 0.15,
      pointRadius: 0,
    };
    return {
      unit,
      data: { labels: series.map((p) => monthLabel(p.date)), datasets: [portfolioDs, spyDs] },
    };
  }, [performance, isDarkMode]);

  if (loading) return <Spinner label="Loading member" />;

  if (error || !member) {
    return (
      <div className="py-16">
        <Link to="/members" className="font-ui text-sm font-semibold text-content-muted hover:text-accent">
          Back to members
        </Link>
        <h1 className="mt-4 font-display text-6xl font-extrabold leading-none text-content">Member not found</h1>
        <p className="mt-3 font-ui text-content-muted">No member of Congress matches this link.</p>
      </div>
    );
  }

  const hasParty = partyMeta(member.party).label !== '?';
  const role = memberRole(member.chamber, member.state, member.district);
  const committees = (member.committees ?? []).filter(Boolean);
  const totalTrades = stats?.total_trades ?? member.trade_count ?? 0;
  const firstYear = yearOf(stats?.first_trade_date);
  const avgDays = roundDays(stats?.avg_days_to_disclose);
  const medianDays = roundDays(stats?.median_days_to_disclose);
  const lastName = member.last_name || member.full_name;
  const pv = performance?.summary.portfolio_value;
  const sv = performance?.summary.spy_value;
  const vsSpy = performance?.summary.vs_spy_pct;

  return (
    <div>
      {/* ---- Ink slab header (full-bleed via a clipped spread shadow, no overflow) ---- */}
      <header
        className="-mt-8 bg-slab pb-8 pt-7 text-slab-on"
        style={{ boxShadow: '0 0 0 100vmax var(--slab)', clipPath: 'inset(0 -100vmax)' }}
      >
        <nav aria-label="Breadcrumb" className="font-ui text-[13px] text-slab-muted">
          <Link to="/members" className="hover:text-slab-on">
            Members
          </Link>
          {(isHouse(member.chamber) || isSenate(member.chamber)) && (
            <>
              {' / '}
              <Link to={`/members?chamber=${isSenate(member.chamber) ? 'Senate' : 'House'}`} className="hover:text-slab-on">
                {isSenate(member.chamber) ? 'Senate' : 'House'}
              </Link>
            </>
          )}
          {member.state && (
            <>
              {' / '}
              <Link to={`/members?state=${member.state}`} className="hover:text-slab-on">
                {stateName(member.state)}
              </Link>
            </>
          )}
        </nav>

        <div className="mt-5 grid items-end gap-8 lg:grid-cols-[minmax(0,1fr)_auto]">
          <div className="min-w-0">
            <h1 className="break-words font-display text-[clamp(3.5rem,10vw,9.75rem)] font-extrabold uppercase leading-[0.82] tracking-[-0.005em]">
              {member.first_name && member.last_name ? (
                <>
                  <span className="block">{member.first_name}</span>
                  <span className="block">{member.last_name}</span>
                </>
              ) : (
                member.full_name
              )}
            </h1>
            <div className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-1 font-ui text-lg">
              {hasParty && <PartyTag party={member.party} className="!border-slab-on !text-slab-on" />}
              <span>
                {hasParty ? `${partyMeta(member.party).name}, ` : ''}
                {role}
              </span>
              {member.term_start && (
                <span className="text-slab-muted">Serving since {yearOf(member.term_start)}</span>
              )}
            </div>
            {committees.length > 0 && (
              <p className="mt-2 max-w-[80ch] font-ui text-sm text-slab-muted">
                Committees:{' '}
                {committees.map((c, i) => (
                  <React.Fragment key={c}>
                    {i > 0 && ', '}
                    <span className="font-semibold text-slab-on">{shortCommittee(c)}</span>
                  </React.Fragment>
                ))}
              </p>
            )}
          </div>

          <dl className="flex flex-wrap gap-y-4">
            <div className="pr-6">
              <dd className="font-display text-6xl font-extrabold leading-none tabular-nums">
                {totalTrades.toLocaleString()}
              </dd>
              <dt className="mt-2 max-w-[16ch] font-ui text-[13px] text-slab-muted">
                trades disclosed{firstYear ? ` since ${firstYear}` : ''}
              </dt>
            </div>
            {stats && (
              <div className="border-l border-slab-muted px-6">
                <dd className="font-display text-6xl font-extrabold leading-none tabular-nums">
                  {stats.trades_last_12_months.toLocaleString()}
                </dd>
                <dt className="mt-2 max-w-[16ch] font-ui text-[13px] text-slab-muted">in the last 12 months</dt>
              </div>
            )}
            {portfolio && portfolio.totals.holdings_count > 0 && (
              <div className="border-l border-slab-muted pl-6">
                <dd className="font-display text-6xl font-extrabold leading-none tabular-nums">
                  {fmtMoney(portfolio.totals.market_value)}
                </dd>
                <dt className="mt-2 max-w-[18ch] font-ui text-[13px] text-slab-muted">
                  estimated holdings, {portfolio.totals.holdings_count} positions
                </dt>
              </div>
            )}
          </dl>
        </div>
      </header>

      {/* ---- Disclosure timing band ---- */}
      <section className="grid gap-8 border-b-[3px] border-content py-8 md:grid-cols-2 xl:grid-cols-4">
        <div className="flex items-center gap-5">
          <DisclosureGauge
            days={avgDays}
            size="md"
            valueLabel={avgDays != null ? `${avgDays} days` : 'No data'}
          />
          <div className="font-ui text-sm text-content-muted">
            <div className="font-bold text-content">Average time to disclose</div>
            {medianDays != null && <div>Median {medianDays} days</div>}
            {stats?.max_days_to_disclose != null && <div>Slowest {stats.max_days_to_disclose} days</div>}
            <div className="text-content-faint">Legal limit {DISCLOSURE_LIMIT_DAYS} days</div>
          </div>
        </div>

        <div>
          <div className="font-ui text-sm font-bold text-content">Filed after the {DISCLOSURE_LIMIT_DAYS}-day limit</div>
          <div className="mt-1 flex items-center gap-3">
            <span
              className={`font-display text-6xl font-extrabold leading-none tabular-nums ${
                stats && stats.late_count > 0 ? 'text-accent' : 'text-content'
              }`}
            >
              {stats ? stats.late_count.toLocaleString() : '–'}
            </span>
            {stats && stats.late_count > 0 && <HatchMark className="h-5 w-12" title="Late filings" />}
          </div>
          <p className="mt-2 font-ui text-sm text-content-muted">
            {stats == null
              ? 'Loading disclosure history.'
              : stats.timed_trades === 0
                ? 'No dated filings on record.'
                : stats.late_count === 0
                  ? `None of ${stats.timed_trades.toLocaleString()} trades were disclosed late.`
                  : `${stats.late_pct ?? 0}% of ${stats.timed_trades.toLocaleString()} trades. Amended filings excluded.`}
          </p>
        </div>

        <div>
          <div className="font-ui text-sm font-bold text-content">Reported volume</div>
          <div className="mt-1 font-display text-4xl font-extrabold leading-none tabular-nums text-content">
            {stats && stats.volume_max > 0
              ? `${fmtMoney(stats.volume_min / 100)}–${fmtMoney(stats.volume_max / 100)}${stats.volume_open_ended ? '+' : ''}`
              : '–'}
          </div>
          <p className="mt-2 font-ui text-sm text-content-muted">
            Sum of the disclosed ranges. Members report value bands, not exact amounts.
          </p>
        </div>

        <div className="font-ui text-sm text-content-muted">
          <div className="font-bold text-content">Activity</div>
          <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
            <dt className="text-content-faint">First trade</dt>
            <dd>{fmtDate(stats?.first_trade_date) || '–'}</dd>
            <dt className="text-content-faint">Last trade</dt>
            <dd>{fmtDate(stats?.last_trade_date) || '–'}</dd>
            <dt className="text-content-faint">Last filing</dt>
            <dd>{fmtDate(stats?.last_filing_date) || '–'}</dd>
            <dt className="text-content-faint">Buys / sells</dt>
            <dd className="tabular-nums">
              {stats ? `${stats.purchase_count.toLocaleString()} / ${stats.sale_count.toLocaleString()}` : '–'}
            </dd>
          </dl>
        </div>
      </section>

      {/* ---- Performance + sectors ---- */}
      <div className="grid gap-12 py-10 lg:grid-cols-12">
        <section className="lg:col-span-7">
          <SectionHead title="Performance vs SPY" note={chart ? `Reconstructed, ${chart.unit}` : 'Reconstructed'} />
          {performanceLoading ? (
            <Spinner label="Building equity curve" className="h-64" />
          ) : !chart ? (
            <Empty>Not enough priced trades to chart this member's portfolio.</Empty>
          ) : (
            <div className="mt-4 flex gap-4">
              <LineChart height={300} data={chart.data} className="min-w-0 flex-1" />
              <div className="flex w-28 shrink-0 flex-col justify-center gap-5">
                <div>
                  <div className="font-display text-3xl font-extrabold leading-none tabular-nums text-content">
                    {pv != null ? fmtMoney(pv) : '–'}
                  </div>
                  <div className="mt-1 font-ui text-xs text-content-muted">Portfolio</div>
                </div>
                <div>
                  <div className="font-display text-3xl font-extrabold leading-none tabular-nums text-bench">
                    {sv != null ? fmtMoney(sv) : '–'}
                  </div>
                  <div className="mt-1 font-ui text-xs text-content-muted">SPY, same cash flows</div>
                </div>
                {vsSpy != null && (
                  <div className="font-ui text-xs text-content-muted">
                    <span className="font-bold text-content">
                      {Math.abs(vsSpy).toFixed(1)}% {vsSpy >= 0 ? 'above' : 'below'}
                    </span>{' '}
                    SPY
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        <section className="lg:col-span-5">
          <SectionHead title="Sectors" note="Share of estimated value" />
          {portfolioLoading ? (
            <Spinner label="Reconstructing positions" className="h-64" />
          ) : sectors.rows.length === 0 ? (
            <Empty>No priced holdings to break down by sector.</Empty>
          ) : (
            <ul className="mt-2">
              {sectors.rows.map((s) => (
                <li key={s.sector} className="grid grid-cols-[10.5rem_minmax(0,1fr)_3.5rem] items-center gap-3 py-2">
                  <span className="truncate font-ui text-sm text-content">{s.sector}</span>
                  <InkBar fraction={s.weight / sectors.max} />
                  <span className="text-right font-display text-xl font-extrabold tabular-nums text-content">
                    {s.weight.toFixed(1)}%
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* ---- Holdings + trade history ---- */}
      <div className="grid gap-12 pb-10 lg:grid-cols-12">
        <section className="lg:col-span-5">
          <SectionHead
            title="Largest holdings"
            note={portfolio && portfolio.totals.holdings_count > 0 ? `Top ${holdings.rows.length} of ${portfolio.totals.holdings_count}` : undefined}
          />
          {portfolioLoading ? (
            <Spinner label="Reconstructing positions" className="h-64" />
          ) : holdings.rows.length === 0 ? (
            <Empty>No priced holdings to reconstruct for this member.</Empty>
          ) : (
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-line font-ui text-xs font-semibold text-content-faint">
                  <th className="py-2 pr-3 font-semibold">Ticker</th>
                  <th className="py-2 pr-3 font-semibold">Company</th>
                  <th className="py-2 text-right font-semibold">Share</th>
                </tr>
              </thead>
              <tbody>
                {holdings.rows.map((h) => (
                  <tr key={h.security_id} className="border-b border-line">
                    <td className="py-2 pr-3">
                      {h.ticker ? (
                        <Link
                          to={`/assets/${encodeURIComponent(h.ticker)}`}
                          className="font-display text-2xl font-extrabold leading-none text-content hover:text-accent"
                        >
                          {h.ticker}
                        </Link>
                      ) : (
                        <span className="font-display text-2xl font-extrabold leading-none text-content-faint">?</span>
                      )}
                    </td>
                    <td className="max-w-0 py-2 pr-3">
                      <div className="truncate font-ui text-sm text-content">{h.name || h.ticker}</div>
                      {h.sector && <div className="truncate font-ui text-xs text-content-faint">{h.sector}</div>}
                    </td>
                    <td className="w-36 py-2">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-20">
                          <InkBar fraction={h.share / holdings.max} className="h-2.5" />
                        </div>
                        <span className="w-12 text-right font-ui text-sm tabular-nums text-content">
                          {h.share.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="lg:col-span-7">
          <SectionHead title="Trade history" note="Grouped by filing date, newest first" />
          {tradesLoading && trades.length === 0 ? (
            <Spinner label="Loading trades" className="h-64" />
          ) : trades.length === 0 ? (
            <Empty>No disclosed trades on record for this member.</Empty>
          ) : (
            <div>
              {tradeGroups.map((g) => (
                <div key={g.date || 'undated'}>
                  <div className="flex items-baseline gap-3 border-b border-line pb-1.5 pt-4 font-ui text-sm">
                    <span className="font-bold text-content">
                      {g.date ? `Filed ${fmtDate(g.date)}` : 'Filing date unknown'}
                    </span>
                    <span className="text-content-faint">
                      {g.trades.length} trade{g.trades.length === 1 ? '' : 's'}
                    </span>
                  </div>
                  {g.trades.map((t) => (
                    <DisclosureRow key={t.id} trade={t} hideMember />
                  ))}
                </div>
              ))}
            </div>
          )}

          <div className="mt-6 flex flex-wrap items-center gap-4">
            {tradesHasNext && (
              <button type="button" onClick={loadMoreTrades} disabled={tradesLoading} className="btn-primary disabled:opacity-60">
                {tradesLoading ? 'Loading' : `Show more (${(tradesTotal - trades.length).toLocaleString()} left)`}
              </button>
            )}
            {isAuthenticated ? (
              alertState === 'done' ? (
                <span className="font-ui text-sm text-content-muted">
                  Alert set.{' '}
                  <Link to="/alerts" className="font-semibold text-content underline hover:text-accent">
                    Manage alerts
                  </Link>
                </span>
              ) : (
                <button
                  type="button"
                  onClick={createAlert}
                  disabled={alertState === 'saving'}
                  className="btn-secondary disabled:opacity-60"
                >
                  {alertState === 'saving' ? 'Saving' : `Get alerts for ${lastName}`}
                </button>
              )
            ) : (
              <Link to="/login" className="font-ui text-sm text-content-muted underline hover:text-accent">
                Sign in to get alerts when {lastName} files
              </Link>
            )}
            {alertState === 'error' && (
              <span className="font-ui text-sm text-accent">Could not create the alert. Check your plan limits in Alerts.</span>
            )}
          </div>
        </section>
      </div>

      <p className="max-w-[80ch] border-t border-line pt-4 font-ui text-xs leading-relaxed text-content-faint">
        Holdings are rebuilt from disclosed buys and sells at the midpoint of each reported range and valued at the
        latest close, so they are an estimate, not an exact portfolio. Only trades matched to a priced security are
        included. Performance compares the reconstructed portfolio with SPY bought and sold on the same dates with the
        same amounts. Disclosure timing counts days from the trade date to the filing date; amended filings and
        trades dated in the future are excluded. Source: House Clerk and Senate eFD periodic transaction reports.
      </p>
    </div>
  );
};

export default MemberProfile;
