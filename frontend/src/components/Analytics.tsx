import React, { useState, useEffect, Suspense } from 'react';
import {
  ChartBarIcon,
  ArrowTrendingUpIcon,
  UserGroupIcon,
  CurrencyDollarIcon,
  CalendarIcon,
  ExclamationTriangleIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { Link } from 'react-router-dom';
import PremiumFeatureWrapper from './PremiumFeatureWrapper';
import apiClient from '../services/api';
import { PageHeader, Panel, StatTile, Spinner, fmtMoney, partyMeta } from './ui';

// Design-system accent hexes (canvas can't read CSS vars; these read on both themes)
const C = {
  verdigris: '#43a897',
  steel: '#7aa8d6',
  brass: '#cca85a',
  oxblood: '#d6707b',
  amethyst: '#9d8bc4',
  faint: '#90a29d',
};
const rgba = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};

// Lazy load chart components to reduce bundle size (each is a default export).
const ChartComponents = {
  BarChart: React.lazy(() => import('./charts/BarChart')),
  LineChart: React.lazy(() => import('./charts/LineChart')),
  PieChart: React.lazy(() => import('./charts/PieChart')),
  DoughnutChart: React.lazy(() => import('./charts/DoughnutChart')),
};

// Loading component for charts
const ChartLoadingSpinner = () => (
  <div className="flex h-64 items-center justify-center gap-3">
    <div className="h-6 w-6 animate-spin rounded-full border-2 border-line border-t-accent" />
    <span className="font-data text-[11px] uppercase tracking-[0.18em] text-content-faint">Loading chart</span>
  </div>
);

interface RawMember {
  member_name?: string;
  full_name?: string;
  total_trades?: number;
  trade_count?: number;
  total_value?: number;
}

interface AnalyticsData {
  topTradingMembers: Array<{
    member_name: string;
    total_trades: number;
    total_value: number;
  }>;
  topTradedTickers: Array<{
    ticker: string;
    count: number;
    total_value: number;
  }>;
  partyDistribution: Record<string, number>;
  chamberDistribution: Record<string, number>;
  amountDistribution: Record<string, number>;
  volumeOverTime: Array<{
    date: string;
    count: number;
    volume: number;
  }>;
}

