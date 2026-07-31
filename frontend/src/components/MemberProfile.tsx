import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeftIcon, DocumentTextIcon, ChartBarIcon, UserIcon } from '@heroicons/react/24/outline';
import { apiClient } from '../services/api';
import type { CongressMember, CongressionalTrade, MirrorHoldingsResult } from '../types';
import { Panel, Spinner, StatTile, PartyTag, fmtMoney } from './ui';

/** Format an already-percentage number (e.g. 142.9 -> "+142.9%"). */
const pct = (n: number | null | undefined, signed = false): string => {
  if (n == null) return '—';
  const s = `${n.toFixed(1)}%`;
  return signed && n >= 0 ? `+${s}` : s;
};
const returnTone = (n: number | null | undefined): string =>
  n == null ? 'text-content' : n >= 0 ? 'text-accent' : 'text-sev-flag';

/** Map a raw disclosure transaction code (P/S/E/…) to a readable label. */
const txnLabel = (t: string | null | undefined): string => {
  switch ((t || '').toUpperCase()) {
    case 'P': return 'Purchase';
    case 'S': return 'Sale';
    case 'S (PARTIAL)': return 'Partial sale';
    case 'E': return 'Exchange';
    default: return t || '—';
  }
};

/** Render a trade's amount from the exact value or the disclosed cents range. */
const tradeAmount = (t: CongressionalTrade): string => {
  if (t.amount_exact != null) return fmtMoney(t.amount_exact / 100);
  if (t.amount_min != null && t.amount_max != null) {
    return `${fmtMoney(t.amount_min / 100)} – ${fmtMoney(t.amount_max / 100)}`;
  }
  if (t.amount_min != null) return fmtMoney(t.amount_min / 100);
  if (t.estimated_value != null) return fmtMoney(t.estimated_value / 100);
  return '—';
};

const Pill: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span className="rounded-sm bg-surface-inset px-2 py-0.5 font-data text-[11px] uppercase tracking-[0.1em] text-content-muted">
    {children}
  </span>
);

