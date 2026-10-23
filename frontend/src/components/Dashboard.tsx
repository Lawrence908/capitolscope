import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import type { CongressionalTrade, DataQualityStats, TopTradingMember } from '../types';
import apiClient from '../services/api';
import stripeService from '../services/stripeService';
import AnalyticsDebug from './AnalyticsDebug';
import DisclosureRow from './trades/DisclosureRow';
import { PageHeader, Panel, Spinner, PartyTag, partyMeta } from './ui';

// Payment Modal Component
interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  type: 'success' | 'cancelled';
  message: string;
  tier?: string;
}

const PaymentModal: React.FC<PaymentModalProps> = ({ isOpen, onClose, type, message, tier }) => {
  if (!isOpen) return null;

  // Feature descriptions based on tier (from PremiumSignup.tsx)
  const getTierFeatures = (tier: string) => {
    const features = {
      pro: [
        'Full Historical Data',
        'Weekly Summaries',
        'Multiple Buyer Alerts',
        'High-Value Trade Alerts',
        'Saved Portfolios / Watchlists',
      ],
      premium: [
        'TradingView-Style Charts',
        'Advanced Portfolio Analytics',
        'Sector/Committee-based Filters',
        'API Access (Rate-limited)',
        'Custom Alert Configurations',
      ],
      enterprise: [
        'Advanced Analytics Dashboard',
        'White-Label Dashboard Options',
        'Priority Support',
        'Increased API Limits',
        'Team Seats / Admin Panel',
      ],
    };
    return features[tier as keyof typeof features] || [];
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black/60" onClick={onClose} />
      <div className="flex min-h-full items-center justify-center p-4 text-center">
        <div className="relative w-full max-w-lg transform overflow-hidden border-2 border-content bg-surface-raised px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:p-6">
          <div className="absolute right-0 top-0 hidden pr-4 pt-4 sm:block">
            <button
              type="button"
              className="text-content-faint transition-colors hover:text-content focus:outline-none"
              onClick={onClose}
            >
              <span className="sr-only">Close</span>
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          <div className="sm:flex sm:items-start">
            <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full sm:mx-0 sm:h-10 sm:w-10">
              {type === 'success' ? (
                <CheckCircleIcon className="h-6 w-6 text-accent" />
              ) : (
                <XCircleIcon className="h-6 w-6 text-content" />
              )}
            </div>
            <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
              <h3 className="font-display text-3xl font-extrabold leading-none text-content">
                {type === 'success' ? 'Payment successful' : 'Payment cancelled'}
              </h3>
              <div className="mt-2">
                <p className="font-ui text-sm text-content-muted">
                  {message}
                  {tier && type === 'success' && (
                    <span className="mt-1 block font-semibold text-content">
                      Welcome to {tier.charAt(0).toUpperCase() + tier.slice(1)} tier.
                    </span>
                  )}
                </p>

                {/* Show unlocked features for successful payments */}
                {type === 'success' && tier && tier !== 'free' && (
                  <div className="mt-4">
                    <h4 className="mb-2 font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
                      You now have access to
                    </h4>
                    <ul className="space-y-1 font-ui text-sm text-content-muted">
                      {getTierFeatures(tier).map((feature, index) => (
                        <li key={index} className="flex items-center">
                          <CheckCircleIcon className="mr-2 h-4 w-4 flex-shrink-0 text-content" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
            <button type="button" className="btn-primary w-full px-3 py-2 text-sm sm:ml-3 sm:w-auto" onClick={onClose}>
              {type === 'success' ? 'Get Started' : 'OK'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DataQualityStats | null>(null);
  const [recentTrades, setRecentTrades] = useState<CongressionalTrade[]>([]);
  const [topMembers, setTopMembers] = useState<TopTradingMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paymentModal, setPaymentModal] = useState<{
    isOpen: boolean;
    type: 'success' | 'cancelled';
    message: string;
    tier?: string;
  }>({
    isOpen: false,
    type: 'success',
    message: '',
  });

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch data in parallel
        const [statsResponse, tradesResponse, membersResponse] = await Promise.all([
          apiClient.getDataQualityStats(),
          apiClient.getTrades({}, 1, 10),
          apiClient.getTopTradingMembers(10),
        ]);

        setStats(statsResponse);
        setRecentTrades(tradesResponse.items || []);
        setTopMembers(membersResponse || []);
      } catch (err) {
        setError('Failed to load dashboard data');
        console.error('Dashboard error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  // Handle payment success/cancellation on component mount
  useEffect(() => {
    const paymentSuccess = stripeService.handlePaymentSuccess();
    const paymentCancelled = stripeService.handlePaymentCancellation();

    if (paymentSuccess.success) {
      setPaymentModal({
        isOpen: true,
        type: 'success',
        message: paymentSuccess.message ?? '',
        tier: paymentSuccess.tier,
      });
      // Clean up URL params
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    if (paymentCancelled.cancelled) {
      setPaymentModal({
        isOpen: true,
        type: 'cancelled',
        message: paymentCancelled.message ?? '',
      });
      // Clean up URL params
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const closePaymentModal = () => {
    setPaymentModal((prev) => ({ ...prev, isOpen: false }));
  };

  if (loading) {
    return <Spinner label="Loading dashboard" />;
  }

  if (error) {
    return (
      <div className="flex items-center gap-3 border-l-4 border-accent bg-surface-inset px-4 py-3 text-content">
        <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0 text-accent" />
        <p className="font-ui text-sm">{error}</p>
      </div>
    );
  }

  const statCards: { title: string; value: string; caption: string; accent?: boolean; link: string }[] = [
    {
      title: 'Total trades',
      value: stats?.total_trades?.toLocaleString() || '0',
      caption: 'disclosed transactions on file',
      link: '/trades',
    },
    {
      title: 'Congress members',
      value: stats?.unique_members?.toLocaleString() || '0',
      caption: 'members with at least one filing',
      link: '/members',
    },
    {
      title: 'Unique tickers',
      value: stats?.unique_tickers?.toLocaleString() || '0',
      caption: 'distinct securities traded',
      link: '/trades',
    },
    {
      title: 'Missing tickers',
      value: `${stats?.null_ticker_percentage?.toFixed(1) || '0'}%`,
      caption: 'filings with no ticker reported',
      accent: true,
      link: '/data-quality',
    },
  ];

  const partyEntries = Object.entries(stats?.party_distribution || {});
  const partyTotal = partyEntries.reduce((sum, [, count]) => sum + Number(count), 0);
  const maxMemberTrades = Math.max(1, ...topMembers.map((m) => m.total_trades ?? 0));

  const sectionLink = 'font-ui text-[12px] font-bold uppercase tracking-[0.08em] text-content hover:text-accent';

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="Dashboard"
        subtitle="Congressional trading at a glance: disclosure volume, the most active members and the latest filings, drawn from public STOCK Act data."
      />

      {/* Stat rail */}
      <div className="grid grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat, i) => (
          <Link
            key={stat.title}
            to={stat.link}
            className={`group border-t-[3px] border-content py-4 pr-4 transition-colors hover:bg-surface-inset ${
              i > 0 ? 'lg:border-l lg:border-l-line lg:pl-4' : ''
            } ${i % 2 === 1 ? 'border-l border-l-line pl-4' : ''}`}
          >
            <div className="font-ui text-[11px] font-semibold uppercase tracking-[0.08em] text-content-faint">
              {stat.title}
            </div>
            <div
              className={`mt-1 font-display text-5xl font-extrabold leading-none tabular-nums ${
                stat.accent ? 'text-accent' : 'text-content'
              }`}
            >
              {stat.value}
            </div>
            <div className="mt-1.5 font-ui text-[12px] text-content-faint group-hover:text-content-muted">
              {stat.caption}
            </div>
          </Link>
        ))}
      </div>

      {/* Latest disclosures + most active */}
      <div className="mt-10 grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1.75fr)_minmax(0,1fr)]">
        <Panel
          title="Latest disclosures"
          right={
            <Link to="/trades" className={sectionLink}>
              All trades →
            </Link>
          }
        >
          {recentTrades && recentTrades.length > 0 ? (
            recentTrades.map((trade, index) => (
              <DisclosureRow key={trade.id || `trade-${index}`} trade={trade} />
            ))
          ) : (
            <div className="py-6 font-ui text-sm text-content-faint">No recent trades available</div>
          )}
        </Panel>

        <div className="space-y-10">
          <Panel
            title="Most active"
            right={
              <Link to="/members" className={sectionLink}>
                All members →
              </Link>
            }
          >
            {topMembers && topMembers.length > 0 ? (
              <div className="divide-y divide-line">
                {topMembers.map((member, index) => {
                  const n = member.total_trades ?? 0;
                  const row = (
                    <>
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex min-w-0 items-center gap-2">
                          <PartyTag party={member.member_party} />
                          <span className="truncate font-ui text-sm font-bold text-content">{member.member_name}</span>
                          <span className="shrink-0 font-ui text-xs text-content-faint">
                            {[member.member_state, member.member_chamber].filter(Boolean).join(' · ')}
                          </span>
                        </div>
                        <span className="font-display text-2xl font-extrabold leading-none tabular-nums text-content">
                          {n.toLocaleString()}
                        </span>
                      </div>
                      <div className="mt-1.5 h-2 bg-surface-inset">
                        <div className="h-full bg-content" style={{ width: `${(n / maxMemberTrades) * 100}%` }} />
                      </div>
                    </>
                  );
                  return member.member_id ? (
                    <Link
                      key={member.member_id}
                      to={`/members/${member.member_id}`}
                      className="block py-2.5 transition-colors hover:bg-surface-inset"
                    >
                      {row}
                    </Link>
                  ) : (
                    <div key={`member-${index}`} className="py-2.5">
                      {row}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-6 font-ui text-sm text-content-faint">No top members available</div>
            )}
          </Panel>

          {/* Party distribution: identical ink bars, labelled (never color-coded) */}
          {partyEntries.length > 0 && (
            <Panel title="Trades by party">
              <div className="space-y-4 py-4">
                {partyEntries.map(([party, count]) => {
                  const meta = partyMeta(party);
                  const frac = partyTotal ? Number(count) / partyTotal : 0;
                  return (
                    <div key={party}>
                      <div className="mb-1.5 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <PartyTag party={party} />
                          <span className="font-ui text-sm font-semibold text-content">{meta.name === 'Unknown' ? party : meta.name}</span>
                        </div>
                        <span className="font-ui text-sm tabular-nums text-content-muted">
                          <span className="font-display text-xl font-extrabold text-content">{Number(count).toLocaleString()}</span>
                          <span className="ml-2">{(frac * 100).toFixed(1)}%</span>
                        </span>
                      </div>
                      <div className="h-2 bg-surface-inset">
                        <div className="h-full bg-content" style={{ width: `${Math.max(1, frac * 100)}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>
          )}
        </div>
      </div>

      {/* Analytics Debug (for troubleshooting) */}
      <div className="mt-10">
        <AnalyticsDebug />
      </div>

      <PaymentModal
        isOpen={paymentModal.isOpen}
        onClose={closePaymentModal}
        type={paymentModal.type}
        message={paymentModal.message}
        tier={paymentModal.tier}
      />
    </div>
  );
};

export default Dashboard;
