import React, { useState, useEffect } from 'react';
import { 
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  InformationCircleIcon,
  DocumentTextIcon,
  UserGroupIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';
import type { DataQualityStats } from '../types';
import apiClient from '../services/api';

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
        setStats(response.data);
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

  const getStatusIcon = (status: 'good' | 'warning' | 'error') => {
    switch (status) {
      case 'good':
        return <CheckCircleIcon className="h-5 w-5 text-accent" />;
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-sev-watch" />;
      case 'error':
        return <XCircleIcon className="h-5 w-5 text-sev-flag" />;
    }
  };

  const getStatusColor = (status: 'good' | 'warning' | 'error') => {
    switch (status) {
      case 'good':
        return 'bg-accent/10 dark:bg-accent/10 border-accent/30 dark:border-accent/30';
      case 'warning':
        return 'bg-sev-watch/10 dark:bg-sev-watch/10 border-sev-watch/30 dark:border-sev-watch/30';
      case 'error':
        return 'bg-sev-flag/10 dark:bg-sev-flag/10 border-sev-flag/30 dark:border-sev-flag/30';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-sev-flag/10 dark:bg-sev-flag/10 border border-sev-flag/30 dark:border-sev-flag/30 rounded-md p-4">
        <div className="flex">
          <XCircleIcon className="h-5 w-5 text-sev-flag" />
          <div className="ml-3">
            <p className="text-sm text-sev-flag dark:text-sev-flag">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!stats) {
    return <div className="p-6">No data quality stats available.</div>;
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
    <div className={`space-y-4 lg:space-y-6 ${className}`}>
      {/* Header */}
      <div className="card p-4 lg:p-6">
        <div className="flex items-center gap-3">
          <InformationCircleIcon className="h-6 w-6 lg:h-8 lg:w-8 text-sev-info" />
          <div>
            <h2 className="text-xl lg:text-2xl font-bold text-content">Data Quality Dashboard</h2>
            <p className="text-sm lg:text-base text-content-muted mt-1">
              Monitor data completeness and identify quality issues
            </p>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 lg:gap-6">
        <div className="card p-4 lg:p-6">
          <div className="flex items-center gap-3">
            <DocumentTextIcon className="h-6 w-6 lg:h-8 lg:w-8 text-sev-info" />
            <div>
              <div className="text-xl lg:text-2xl font-bold text-content">
                {stats.total_trades?.toLocaleString() || '0'}
              </div>
              <div className="text-xs lg:text-sm text-content-muted">Total Trades</div>
            </div>
          </div>
        </div>

        <div className="card p-4 lg:p-6">
          <div className="flex items-center gap-3">
            <UserGroupIcon className="h-6 w-6 lg:h-8 lg:w-8 text-accent" />
            <div>
              <div className="text-xl lg:text-2xl font-bold text-content">
                {stats.unique_members?.toLocaleString() || '0'}
              </div>
              <div className="text-xs lg:text-sm text-content-muted">Unique Members</div>
            </div>
          </div>
        </div>

        <div className="card p-4 lg:p-6">
          <div className="flex items-center gap-3">
            <ChartBarIcon className="h-6 w-6 lg:h-8 lg:w-8 text-accent-2" />
            <div>
              <div className="text-xl lg:text-2xl font-bold text-content">
                {stats.unique_tickers?.toLocaleString() || '0'}
              </div>
              <div className="text-xs lg:text-sm text-content-muted">Unique Securities</div>
            </div>
          </div>
        </div>
      </div>

      {/* Data Quality Metrics */}
      <div className="space-y-4">
        <h3 className="text-base lg:text-lg font-semibold text-content">
          Data Completeness Metrics
        </h3>
        
        {metrics.map((metric, index) => (
          <div key={index} className={`card p-4 lg:p-6 border ${getStatusColor(metric.status)}`}>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex items-center gap-3">
                {getStatusIcon(metric.status)}
                <div>
                  <h4 className="font-semibold text-content text-sm lg:text-base">
                    {metric.name}
                  </h4>
                  <p className="text-xs lg:text-sm text-content-muted">
                    {metric.description}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xl lg:text-2xl font-bold text-content">
                  {metric.percentage.toFixed(1)}%
                </div>
                <div className="text-xs lg:text-sm text-content-muted">
                  {metric.value.toLocaleString()} / {metric.total.toLocaleString()}
                </div>
              </div>
            </div>
            
            {/* Progress bar */}
            <div className="mt-4">
              <div className="w-full bg-surface-inset dark:bg-surface-inset rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${
                    metric.status === 'good' ? 'bg-accent/100' :
                    metric.status === 'warning' ? 'bg-sev-watch/100' : 'bg-sev-flag/100'
                  }`}
                  style={{ width: `${Math.min(metric.percentage, 100)}%` }}
                ></div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Issues Summary */}
      <div className="card p-4 lg:p-6">
        <h3 className="text-base lg:text-lg font-semibold text-content mb-4">
          Data Quality Issues
        </h3>
        
        <div className="space-y-3">
          {stats.trades_without_ticker > 0 && (
            <div className="flex items-center gap-2 text-sm">
              <XCircleIcon className="h-4 w-4 text-sev-flag" />
              <span className="text-content-muted">
                {stats.trades_without_ticker.toLocaleString()} trades missing ticker data ({stats.null_ticker_percentage.toFixed(1)}%)
              </span>
            </div>
          )}
          
          {stats.trades_with_ticker > 0 && (
            <div className="flex items-center gap-2 text-sm">
              <CheckCircleIcon className="h-4 w-4 text-accent" />
              <span className="text-content-muted">
                {stats.trades_with_ticker.toLocaleString()} trades have ticker data ({(100 - stats.null_ticker_percentage).toFixed(1)}%)
              </span>
            </div>
          )}
          
          {stats.trades_without_ticker === 0 && (
            <div className="flex items-center gap-2 text-sm">
              <CheckCircleIcon className="h-4 w-4 text-accent" />
              <span className="text-content-muted">
                All trades have ticker data - excellent data quality!
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Recommendations */}
      <div className="card p-4 lg:p-6 bg-sev-info/10 dark:bg-sev-info/10 border border-sev-info/30 dark:border-sev-info/30">
        <h3 className="text-base lg:text-lg font-semibold text-content mb-4">
          Recommendations
        </h3>
        
        <div className="space-y-2 text-xs lg:text-sm text-content-muted">
          <p>• Run SQL audit queries to identify specific data issues</p>
          <p>• Update import scripts to validate data during ingestion</p>
          <p>• Implement data quality monitoring alerts</p>
          <p>• Create data cleaning scripts for identified issues</p>
        </div>
      </div>
    </div>
  );
};

export default DataQualityDashboard; 