const Analytics: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [partialLoading, setPartialLoading] = useState(false);
  const [timePeriod, setTimePeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily');

  // Check subscription tier (free users see the upgrade banner)
  const subscriptionTier = user?.subscription_tier?.toLowerCase();
  const isFree = subscriptionTier === 'free' || !subscriptionTier;

  useEffect(() => {
    const fetchAnalyticsData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch all analytics data with individual error handling
        const fetchWithRetry = async <T,>(fetchFn: () => Promise<T>, retries = 2): Promise<T | undefined> => {
          for (let i = 0; i <= retries; i++) {
            try {
              return await fetchFn();
            } catch (err) {
              if (i === retries) throw err;
              const status = (err as { response?: { status?: number } })?.response?.status;
              // If it's a 429, wait before retrying
              if (status === 429) {
                const retryAfter =
                  (err as { response?: { headers?: Record<string, string> } })?.response?.headers?.['retry-after'] || 60;
                await new Promise((resolve) => setTimeout(resolve, Number(retryAfter) * 1000));
              } else {
                // For other errors, wait a shorter time
                await new Promise((resolve) => setTimeout(resolve, 1000 * (i + 1)));
              }
            }
          }
        };

        // Fetch all analytics data with individual error handling
        const [
          topTradingMembers,
          topTradedTickers,
          partyDistribution,
          chamberDistribution,
          amountDistribution,
          volumeOverTime,
        ] = await Promise.allSettled([
          fetchWithRetry(() => apiClient.getTopTradingMembers(10)),
          fetchWithRetry(() => apiClient.getTopTradedTickers(10)),
          fetchWithRetry(() => apiClient.getPartyDistribution()),
          fetchWithRetry(() => apiClient.getChamberDistribution()),
          fetchWithRetry(() => apiClient.getAmountDistribution()),
          fetchWithRetry(() => apiClient.getVolumeOverTime(timePeriod)),
        ]);

        // Check if we have at least some data
        const successfulRequests = [
          topTradingMembers,
          topTradedTickers,
          partyDistribution,
          chamberDistribution,
          amountDistribution,
          volumeOverTime,
        ].filter((result) => result.status === 'fulfilled');

        if (successfulRequests.length === 0) {
          setError('Failed to load analytics data. Please try again later.');
          return;
        }

        // Show partial loading state if some requests are still pending
        if (successfulRequests.length < 6) {
          setPartialLoading(true);
        }

        // Extract data from successful requests, use defaults for failed ones
        const analyticsData: AnalyticsData = {
          topTradingMembers:
            topTradingMembers.status === 'fulfilled'
              ? ((topTradingMembers.value as RawMember[]) || []).map((member) => ({
                  member_name: member.member_name || member.full_name || 'Unknown',
                  total_trades: member.total_trades ?? member.trade_count ?? 0,
                  total_value: member.total_value || 0,
                }))
              : [],
          topTradedTickers: topTradedTickers.status === 'fulfilled' ? (topTradedTickers.value ?? []) : [],
          partyDistribution: partyDistribution.status === 'fulfilled' ? (partyDistribution.value ?? {}) : {},
          chamberDistribution: chamberDistribution.status === 'fulfilled' ? (chamberDistribution.value ?? {}) : {},
          amountDistribution: amountDistribution.status === 'fulfilled' ? (amountDistribution.value ?? {}) : {},
          volumeOverTime: volumeOverTime.status === 'fulfilled' ? (volumeOverTime.value ?? []) : [],
        };

        setData(analyticsData);

        // Clear partial loading state if all data is loaded
        if (successfulRequests.length === 6) {
          setPartialLoading(false);
        }

        // Show warning if some requests failed
        if (successfulRequests.length < 6) {
          console.warn('Some analytics data failed to load');
        }
      } catch (err) {
        setError('Failed to load analytics data');
        console.error('Analytics error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalyticsData();
  }, [timePeriod]);

  // Helper function to format dates
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: timePeriod === 'monthly' ? 'numeric' : undefined,
    });
  };

  if (loading) {
    return <Spinner label="Computing analytics" />;
  }

  if (error && !data) {
    return (
      <div className="flex items-center gap-3 rounded-md border border-sev-flag/40 px-4 py-3 status-error">
        <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" />
        <p className="font-ui text-sm">{error}</p>
      </div>
    );
  }

  if (!data || (data.topTradingMembers.length === 0 && data.topTradedTickers.length === 0)) {
    return <div className="p-6 font-ui text-sm text-content-faint">No analytics data available.</div>;
  }

  // Prepare chart data with defensive checks
  const topMembersChartData = {
    labels: data.topTradingMembers?.map((member) => member.member_name) || [],
    datasets: [
      {
        label: 'Total Trades',
        data: data.topTradingMembers?.map((member) => member.total_trades) || [],
        backgroundColor: rgba(C.verdigris, 0.8),
        borderColor: C.verdigris,
        borderWidth: 1,
      },
    ],
  };

  const topTickersChartData = {
    labels: data.topTradedTickers?.map((ticker) => ticker.ticker) || [],
    datasets: [
      {
        label: 'Trade Count',
        data: data.topTradedTickers?.map((ticker) => ticker.count) || [],
        backgroundColor: rgba(C.steel, 0.8),
        borderColor: C.steel,
        borderWidth: 1,
      },
    ],
  };

  const partyChartData = {
    labels: Object.keys(data.partyDistribution || {}),
    datasets: [
      {
        label: 'Trades by Party',
        data: Object.values(data.partyDistribution || {}),
        backgroundColor: Object.keys(data.partyDistribution || {}).map((p) => rgba(partyMeta(p).color, 0.8)),
        borderColor: Object.keys(data.partyDistribution || {}).map((p) => partyMeta(p).color),
        borderWidth: 2,
      },
    ],
  };

  const chamberChartData = {
    labels: Object.keys(data.chamberDistribution || {}),
    datasets: [
      {
        label: 'Trades by Chamber',
        data: Object.values(data.chamberDistribution || {}),
        backgroundColor: [rgba(C.brass, 0.8), rgba(C.verdigris, 0.8), rgba(C.faint, 0.8)],
        borderColor: [C.brass, C.verdigris, C.faint],
        borderWidth: 2,
      },
    ],
  };

  const amountChartData = {
    labels: Object.keys(data.amountDistribution || {}),
    datasets: [
      {
        label: 'Number of Trades',
        data: Object.values(data.amountDistribution || {}),
        backgroundColor: rgba(C.brass, 0.8),
        borderColor: C.brass,
        borderWidth: 1,
      },
    ],
  };

  const volumeChartData = {
    labels: data.volumeOverTime?.map((item) => formatDate(item.date)) || [],
    datasets: [
      {
        label: 'Trade Volume',
        data: data.volumeOverTime?.map((item) => item.volume / 100) || [], // Convert cents to dollars
        borderColor: C.verdigris,
        backgroundColor: rgba(C.verdigris, 0.12),
        borderWidth: 2,
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const totalTrades = Object.values(data.partyDistribution).reduce((a, b) => a + b, 0);
  const totalVolume = data.volumeOverTime.reduce((sum, item) => sum + item.volume, 0) / 100;

  return (
    <div>
      <PageHeader
        eyebrow="CapitolScope · Analytics"
        title="Analytics"
        subtitle="Comprehensive analysis of congressional trading — top members and securities, party and chamber breakdowns, amount distribution, and volume over time."
        actions={
          <div className="flex items-center gap-2">
            <CalendarIcon className="h-5 w-5 text-content-faint" />
            <select
              value={timePeriod}
              onChange={(e) => setTimePeriod(e.target.value as 'daily' | 'weekly' | 'monthly')}
              className="input-field text-sm"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
        }
      />

      <div className="space-y-6">
        {/* Premium Upgrade Banner for Free Users */}
        {isFree && (
          <div className="flex flex-col gap-4 rounded-md border border-accent/40 bg-accent/10 p-4 sm:flex-row sm:items-center sm:justify-between lg:p-6">
            <div className="flex items-center">
              <SparklesIcon className="mr-3 h-6 w-6 flex-shrink-0 text-accent" />
              <div>
                <h4 className="font-display text-lg font-medium text-content">Unlock Advanced Analytics</h4>
                <p className="font-ui text-sm text-content-muted">
                  Comprehensive trading analytics, advanced charts, and detailed insights.
                </p>
              </div>
            </div>
            <Link to="/premium" className="btn-primary whitespace-nowrap px-4 py-2 text-sm">
              View Plans
            </Link>
          </div>
        )}

        {/* Partial Loading Indicator */}
        {partialLoading && (
          <div className="flex items-center gap-3 rounded-md border border-sev-watch/40 bg-sev-watch/10 p-4">
            <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0 text-sev-watch" />
            <div>
              <h4 className="font-ui text-sm font-medium text-content">Loading partial data</h4>
              <p className="font-ui text-sm text-content-faint">
                Some analytics are still loading; the page will update automatically.
              </p>
            </div>
          </div>
        )}

        {/* Top Trading Members */}
        <PremiumFeatureWrapper featureName="Top Trading Members Analytics" requiredTier="pro" showBadge={false}>
          <Panel title={<span className="inline-flex items-center gap-2"><UserGroupIcon className="h-4 w-4" /> Top Trading Members</span>}>
            <div className="p-4">
              <Suspense fallback={<ChartLoadingSpinner />}>
                <ChartComponents.BarChart data={topMembersChartData} title="Members by Total Trades" height={300} />
              </Suspense>
            </div>
          </Panel>
        </PremiumFeatureWrapper>

        {/* Top Traded Tickers */}
        <PremiumFeatureWrapper featureName="Most Traded Securities Analytics" requiredTier="pro" showBadge={false}>
          <Panel title={<span className="inline-flex items-center gap-2"><ChartBarIcon className="h-4 w-4" /> Most Traded Securities</span>}>
            <div className="p-4">
              <Suspense fallback={<ChartLoadingSpinner />}>
                <ChartComponents.BarChart data={topTickersChartData} title="Securities by Trade Count" height={300} />
              </Suspense>
            </div>
          </Panel>
        </PremiumFeatureWrapper>

        {/* Party and Chamber Distribution */}
        <PremiumFeatureWrapper featureName="Party and Chamber Distribution Analytics" requiredTier="pro" showBadge={false}>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel title={<span className="inline-flex items-center gap-2"><ArrowTrendingUpIcon className="h-4 w-4" /> Trading by Party</span>}>
              <div className="p-4">
                <Suspense fallback={<ChartLoadingSpinner />}>
                  <ChartComponents.PieChart data={partyChartData} title="Trades by Political Party" height={250} />
                </Suspense>
              </div>
            </Panel>

            <Panel title={<span className="inline-flex items-center gap-2"><CurrencyDollarIcon className="h-4 w-4" /> Trading by Chamber</span>}>
              <div className="p-4">
                <Suspense fallback={<ChartLoadingSpinner />}>
                  <ChartComponents.DoughnutChart data={chamberChartData} title="Trades by Congressional Chamber" height={250} />
                </Suspense>
              </div>
            </Panel>
          </div>
        </PremiumFeatureWrapper>

        {/* Amount Distribution */}
        <PremiumFeatureWrapper featureName="Trade Amount Distribution Analytics" requiredTier="pro" showBadge={false}>
          <Panel title={<span className="inline-flex items-center gap-2"><CurrencyDollarIcon className="h-4 w-4" /> Trade Amount Distribution</span>}>
            <div className="p-4">
              <Suspense fallback={<ChartLoadingSpinner />}>
                <ChartComponents.BarChart data={amountChartData} title="Trades by Amount Range" height={300} />
              </Suspense>
            </div>
          </Panel>
        </PremiumFeatureWrapper>

        {/* Volume Over Time */}
        <PremiumFeatureWrapper featureName="Trading Volume Over Time Analytics" requiredTier="premium" showBadge={false}>
          <Panel title={<span className="inline-flex items-center gap-2"><ArrowTrendingUpIcon className="h-4 w-4" /> Trading Volume Over Time</span>}>
            <div className="p-4">
              <Suspense fallback={<ChartLoadingSpinner />}>
                <ChartComponents.LineChart data={volumeChartData} title={`Trade Volume (${timePeriod})`} height={300} />
              </Suspense>
            </div>
          </Panel>
        </PremiumFeatureWrapper>

        {/* Summary Stats */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="card p-4 lg:p-5">
            <StatTile label="Total Members" value={data.topTradingMembers.length} />
          </div>
          <div className="card p-4 lg:p-5">
            <StatTile label="Total Securities" value={data.topTradedTickers.length} tone="steel" />
          </div>
          <div className="card p-4 lg:p-5">
            <StatTile label="Total Trades" value={totalTrades.toLocaleString()} tone="accent" />
          </div>
          <div className="card p-4 lg:p-5">
            <StatTile label="Total Volume" value={fmtMoney(totalVolume)} tone="brass" />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