const MemberProfile: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [member, setMember] = useState<CongressMember | null>(null);
  const [recentTrades, setRecentTrades] = useState<CongressionalTrade[]>([]);
  const [portfolio, setPortfolio] = useState<MirrorHoldingsResult | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMemberData = async () => {
      if (!id) return;

      try {
        setLoading(true);
        // Use the proper getMember API endpoint
        const memberData = await apiClient.getMember(id);
        setMember(memberData);
      } catch (err) {
        setError('Failed to load member data');
        console.error('Error fetching member:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchMemberData();
  }, [id]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setPortfolioLoading(true);
    apiClient
      .getMemberPortfolio(id)
      .then((data) => {
        if (!cancelled) setPortfolio(data);
      })
      .catch((err) => {
        console.error('Error fetching member portfolio:', err);
        if (!cancelled) setPortfolio(null);
      })
      .finally(() => {
        if (!cancelled) setPortfolioLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    apiClient
      .getTrades({ member_ids: [id], sort_by: 'transaction_date', sort_order: 'desc' }, 1, 10)
      .then((data) => {
        if (!cancelled) setRecentTrades(data.items ?? []);
      })
      .catch((err) => {
        console.error('Error fetching member trades:', err);
        if (!cancelled) setRecentTrades([]);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return <Spinner label="Loading profile" />;
  }

  if (error || !member) {
    return (
      <div className="card p-6">
        <Link to="/members" className="btn-secondary mb-4 inline-flex items-center text-sm">
          <ArrowLeftIcon className="mr-2 h-4 w-4" />
          Back to Members
        </Link>
        <div className="text-center">
          <h2 className="mb-2 font-display text-xl text-content">{error || 'Member not found'}</h2>
          <p className="font-ui text-sm text-content-faint">The requested member could not be found.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <Link to="/members" className="btn-secondary inline-flex items-center text-sm">
          <ArrowLeftIcon className="mr-2 h-4 w-4" />
          Back to Members
        </Link>
        <div className="font-data text-[11px] uppercase tracking-[0.1em] text-content-faint">
          Updated {new Date().toLocaleDateString()}
        </div>
      </div>

      {/* Member Info Card */}
      <div className="card p-4 lg:p-6">
        <div className="flex flex-col items-start space-y-4 sm:flex-row sm:space-x-6 sm:space-y-0">
          <div className="flex-shrink-0">
            <div className="flex h-20 w-20 items-center justify-center rounded-full border border-line bg-surface-inset lg:h-24 lg:w-24">
              <UserIcon className="h-10 w-10 text-content-faint lg:h-12 lg:w-12" />
            </div>
          </div>
          <div className="flex-1">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
              <h1 className="font-display text-3xl font-medium text-content">{member.full_name}</h1>
              <Link
                to="/scrutiny"
                className="font-data text-[11px] uppercase tracking-[0.1em] text-accent hover:text-accent-strong"
              >
                View in Scrutiny →
              </Link>
            </div>
            <div className="mb-5 flex flex-wrap items-center gap-2">
              {member.party && <PartyTag party={member.party} />}
              {member.chamber && <Pill>{member.chamber}</Pill>}
              {member.state && <Pill>{member.state}</Pill>}
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <StatTile label="Total Trades" value={member.trade_count?.toLocaleString() || '—'} />
              <StatTile
                label="Total Volume"
                value={member.total_trade_value ? fmtMoney(member.total_trade_value / 100) : '—'}
                tone="accent"
              />
              <StatTile
                label="Portfolio Value"
                value={member.portfolio_value ? fmtMoney(member.portfolio_value / 100) : '—'}
                tone="brass"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Recent Trades */}
      <div className="mt-6">
        <Panel
          title="Recent Trades"
          right={
            <Link to="/trades" className="font-data text-[11px] uppercase tracking-[0.1em] text-accent hover:text-accent-strong">
              View all trades →
            </Link>
          }
        >
          {recentTrades.length > 0 ? (
            <div className="divide-y divide-line">
              {recentTrades.map((trade) => (
                <div key={trade.id} className="flex items-center justify-between px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-data font-medium text-content">{trade.ticker || 'Unknown'}</span>
                      <span className="font-ui text-xs text-content-faint">{txnLabel(trade.transaction_type)}</span>
                    </div>
                    {trade.asset_name ? (
                      <div className="mt-0.5 truncate font-ui text-[11px] text-content-muted">{trade.asset_name}</div>
                    ) : null}
                    <div className="mt-0.5 font-data text-[11px] tabular-nums text-content-faint">
                      {trade.transaction_date ? new Date(trade.transaction_date).toLocaleDateString() : "—"}
                    </div>
                  </div>
                  <div className="ml-2 text-right font-data text-sm tabular-nums text-content">
                    {tradeAmount(trade)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="px-4 py-10 text-center">
              <ChartBarIcon className="mx-auto mb-3 h-10 w-10 text-content-faint" />
              <p className="font-ui text-sm text-content-faint">No recent trades found</p>
            </div>
          )}
        </Panel>
      </div>

      {/* Reconstructed portfolio */}
      <div className="mt-6">
        <Panel
          title="Reconstructed Portfolio"
          right={
            portfolio?.meta ? (
              <span className="font-data text-[11px] uppercase tracking-[0.1em] text-content-faint">
                {portfolio.meta.priced_trades} priced trades
              </span>
            ) : undefined
          }
        >
          {portfolioLoading ? (
            <Spinner label="Reconstructing positions" />
          ) : !portfolio || portfolio.holdings.length === 0 ? (
            <div className="px-4 py-10 text-center">
              <ChartBarIcon className="mx-auto mb-3 h-10 w-10 text-content-faint" />
              <p className="font-ui text-sm text-content-faint">
                No priced holdings to reconstruct for this member.
              </p>
            </div>
          ) : (
            <div className="p-4">
              <div className="mb-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
                <StatTile label="Market Value" value={fmtMoney(portfolio.totals.market_value)} />
                <StatTile
                  label="Total Return"
                  value={pct(portfolio.totals.return_pct, true)}
                  tone={(portfolio.totals.return_pct ?? 0) >= 0 ? 'accent' : 'flag'}
                />
                <StatTile label="Cost Basis" value={fmtMoney(portfolio.totals.cost_basis)} />
                <StatTile label="Holdings" value={String(portfolio.totals.holdings_count)} />
              </div>

              {/* Sector allocation */}
              {portfolio.sector_allocation && portfolio.sector_allocation.length > 0 && (
                <div className="mb-6">
                  <div className="mb-2 font-data text-[10px] uppercase tracking-[0.14em] text-content-faint">
                    Sector allocation
                  </div>
                  <div className="space-y-1.5">
                    {portfolio.sector_allocation.slice(0, 6).map((s) => (
                      <div key={s.sector} className="flex items-center gap-3">
                        <span className="w-32 shrink-0 truncate font-ui text-xs text-content-muted">
                          {s.sector}
                        </span>
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-inset">
                          <div
                            className="h-full rounded-full bg-accent"
                            style={{ width: `${Math.min(100, s.weight_pct ?? 0)}%` }}
                          />
                        </div>
                        <span className="w-12 shrink-0 text-right font-data text-[11px] tabular-nums text-content-faint">
                          {s.weight_pct != null ? `${s.weight_pct.toFixed(0)}%` : '—'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Top holdings */}
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-line font-data text-[10px] uppercase tracking-[0.14em] text-content-faint">
                      <th className="px-2 py-2">Ticker</th>
                      <th className="px-2 py-2 text-right">Market value</th>
                      <th className="px-2 py-2 text-right">Return</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {portfolio.holdings.slice(0, 10).map((h) => (
                      <tr key={h.security_id}>
                        <td className="px-2 py-2">
                          <span className="font-data text-sm text-content">{h.ticker || '—'}</span>
                          {h.name && (
                            <span className="ml-2 font-ui text-xs text-content-faint">{h.name}</span>
                          )}
                        </td>
                        <td className="px-2 py-2 text-right font-data text-sm tabular-nums text-content">
                          {fmtMoney(h.market_value)}
                        </td>
                        <td className={`px-2 py-2 text-right font-data text-sm tabular-nums ${returnTone(h.return_pct)}`}>
                          {pct(h.return_pct, true)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 font-ui text-[11px] leading-relaxed text-content-faint">
                Reconstructed from disclosed trades (dollar ranges, no share counts) and valued at the
                latest close — an approximation, not an exact portfolio.
              </p>
            </div>
          )}
        </Panel>
      </div>

      {/* Additional sections */}
      <div className="mt-6">
        <Panel title="Additional Information">
          <div className="flex items-center gap-3 p-4">
            <DocumentTextIcon className="h-5 w-5 flex-shrink-0 text-content-faint" />
            <p className="font-ui text-sm text-content-muted">
              More detailed member information — voting records, committee assignments, and advanced
              analytics — will be available soon.
            </p>
          </div>
        </Panel>
      </div>
    </div>
  );
};

export default MemberProfile;
