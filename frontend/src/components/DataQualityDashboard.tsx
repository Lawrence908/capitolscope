import React, { useState, useEffect } from 'react';
import {
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import type { DataQualityStats } from '../types';
import apiClient from '../services/api';
import { Panel, Spinner, StatTile } from './ui';

interface DataQualityMetric {
  name: string;
  value: number;
  total: number;
  percentage: number;
  status: 'good' | 'warning' | 'error';
  description: string;
}

interface DataQualityDashboardProps {
  className?: string;
}

const DataQualityDashboard: React.FC<DataQualityDashboardProps> = ({ className = '' }) => {
  const [stats, setStats] = useState<DataQualityStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDataQualityStats = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.getDataQualityStats();
        setStats(response);
      } catch (err) {
        setError('Failed to load data quality stats');
        console.error('Data quality error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDataQualityStats();
  }, []);

  const getMetricStatus = (percentage: number): 'good' | 'warning' | 'error' => {
    if (percentage >= 95) return 'good';
    if (percentage >= 80) return 'warning';
    return 'error';
  };

  // Bulletin status: ink for good and watch, the brand red only for problems.
  const getStatusIcon = (status: 'good' | 'warning' | 'error') => {
    switch (status) {
      case 'good':
        return <CheckCircleIcon className="h-5 w-5 text-content" />;
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-content" />;
      case 'error':
        return <XCircleIcon className="h-5 w-5 text-accent" />;
    }
  };

  const STATUS_STAMP: Record<'good' | 'warning' | 'error', { label: string; className: string }> = {
    good: { label: 'Good', className: 'border-content bg-content text-surface' },
    warning: { label: 'Watch', className: 'border-content text-content' },
    error: { label: 'Flag', className: 'border-accent text-accent' },
  };

  if (loading) {
    return <Spinner label="Loading data quality" />;
  }

  if (error) {
    return (
      <div className="flex items-center gap-3 border-l-4 border-accent bg-surface-inset p-4">
        <XCircleIcon className="h-5 w-5 flex-shrink-0 text-accent" />
        <p className="font-ui text-sm text-content">{error}</p>
      </div>
    );
  }

  if (!stats) {
    return <div className="py-6 font-ui text-sm text-content-faint">No data quality stats available.</div>;
  }

  // Calculate data quality metrics
  const metrics: DataQualityMetric[] = [
    {
      name: 'Trades with Ticker Data',
      value: stats.trades_with_ticker,
      total: stats.total_trades,
      percentage: (stats.trades_with_ticker / stats.total_trades) * 100,
      status: getMetricStatus((stats.trades_with_ticker / stats.total_trades) * 100),
      description: 'Percentage of trades that have ticker information'
    },
    {
      name: 'Trades without Ticker Data',
      value: stats.trades_without_ticker,
      total: stats.total_trades,
      percentage: (stats.trades_without_ticker / stats.total_trades) * 100,
      status: getMetricStatus((stats.trades_without_ticker / stats.total_trades) * 100),
      description: 'Percentage of trades missing ticker information'
    },
    {
      name: 'Unique Members',
      value: stats.unique_members,
      total: stats.total_trades,
      percentage: (stats.unique_members / stats.total_trades) * 100,
      status: 'good', // This is just informational
      description: 'Number of unique members who have traded'
    },
    {
      name: 'Unique Tickers',
      value: stats.unique_tickers,
      total: stats.total_trades,
      percentage: (stats.unique_tickers / stats.total_trades) * 100,
      status: 'good', // This is just informational
      description: 'Number of unique securities traded'
    }
  ];

  return (
    <div className={`space-y-10 ${className}`}>
      {/* Header + summary stats */}
      <Panel title="Data quality" right={<span className="font-ui text-[12px] text-content-faint">Completeness of the disclosure record</span>}>
        <div className="grid grid-cols-1 sm:grid-cols-3">
          {[
            { label: 'Total trades', value: stats.total_trades?.toLocaleString() || '0' },
            { label: 'Unique members', value: stats.unique_members?.toLocaleString() || '0' },
            { label: 'Unique securities', value: stats.unique_tickers?.toLocaleString() || '0' },
          ].map((t, i) => (
            <div key={t.label} className={`border-b border-line py-4 ${i > 0 ? 'sm:border-l sm:pl-4' : ''}`}>
              <StatTile label={t.label} value={t.value} size="lg" />
            </div>
          ))}
        </div>
      </Panel>

      {/* Data Quality Metrics */}
      <Panel title="Completeness metrics">
        <div className="divide-y divide-line">
          {metrics.map((metric, index) => {
            const stamp = STATUS_STAMP[metric.status];
            return (
              <div key={index} className="py-4">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(metric.status)}
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-ui text-sm font-bold text-content lg:text-base">{metric.name}</h4>
                        <span
                          className={`border-2 px-1.5 py-px font-display text-[12px] font-extrabold uppercase leading-tight tracking-[0.04em] ${stamp.className}`}
                        >
                          {stamp.label}
                        </span>
                      </div>
                      <p className="font-ui text-xs text-content-muted lg:text-sm">{metric.description}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-display text-3xl font-extrabold leading-none tabular-nums text-content">
                      {metric.percentage.toFixed(1)}%
                    </div>
                    <div className="mt-1 font-ui text-xs tabular-nums text-content-faint">
                      {metric.value.toLocaleString()} / {metric.total.toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mt-3 h-2 w-full bg-surface-inset">
                  <div
                    className={`h-2 ${metric.status === 'error' ? 'bg-accent' : 'bg-content'}`}
                    style={{ width: `${Math.min(metric.percentage, 100)}%` }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-10 lg:grid-cols-2">
        {/* Issues Summary */}
        <Panel title="Issues">
          <div className="space-y-3 py-4">
            {stats.trades_without_ticker > 0 && (
              <div className="flex items-center gap-2 font-ui text-sm">
                <XCircleIcon className="h-4 w-4 flex-shrink-0 text-accent" />
                <span className="text-content-muted">
                  {stats.trades_without_ticker.toLocaleString()} trades missing ticker data ({stats.null_ticker_percentage.toFixed(1)}%)
                </span>
              </div>
            )}

            {stats.trades_with_ticker > 0 && (
              <div className="flex items-center gap-2 font-ui text-sm">
                <CheckCircleIcon className="h-4 w-4 flex-shrink-0 text-content" />
                <span className="text-content-muted">
                  {stats.trades_with_ticker.toLocaleString()} trades have ticker data ({(100 - stats.null_ticker_percentage).toFixed(1)}%)
                </span>
              </div>
            )}

            {stats.trades_without_ticker === 0 && (
              <div className="flex items-center gap-2 font-ui text-sm">
                <CheckCircleIcon className="h-4 w-4 flex-shrink-0 text-content" />
                <span className="text-content-muted">All trades have ticker data: excellent data quality.</span>
              </div>
            )}
          </div>
        </Panel>

        {/* Recommendations */}
        <Panel title="Recommendations">
          <ul className="list-inside list-disc space-y-2 py-4 font-ui text-sm text-content-muted">
            <li>Run SQL audit queries to identify specific data issues</li>
            <li>Update import scripts to validate data during ingestion</li>
            <li>Implement data quality monitoring alerts</li>
            <li>Create data cleaning scripts for identified issues</li>
          </ul>
        </Panel>
      </div>
    </div>
  );
};

export default DataQualityDashboard;
