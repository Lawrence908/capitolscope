import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  UserGroupIcon,
  DocumentTextIcon,
  ArrowTrendingUpIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import type { CongressionalTrade, CongressMember, DataQualityStats } from '../types';
import apiClient from '../services/api';
import stripeService from '../services/stripeService';
import AnalyticsDebug from './AnalyticsDebug';
import {
  PageHeader,
  Panel,
  Spinner,
  Meter,
  PartyTag,
  fmtMoney,
  partyMeta,
  type Tone,
} from './ui';

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
        <div className="card-elevated relative w-full max-w-lg transform overflow-hidden px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:p-6">
          <div className="absolute right-0 top-0 hidden pr-4 pt-4 sm:block">
            <button
              type="button"
              className="rounded-md text-content-faint transition-colors hover:text-content focus:outline-none"
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
                <XCircleIcon className="h-6 w-6 text-sev-flag" />
              )}
            </div>
            <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
              <h3 className="font-display text-lg font-medium leading-6 text-content">
                {type === 'success' ? 'Payment Successful' : 'Payment Cancelled'}
              </h3>
              <div className="mt-2">
                <p className="font-ui text-sm text-content-muted">
                  {message}
                  {tier && type === 'success' && (
                    <span className="mt-1 block font-medium text-accent">
                      Welcome to {tier.charAt(0).toUpperCase() + tier.slice(1)} tier.
                    </span>
                  )}
                </p>

                {/* Show unlocked features for successful payments */}
                {type === 'success' && tier && tier !== 'free' && (
                  <div className="mt-4">
                    <h4 className="mb-2 font-data text-[11px] uppercase tracking-[0.14em] text-content-faint">
                      You now have access to
                    </h4>
                    <ul className="space-y-1 font-ui text-sm text-content-muted">
                      {getTierFeatures(tier).map((feature, index) => (
                        <li key={index} className="flex items-center">
                          <CheckCircleIcon className="mr-2 h-4 w-4 flex-shrink-0 text-accent" />
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
  const [topMembers, setTopMembers] = useState<CongressMember[]>([]);
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

        setStats(statsResponse.data);
        setRecentTrades(tradesResponse.items || []);
        setTopMembers(membersResponse.data || []);
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
        message: paymentSuccess.message,
        tier: paymentSuccess.tier,
      });
      // Clean up URL params
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    if (paymentCancelled.cancelled) {
      setPaymentModal({
        isOpen: true,
        type: 'cancelled',
        message: paymentCancelled.message,
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
      <div className="flex items-center gap-3 rounded-md border border-sev-flag/40 px-4 py-3 status-error">
        <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" />
        <p className="font-ui text-sm">{error}</p>
      </div>
    );
  }

  const statCards: { title: string; value: string; icon: typeof DocumentTextIcon; tone: Tone; link: string }[] = [
    {
      title: 'Total Trades',
      value: stats?.total_trades?.toLocaleString() || '0',
      icon: DocumentTextIcon,
      tone: 'accent',
      link: '/trades',
    },
    {
      title: 'Congress Members',
      value: stats?.unique_members?.toLocaleString() || '0',
      icon: UserGroupIcon,
      tone: 'steel',
      link: '/members',
    },
    {
      title: 'Unique Tickers',
      value: stats?.unique_tickers?.toLocaleString() || '0',
      icon: ArrowTrendingUpIcon,
      tone: 'brass',
      link: '/trades',
    },
    {
      title: 'Missing Tickers',
      value: `${stats?.null_ticker_percentage?.toFixed(1) || '0'}%`,
      icon: ExclamationTriangleIcon,
      tone: 'flag',
      link: '/data-quality',
    },
  ];

  const toneText: Record<Tone, string> = {
    default: 'text-content',
    accent: 'text-accent',
    brass: 'text-accent-2',
    flag: 'text-sev-flag',
    steel: 'text-sev-info',
    coral: 'text-sev-watch',
  };

  const partyEntries = Object.entries(stats?.party_distribution || {});
  const partyTotal = partyEntries.reduce((sum, [, count]) => sum + Number(count), 0);

  return (
    <div>
      <PageHeader
        eyebrow="CapitolScope · Overview"
        title="Dashboard"
        subtitle="Congressional trading at a glance — disclosure volume, the most active members, and the latest filings, drawn from public STOCK Act data."
      />

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <Link key={stat.title} to={stat.link} className="card-interactive group p-5">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-data text-[10px] uppercase tracking-[0.14em] text-content-faint">
                    {stat.title}
                  </div>
                  <div className={`mt-2 font-data text-3xl font-medium tabular-nums ${toneText[stat.tone]}`}>
                    {stat.value}
                  </div>
                </div>
                <Icon className={`h-5 w-5 ${toneText[stat.tone]}`} />
              </div>
            </Link>
          );
        })}
      </div>

      {/* Recent trades and top members */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel
          title="Recent Trades"
          right={
            <Link to="/trades" className="font-data text-[11px] uppercase tracking-[0.1em] text-accent hover:text-accent-strong">
              View all →
            </Link>
          }
        >
          <div className="divide-y divide-line">
            {recentTrades && recentTrades.length > 0 ? (
              recentTrades.map((trade, index) => (
                <div key={trade.id || `trade-${index}`} className="flex items-center justify-between gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-ui text-sm font-medium text-content">
                      {trade.member_name || 'Unknown'}
                    </p>
                    <p className="mt-0.5 font-ui text-xs text-content-faint">
                      {trade.ticker ? (
                        <span className="font-data text-content-muted">{trade.ticker}</span>
                      ) : (
                        <span>No ticker</span>
                      )}
                      {' · '}
                      <span className="capitalize">{trade.transaction_type || 'Unknown'}</span>
                    </p>
                  </div>
                  <div className="ml-2 text-right">
                    <p className="font-data text-sm tabular-nums text-content">
                      {trade.estimated_value ? fmtMoney(trade.estimated_value / 100) : '—'}
                    </p>
                    <p className="font-data text-[11px] tabular-nums text-content-faint">
                      {new Date(trade.transaction_date).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <div className="px-4 py-6 text-center font-ui text-sm text-content-faint">
                No recent trades available
              </div>
            )}
          </div>
        </Panel>

        <Panel
          title="Top Trading Members"
          right={
            <Link to="/members" className="font-data text-[11px] uppercase tracking-[0.1em] text-accent hover:text-accent-strong">
              View all →
            </Link>
          }
        >
          <div className="divide-y divide-line">
            {topMembers && topMembers.length > 0 ? (
              topMembers.map((member, index) => (
                <div key={member.id || `member-${index}`} className="flex items-center justify-between gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate font-ui text-sm font-medium text-content">{member.member_name}</p>
                      <PartyTag party={member.party} />
                    </div>
                    <p className="mt-0.5 font-ui text-xs text-content-faint">{member.state}</p>
                  </div>
                  <div className="ml-2 text-right">
                    <p className="font-data text-sm tabular-nums text-content">{member.trade_count || 0} trades</p>
                    <p className="font-data text-[11px] uppercase tracking-[0.08em] text-content-faint">{member.chamber}</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="px-4 py-6 text-center font-ui text-sm text-content-faint">No top members available</div>
            )}
          </div>
        </Panel>
      </div>

      {/* Party distribution — proportion bars */}
      {partyEntries.length > 0 && (
        <div className="mt-6">
          <Panel title="Party Distribution">
            <div className="space-y-4 p-4">
              {partyEntries.map(([party, count]) => {
                const meta = partyMeta(party);
                const frac = partyTotal ? Number(count) / partyTotal : 0;
                return (
                  <div key={party}>
                    <div className="mb-1.5 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <PartyTag party={party} />
                        <span className="font-ui text-sm text-content-muted">{party}</span>
                      </div>
                      <span className="font-data text-sm tabular-nums text-content">
                        {Number(count).toLocaleString()}
                        <span className="ml-2 text-content-faint">{(frac * 100).toFixed(1)}%</span>
                      </span>
                    </div>
                    <Meter value={frac} color={meta.color} height={8} />
                  </div>
                );
              })}
            </div>
          </Panel>
        </div>
      )}

      {/* Analytics Debug (for troubleshooting) */}
      <div className="mt-6">
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
